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


# ─────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────
def save_audit_log(rca_result: dict, model_used: str):
    """Appends every RCA result to a persistent audit log."""
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
    print(f"✅ Audit log updated. Total incidents logged: {len(existing)}")


# ─────────────────────────────────────────────
# STAGE 1 — FLASH ANOMALY FILTER
# ─────────────────────────────────────────────
def flash_anomaly_filter(raw_telemetry: str) -> str:
    """
    Stage 1: Gemini Flash-Lite rapidly scans raw telemetry and returns
    only the anomalous lines worth investigating.

    If Flash fails for any reason (quota, network, model unavailable),
    the full raw telemetry is returned as a passthrough so Stage 2
    still runs. This prevents a Flash failure from killing the pipeline.
    """
    flash_model = 'gemini-2.0-flash-lite'

    filter_prompt = f"""You are a high-speed log anomaly detector.
Scan the following telemetry logs and return ONLY the lines that indicate
errors, warnings, failures, or suspicious patterns.
Ignore all INFO lines that show normal operation.
Return the filtered lines as plain text, one per line.
If no anomalies are found, return exactly: NO_ANOMALIES_DETECTED

[RAW TELEMETRY]
{raw_telemetry}
"""

    try:
        print("⚡ Stage 1: Flash-Lite anomaly filtering...")
        response = client.models.generate_content(
            model=flash_model,
            contents=filter_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.0
            )
        )
        result = response.text.strip()

        # If Flash finds nothing or returns empty, pass through full telemetry
        if not result or result == "NO_ANOMALIES_DETECTED":
            print("⚠️ Flash found no anomalies. Passing full telemetry to Pro.")
            return raw_telemetry

        print(f"✅ Stage 1 complete. Anomalous lines extracted.")
        return result

    except Exception as e:
        # ── GRACEFUL PASSTHROUGH ──────────────────────────────────────
        # Flash failed (quota / network / model unavailable).
        # Return raw telemetry so Stage 2 (Pro) still runs uninterrupted.
        print(f"⚠️ Flash filter failed: {e}. Passing raw telemetry to Stage 2.")
        return raw_telemetry


# ─────────────────────────────────────────────
# CONTEXT LOADER
# ─────────────────────────────────────────────
def load_context(df_telemetry: pd.DataFrame, df_deployments: pd.DataFrame):
    """
    Pre-processes telemetry and deployments.
    Caps telemetry at 50 rows before passing to Flash to avoid token overflow.
    """
    # Cap at 50 rows — enough signal, avoids token overflow on large CSVs
    raw_telemetry_str = df_telemetry.tail(50).to_string(index=False)

    # Run through Stage 1 Flash filter
    filtered_telemetry_str = flash_anomaly_filter(raw_telemetry_str)

    # Deployment log — send full context (typically small)
    clean_deployments = df_deployments.to_string(index=False)

    return filtered_telemetry_str, clean_deployments


# ─────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────
def build_prompt(df_telemetry: pd.DataFrame, df_deployments: pd.DataFrame):
    """Assembles the full multi-source prompt for Gemini Pro."""

    # 1. Load Cluster Manifest
    try:
        with open("config/cluster_manifest.json", "r") as f:
            cluster_map = f.read()
    except Exception:
        cluster_map = "Cluster manifest not available."

    # 2. Pre-process telemetry (includes Stage 1 Flash filter)
    clean_telemetry, clean_deployments = load_context(df_telemetry, df_deployments)

    # 3. Query ChromaDB with the filtered anomalies as the search query
    print("🔍 Querying ChromaDB historical memory...")
    historical_memory = query_historical_memory(clean_telemetry)

    # 4. Assemble final prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        historical_memory=historical_memory,
        cluster_map=cluster_map,
        clean_deployments=clean_deployments,
        clean_telemetry=clean_telemetry
    )

    return SYSTEM_INSTRUCTION, user_prompt


# ─────────────────────────────────────────────
# MAIN RCA FUNCTION
# ─────────────────────────────────────────────
def generate_rca_with_fallback(df_telemetry=None, df_deployments=None):
    """
    Core agent pipeline with three layers of resilience:
      Layer 1 — Flash filter try/except (passthrough on failure)
      Layer 2 — Pro model → Flash-Lite model fallback on quota/503
      Layer 3 — App.py cached mock RCA (only if both models fail)
    """

    # Load defaults if no custom data provided by Streamlit
    if df_telemetry is None:
        df_telemetry = pd.read_csv("data/processed/structured_telemetry.csv")
    if df_deployments is None:
        df_deployments = pd.read_csv("data/processed/deployment_log.csv")

    primary_model = 'gemini-2.0-flash'      # swap to gemini-3.1-pro-preview if available
    fallback_model = 'gemini-2.0-flash-lite'

    # ── EVERYTHING inside one try block ──────────────────────────────
    # build_prompt() (which calls flash_anomaly_filter) is now protected.
    # Previously it sat outside the try, so any Flash failure bypassed
    # the fallback model and went straight to the cached mock.
    try:
        system_instruction, user_prompt = build_prompt(
            df_telemetry=df_telemetry,
            df_deployments=df_deployments
        )

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
        print(f"✅ RCA complete via {primary_model}.")
        return response, primary_model

    except Exception as e:
        error_msg = str(e)
        quota_errors = ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "quota"]

        if any(code in error_msg for code in quota_errors):
            # ── LAYER 2: Model fallback ───────────────────────────────
            print(f"⚠️ {primary_model} unavailable ({error_msg[:60]}). Triggering fallback: {fallback_model}...")
            time.sleep(1)

            try:
                # Re-build prompt for the fallback attempt
                system_instruction, user_prompt = build_prompt(
                    df_telemetry=df_telemetry,
                    df_deployments=df_deployments
                )
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
                print(f"✅ RCA complete via fallback {fallback_model}.")
                return response, fallback_model

            except Exception as fallback_error:
                # Both models failed — raise so app.py shows cached mock
                raise RuntimeError(
                    f"Both models failed. Primary: {error_msg[:80]}. "
                    f"Fallback: {str(fallback_error)[:80]}"
                )
        else:
            # Non-quota error (bad API key, malformed prompt, etc.) — raise immediately
            raise e