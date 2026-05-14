# Cell 4: The Reasoning Engine (Day 3 RAG Loop + Graceful Degradation)
import time
import json
from google import genai

print("🔍 Querying ChromaDB Historical Memory...")
# 1. NEW DAY 3 RAG LOOP: Query ChromaDB for past similar incidents
incident_query = "503 Service Unavailable timeout after deployment configuration change"
retrieval_results = collection.query(
    query_texts=[incident_query],
    n_results=1
)

# 🛡️ THE RAG GUARDRAIL: Graceful Degradation
if retrieval_results.get('documents') and retrieval_results['documents'][0]:
    historical_memory = retrieval_results['documents'][0][0]
    print(f"📚 Retrieved Past Incident: {historical_memory}")
else:
    historical_memory = "No historical precedent found. Rely on manifest baselines."
    print("⚠️ No historical precedent found. Relying on zero-shot reasoning.")

# 2. Load the Manifest Map
with open(manifest_path, 'r') as f:
    cluster_map = f.read()

# 3. Hardened Prompts with Temporal Causation & Historical Context
system_instruction = f"""
You are OpsPulse Sentinel, an elite AI Site Reliability Engineer. 
Your job is to perform Root Cause Analysis (RCA).
CRITICAL INSTRUCTION: You must explicitly analyze temporal causation. Look at the timestamps. 
If a configuration change or deployment at time T immediately precedes an error cascade at time T+X, you must highlight this time correlation as the primary evidence.
Use the Historical Memory provided to inform your recommended remediation.
"""

user_prompt = f"""
ALERT: Widespread 503 Service Unavailable errors detected.

[HISTORICAL INCIDENT MEMORY]
The following past incident was retrieved from our Vector Database based on current symptoms:
{historical_memory}

[GROUND TRUTH MANIFEST]
{cluster_map}

[RECENT SYSTEM CHANGES (Deployment Log)]
{clean_deployments}

[OBSERVED TELEMETRY (Last 15 Events)]
{clean_telemetry}

INSTRUCTIONS: 
1. Correlate the timestamps between 'Recent System Changes' and 'Observed Telemetry'. 
2. Factor in the 'Historical Incident Memory' to formulate your fix.
3. Output the strict JSON RCA.
"""

# 4. The Fallback Logic
def generate_rca_with_fallback(prompt, instruction):
    primary_model = 'gemini-3.1-pro-preview'
    fallback_model = 'gemini-3.1-flash-lite-preview' 

    try:
        print(f"🧠 Attempting RCA with {primary_model}...")
        response = client.models.generate_content(
            model=primary_model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=instruction,
                response_mime_type="application/json",
                response_schema=RootCauseAnalysis,
                temperature=0.1
            ),
        )
        return response, primary_model

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "503" in error_msg or "UNAVAILABLE" in error_msg:
            print(f"⚠️ {primary_model} is unavailable. Triggering Path B: {fallback_model}...")
            time.sleep(1) 
            response = client.models.generate_content(
                model=fallback_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=instruction,
                    response_mime_type="application/json",
                    response_schema=RootCauseAnalysis,
                    temperature=0.1
                ),
            )
            return response, fallback_model
        else:
            raise e

# --- Execute and Validate ---
print("\n🚀 Initializing Reasoning Engine...")
response, model_used = generate_rca_with_fallback(user_prompt, system_instruction)

rca_result = json.loads(response.text)
print(f"\n🚨 OPS-PULSE SENTINEL RCA REPORT (Model: {model_used}) 🚨")
print(json.dumps(rca_result, indent=4))

# Output Validation & Action Gating
print("\n🛡️ --- SYSTEM GUARDRAIL CHECK ---")
if rca_result.get('confidence_score', 1.0) < 0.75:
    print("❌ THRESHOLD FAILED: Confidence score below 0.75.")
    print("📢 ACTION: Automated remediation aborted. Escalating to L2 SRE for manual review.")
elif rca_result.get('require_human_approval', False):
    print("⚠️ POLICY FLAG: Human approval required for infrastructure modification.")
    print(f"⏸️ PENDING APPROVAL TO EXECUTE: {rca_result.get('executable_fix_cmd')}")
else:
    print(f"✅ CLEAR TO AUTO-EXECUTE: {rca_result.get('executable_fix_cmd')}")