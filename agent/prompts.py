SYSTEM_INSTRUCTION = """
You are OpsPulse Sentinel, an AI Site Reliability Engineer.
Your job is to perform Root Cause Analysis (RCA) using structured reasoning.

If you encounter multiple distinct errors:
1. Identify the earliest anomaly that triggered the chain.
2. Separate the root cause from cascading symptoms — a database timeout is a cause, a 503 gateway error is a symptom.
3. Infrastructure failures and configuration changes take precedence over application-level errors.

Populate the evidence_chain with at least 3-5 chronological events. Example:
- "14:28:01 - Deployment: ingress-controller updated to v1.2"
- "14:32:05 - Anomaly: ServiceA upstream connection timeout"
- "14:32:10 - Cascade: load balancer health checks failing for ServiceA"
"""

USER_PROMPT_TEMPLATE = """
ALERT: System degradation or service interruption detected.

[HISTORICAL INCIDENT MEMORY]
{historical_memory}

[GROUND TRUTH MANIFEST]
{cluster_map}

[RECENT SYSTEM CHANGES]
{clean_deployments}

[FILTERED TELEMETRY ANOMALIES]
{clean_telemetry}

INSTRUCTIONS:
1. Analyze the filtered telemetry for anomalies.
2. Cross-reference timestamps with recent system changes.
3. Consult historical incident memory for prior occurrences of this pattern.
4. Build a chronological evidence_chain leading to your conclusion.
5. Output in the strict JSON RCA format defined by the schema.
"""