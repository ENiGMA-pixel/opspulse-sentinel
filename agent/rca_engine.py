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


def load_context(df_telemetry=None, df_deployments=None):
    with open("config/cluster_manifest.json", "r") as f:
        cluster_map = f.read()

    if df_telemetry is None:
        df_telemetry = pd.read_csv("data/processed/structured_telemetry.csv")
    if df_deployments is None:
        df_deployments = pd.read_csv("data/processed/deployment_log.csv")

    important = df_telemetry[df_telemetry['Level'].isin(['ERROR', 'FATAL', 'WARN', 'INFO'])]
    clean_telemetry = "\n".join(
        f"[{r['Time']}] {r['Component']}: {r['Content']}"
        for _, r in important.tail(15).iterrows()
    )
    clean_deployments = df_deployments.tail(5).to_string(index=False)

    return cluster_map, clean_telemetry, clean_deployments


def build_prompt(df_telemetry=None, df_deployments=None):
    historical_memory = query_historical_memory(
        "503 Service Unavailable timeout after deployment configuration change"
    )
    cluster_map, clean_telemetry, clean_deployments = load_context(
        df_telemetry=df_telemetry,
        df_deployments=df_deployments
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        historical_memory=historical_memory,
        cluster_map=cluster_map,
        clean_deployments=clean_deployments,
        clean_telemetry=clean_telemetry
    )

    return SYSTEM_INSTRUCTION.strip(), user_prompt.strip()


def generate_rca_with_fallback(df_telemetry=None, df_deployments=None):
    primary_model = 'gemini-3.1-pro-preview'
    fallback_model = 'gemini-3.1-flash-lite-preview'

    system_instruction, user_prompt = build_prompt(
        df_telemetry=df_telemetry,
        df_deployments=df_deployments
    )

    try:
        print(f"🧠 Attempting RCA with {primary_model}...")
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