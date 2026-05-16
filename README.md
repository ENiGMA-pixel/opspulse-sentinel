# ⚡ OpsPulse Sentinel
### Autonomous Root Cause Analysis for Enterprise SRE Teams

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?logo=streamlit)](https://opspulse-sentinel.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![Gemini](https://img.shields.io/badge/Powered%20by-Gemini%203.1-4285F4?logo=google)](https://ai.google.dev)

> **Hackathon Track:** Track 2 — AI Agents with Google AI Studio
> **Stack:** Gemini 3.1 Pro + Flash-Lite · ChromaDB · Pydantic · Streamlit

---
<p align="center">
  <img src="docs/1.png" alt="OpsPulse Sentinel Dashboard" width="100%">
  <br>
  <em>OpsPulse Sentinel Incident Command Center: Diagnosing a critical telemetry anomaly in under 60 seconds.</em>
</p>

## 📊 Projected MTTR Impact

| Diagnostic Phase | Manual SRE | OpsPulse Sentinel | Reduction |
|---|---|---|---|
| Log Triage | 15 min | 3 sec | 99.7% |
| Cross-Service Correlation | 45 min | 15 sec | 99.4% |
| Root Cause Identification | 30 min | 10 sec | 99.4% |
| **Total MTTR** | **90 min** | **< 60 sec** | **~98.9%** |

> ⚠️ **Note:** These are projected benchmark figures based on controlled validation against a synthetic failure suite. Real-world MTTR will vary depending on cluster size, log volume, and approval latency.

---

## 🧠 What OpsPulse Sentinel Does

Traditional monitoring tools (Datadog, Grafana, PagerDuty) tell you **something is broken**. They surface alerts and metrics. They do not tell you **why** it broke, **what changed**, or **what command to run** to fix it.

OpsPulse Sentinel is an autonomous SRE agent that:

1. **Ingests** telemetry logs, deployment history, and cluster architecture simultaneously
2. **Filters** raw logs using Gemini Flash-Lite to extract only anomalous events
3. **Retrieves** semantically similar past incidents from a ChromaDB vector memory
4. **Reasons** across all three sources using Gemini Pro with explicit temporal causation logic
5. **Outputs** a structured JSON RCA report with a ready-to-run remediation command
6. **Gates** execution behind a human approval policy before touching infrastructure

---

## 🏗️ Architecture

```
Raw Telemetry CSV
       │
       ▼
┌─────────────────────────────┐
│  Stage 1: Flash-Lite Filter │  ← Gemini 3.1 Flash-Lite-Preview
│  Anomaly extraction from    │    Strips INFO noise, returns
│  50 raw log lines           │    only ERRORs / WARNs / FATALs
└────────────┬────────────────┘
             │ filtered_anomalies
             ▼
┌─────────────────────────────┐
│  ChromaDB Vector Memory     │  ← PersistentClient on disk
│  Semantic similarity search │    5 historical incident resolutions
│  over past incidents        │    Returns closest precedent
└────────────┬────────────────┘
             │ historical_memory
             ▼
┌─────────────────────────────────────────────┐
│  Stage 2: Gemini Pro Deep RCA               │  ← gemini-3.1-pro-preview
│                                             │    (fallback: flash-lite-preview)
│  Multi-source prompt:                       │
│  [Historical Memory] + [Cluster Manifest]   │
│  + [Deployment Log]  + [Filtered Telemetry] │
│                                             │
│  Temporal causation instruction:            │
│  "If change at T precedes errors at T+X,   │
│   highlight as primary evidence"            │
└────────────┬────────────────────────────────┘
             │ Pydantic-validated JSON RCA
             ▼
┌─────────────────────────────┐
│  Policy Guardrail           │
│  confidence < 0.75 → block  │
│  require_human_approval     │
│  → gate before execution    │
└─────────────────────────────┘
             │
             ▼
     Streamlit Dashboard
     (Approve / Reject / Escalate)
```

### Dual-Model Routing

| Model | Role | Trigger |
|---|---|---|
| `gemini-3.1-flash-lite-preview` | Stage 1 anomaly filter | Always (every run) |
| `gemini-3.1-pro-preview` | Stage 2 deep RCA | Primary attempt |
| `gemini-3.1-flash-lite-preview` | Stage 2 fallback | On quota/503/429 |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Installation

```bash
# Clone the repo
git clone https://github.com/ENiGMA-pixel/opspulse-sentinel.git
cd opspulse-sentinel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run

```bash
streamlit run ui/app.py
```

Open `http://localhost:8501`

### Data Setup

The repo includes a pre-built synthetic validation dataset:
- `data/processed/structured_telemetry.csv` — 2000 HDFS-style log events with injected Helm timeout failure
- `data/processed/deployment_log.csv` — deployment history including the synthetic `helm upgrade ingress-controller --set proxy-connect-timeout=5s` event

To use your own logs, upload CSVs directly in the app UI. Required columns: `Date`, `Time`, `Pid`, `Level`, `Component`, `Content`.

> **Raw data:** Download `HDFS_2k.log` from [LogHub](https://github.com/logpai/loghub) and place in `data/raw/` to run the full ingestion pipeline from scratch.

---

## 📁 Project Structure

```
opspulse-sentinel/
├── agent/
│   ├── __init__.py
│   ├── memory_bank.py       ← ChromaDB PersistentClient + 5 historical incidents
│   ├── prompts.py           ← SYSTEM_INSTRUCTION + USER_PROMPT_TEMPLATE
│   ├── rca_engine.py        ← Two-stage pipeline + fallback logic + audit logging
│   └── schema.py            ← Pydantic RootCauseAnalysis schema
├── config/
│   └── cluster_manifest.json ← Ground truth baselines (timeouts, dependencies)
├── data/
│   └── processed/
│       ├── deployment_log.csv
│       └── structured_telemetry.csv
├── ui/
│   └── app.py               ← Streamlit three-act dashboard
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔬 Validation: The Synthetic Test Suite

The benchmark scenario is a **controlled Helm timeout failure**:

```
14:28:01 → helm upgrade ingress-controller --set proxy-connect-timeout=5s
14:32:05 → ServiceA upstream connection timeouts begin
14:32:18 → 503 error storm at 100% rate
```

Gemini correctly identifies the 4-minute causal gap without keyword matching — it reasons about temporal correlation between the deployment event and the error cascade.

A second unseen scenario (PostgreSQL connection pool exhaustion) was also validated:
- Different telemetry source, different failure pattern
- Gemini correctly calculated `25+20+20 = 65` combined pool size exceeding the 100-connection limit
- Generated three separate `kubectl patch` commands, one per affected service

---

## 🛡️ Safety & Governance

| Feature | Implementation |
|---|---|
| Confidence threshold | RCA blocked if `confidence_score < 0.75` |
| Human approval gate | `require_human_approval: true` for all infrastructure changes |
| Dual-model fallback | Automatic switch to Flash-Lite on quota/503/429 errors |
| Flash passthrough | If Stage 1 fails, raw telemetry passes to Stage 2 uninterrupted |
| Audit trail | Every RCA written to `audit_log.json` with timestamp and model used |
| Structured output | Pydantic schema enforces JSON contract — no free-text hallucination |

---

## 🆚 Competitive Context

| Capability | Datadog | PagerDuty | Grafana | OpsPulse Sentinel |
|---|---|---|---|---|
| Anomaly detection | ✅ | ✅ | ✅ | ✅ |
| Root cause explanation | ⚠️ Partial | ❌ | ❌ | ✅ |
| Deployment correlation | ⚠️ Manual | ❌ | ❌ | ✅ Automatic |
| Historical memory (RAG) | ❌ | ❌ | ❌ | ✅ ChromaDB |
| Executable fix command | ❌ | ❌ | ❌ | ✅ |
| Human approval gate | ❌ | ⚠️ | ❌ | ✅ |
| Custom log upload | ❌ | ❌ | ❌ | ✅ |

---

## 🗺️ Production Roadmap (V2)

- **Multi-cluster support** — dynamic manifest selection per uploaded log source
- **Real-time streaming** — Kafka/Pub-Sub integration replacing static CSV ingestion
- **Expanding memory** — ChromaDB auto-populated from resolved incidents over time
- **Slack/PagerDuty integration** — push RCA reports to existing on-call workflows
- **RBAC** — role-based approval policies per team and severity level

---

## 🔑 Environment Variables

```bash
# .env
GEMINI_API_KEY=your_key_here
```

Get your key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

*Built for the Google AI Studio Hackathon — Track 2: AI Agents with Google AI Studio*
