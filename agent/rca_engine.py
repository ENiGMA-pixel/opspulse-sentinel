import time
import os
import json
import logging
from datetime import datetime
import pandas as pd
from google import genai
from agent.schema import RootCauseAnalysis
from agent.memory_bank import query_historical_memory
from agent.prompts import SYSTEM_INSTRUCTION, USER_PROMPT_TEMPLATE
import streamlit as st

logger = logging.getLogger(__name__)

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def save_audit_log(rca_result: dict, model_used: str):
    """Write RCA result to audit_log.json. Creates file if absent."""
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


def flash_anomaly_filter(raw_telemetry: str) -> str:
    """
    Run raw telemetry through Flash-Lite to extract anomalous lines only.
    Falls back to passing raw telemetry if the model call fails.
    """
    flash_model = 'gemini-3.1-flash-lite-preview'

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
        response = client.models.generate_content(
            model=flash_model,
            contents=filter_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.0
            )
        )
        result = response.text.strip()

        if not result or result == "NO_ANOMALIES_DETECTED":
            return raw_telemetry

        return result

    except Exception as e:
        logger.warning("flash filter failed, passing raw telemetry: %s", e)
        return raw_telemetry


def load_context(df_telemetry: pd.DataFrame, df_deployments: pd.DataFrame):
    # cap at 50 rows to avoid token overflow on large uploads
    raw_telemetry = df_telemetry.tail(50).to_string(index=False)
    filtered_telemetry = flash_anomaly_filter(raw_telemetry)
    clean_deployments = df_deployments.to_string(index=False)
    return filtered_telemetry, clean_deployments


def build_prompt(df_telemetry: pd.DataFrame, df_deployments: pd.DataFrame):
    try:
        with open("config/cluster_manifest.json", "r") as f:
            cluster_map = f.read()
    except Exception:
        cluster_map = "Cluster manifest not available."

    clean_telemetry, clean_deployments = load_context(df_telemetry, df_deployments)
    historical_memory = query_historical_memory(clean_telemetry)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        historical_memory=historical_memory,
        cluster_map=cluster_map,
        clean_deployments=clean_deployments,
        clean_telemetry=clean_telemetry
    )

    return SYSTEM_INSTRUCTION, user_prompt


def generate_rca_with_fallback(df_telemetry=None, df_deployments=None):
    if df_telemetry is None:
        df_telemetry = pd.read_csv("data/processed/structured_telemetry.csv")
    if df_deployments is None:
        df_deployments = pd.read_csv("data/processed/deployment_log.csv")

    primary_model = 'gemini-3.1-pro-preview'
    fallback_model = 'gemini-3.1-flash-lite-preview'

    quota_errors = [
        "429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE",
        "quota", "PERMISSION_DENIED", "billing", "API_KEY_INVALID", "invalid"
    ]

    try:
        system_instruction, user_prompt = build_prompt(
            df_telemetry=df_telemetry,
            df_deployments=df_deployments
        )

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
        if any(code in error_msg for code in quota_errors):
            logger.warning("primary model unavailable (%s), falling back to %s", primary_model, fallback_model)
            time.sleep(1)

            try:
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
                return response, fallback_model

            except Exception as fallback_error:
                raise RuntimeError(
                    f"Both models failed. Primary: {error_msg[:80]}. "
                    f"Fallback: {str(fallback_error)[:80]}"
                )
        else:
            raise e
