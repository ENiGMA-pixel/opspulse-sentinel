import time
import os
import json
from datetime import datetime
import pandas as pd
from google import genai
from agent.schema import RootCauseAnalysis
from agent.memory_bank import query_historical_memory
from agent.prompts import SYSTEM_INSTRUCTION, USER_PROMPT_TEMPLATE
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def save_audit_log(rca_result: dict, model_used: str):
    """
    Appends every RCA result to a persistent audit log.
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "model_used": model_used,
        "rca_result": rca_result
    }
    log_path = "audit_log.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []
    else:
        existing = []
        
    existing.append(log_entry)
    with open(log_path, "w") as f:
        json.dump(existing, f, indent=4)
    print(f"✅ Audit log updated. Total incidents: {len(existing)}")


def flash_anomaly_filter(raw_telemetry: str) -> str:
    """
    Stage 1: Gemini Flash-Lite rapidly scans raw telemetry
    and returns only the anomalous lines worth investigating.
    """
    flash_model = 'gemini-3.1-flash-lite-preview'

    filter_prompt = f"""
You are a high-speed log anomaly detector.
Scan the following telemetry logs and return ONLY the lines that indicate
errors, warnings, failures, or suspicious patterns.
Ignore all INFO lines that show normal operation.
Return the filtered lines as plain text, one per line.
If no anomalies found, return: "NO_ANOMALIES_DETECTED"

[RAW TELEMETRY]
{raw_telemetry}
"""

    print("⚡ Stage 1: Flash-Lite anomaly filtering...")
    response = client.models.generate_content(
        model=flash_model,
        contents=filter_prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.0
        )
    )
    filtered = response.text.strip()
    print(f"✅ Flash filter complete. Anomalies extracted.")
    return filtered


def load_context(df_telemetry, df_deployments):
    """Loads and pre-processes context for the Pro model."""
    
    # Convert DataFrame to string before passing to Flash
    raw_telemetry_str = df_telemetry.to_string(index=False)
    
    # ⚡ NEW: Run the raw telemetry through the Flash filter first
    filtered_telemetry_str = flash_anomaly_filter(raw_telemetry_str)
    
    # Format the deployment logs normally
    clean_deployments = df_deployments.to_string(index=False)
    
    return filtered_telemetry_str, clean_deployments


def build_prompt(df_telemetry, df_deployments):
    """Assembles the final prompt for Gemini Pro."""
    
    # 1. Load Cluster Manifest
    try:
        with open("config/cluster_manifest.json", "r") as f:
            cluster_map = f.read()
    except Exception:
        cluster_map = "Cluster manifest not available."

    # 2. Pre-process telemetry and deployments (Includes Stage 1 Flash Filter)
    clean_telemetry, clean_deployments = load_context(df_telemetry, df_deployments)
    
    # 3. Query Historical Memory using the anomalies we just found!
    print("🔍 Querying ChromaDB Historical Memory...")
    historical_memory = query_historical_memory(clean_telemetry)
    
    # 4. Inject all context into your final prompt string
    user_prompt = USER_PROMPT_TEMPLATE.format(
        historical_memory=historical_memory,
        cluster_map=cluster_map,
        clean_deployments=clean_deployments,
        clean_telemetry=clean_telemetry # <--- This is now the Flash-filtered output!
    )
    
    # Return BOTH the system instruction and the user prompt
    return SYSTEM_INSTRUCTION, user_prompt


def generate_rca_with_fallback(df_telemetry=None, df_deployments=None):
    
    # Load defaults if none provided by Streamlit
    if df_telemetry is None:
        df_telemetry = pd.read_csv("data/processed/structured_telemetry.csv")
    if df_deployments is None:
        df_deployments = pd.read_csv("data/processed/deployment_log.csv")

    primary_model = 'gemini-3.1-pro-preview'
    fallback_model = 'gemini-3.1-flash-lite-preview'

    # Unpack the two values returned by build_prompt
    system_instruction, user_prompt = build_prompt(
        df_telemetry=df_telemetry,
        df_deployments=df_deployments
    )

    try:
        print(f"🧠 Stage 2: Deep RCA with {primary_model}...")
        response = client.models.generate_content(
            model=primary_model,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=RootCauseAnalysis,
                temperature=0.1
            ),
        )
        return response, primary_model

    except Exception as e:
        error_msg = str(e)
        if any(code in error_msg for code in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]):
            print(f"⚠️ {primary_model} unavailable. Triggering fallback: {fallback_model}...")
            time.sleep(1)
            response = client.models.generate_content(
                model=fallback_model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=RootCauseAnalysis,
                    temperature=0.1
                ),
            )
            return response, fallback_model
        else:
            raise e