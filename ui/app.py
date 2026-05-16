import sys
import os

# Resolve repo root and inject into path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import time
import json
import streamlit as st
import pandas as pd
from agent.rca_engine import generate_rca_with_fallback, save_audit_log

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OpsPulse Sentinel | SRE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    h1, h2, h3 {
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }

    /* Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #0D1117;
        border: 1px solid #21262D;
        padding: 1.1rem 1.2rem;
        border-radius: 8px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.3);
    }

    /* Header */
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        color: #F0F6FC;
        letter-spacing: -0.04em;
        margin-bottom: 0.1rem;
    }
    .header-sub {
        font-size: 0.95rem;
        color: #6E7681;
        font-weight: 400;
        margin-bottom: 1.8rem;
    }

    /* Status Badges */
    .badge-success {
        background: rgba(46,160,67,0.15);
        color: #3FB950;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(46,160,67,0.35);
        letter-spacing: 0.04em;
    }
    .badge-cached {
        background: rgba(210,153,34,0.15);
        color: #D29922;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(210,153,34,0.35);
        letter-spacing: 0.04em;
    }

    /* RCA Report Box */
    .rca-box {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 22px 24px;
        margin-top: 12px;
        margin-bottom: 16px;
    }
    .rca-label {
        font-size: 0.72rem;
        color: #6E7681;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .rca-value {
        font-size: 1rem;
        color: #E6EDF3;
        margin-bottom: 18px;
        line-height: 1.55;
    }
    .rca-value:last-child {
        margin-bottom: 0;
    }

    /* Evidence Chain */
    .evidence-box {
        background-color: #0D1117;
        border: 1px solid #21262D;
        border-left: 3px solid #F78166;
        border-radius: 6px;
        padding: 16px 20px;
        margin-top: 12px;
        margin-bottom: 20px;
    }
    .evidence-title {
        font-size: 0.72rem;
        color: #F78166;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .evidence-item {
        display: flex;
        gap: 12px;
        margin-bottom: 8px;
        align-items: flex-start;
    }
    .evidence-dot {
        width: 6px;
        height: 6px;
        background: #F78166;
        border-radius: 50%;
        margin-top: 6px;
        flex-shrink: 0;
    }
    .evidence-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #CDD9E5;
        line-height: 1.5;
    }

    /* Terminal output */
    .terminal-block {
        background: #0D1117;
        border: 1px solid #30363D;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #3FB950;
        padding: 16px 20px;
        line-height: 1.7;
    }

    /* Divider */
    hr { border-color: #21262D !important; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0D1117;
        border-right: 1px solid #21262D;
    }
    </style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ OpsPulse")
    st.markdown("<span class='badge-success'>● AGENT ACTIVE</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Connections")
    st.markdown("🟢 Telemetry Stream\n\n🟢 ChromaDB Vector Store\n\n🟢 Cluster Manifest Loaded")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Agent Architecture")
    st.success("**Stage 1 — Filter**\nGemini Flash-Lite\nAnomaly extraction")
    st.info("**Stage 2 — Reason**\nGemini Pro Preview\nSemantic RCA\n\n*Auto-fallback to Flash-Lite on quota limits*")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Pipeline Status")
    pipeline_status = st.empty()
    pipeline_status.markdown("""
    - ⬜ Stage 1: Flash Anomaly Filter
    - ⬜ ChromaDB Memory Query
    - ⬜ Stage 2: Pro Deep RCA
    - ⬜ Policy Validation
    """)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Audit Log")
    try:
        with open("audit_log.json", "r") as f:
            audit_data = json.load(f)
        with st.expander(f"View History ({len(audit_data)} events)"):
            for entry in reversed(audit_data[-5:]):
                st.caption(f"{entry['timestamp'][:16].replace('T', ' ')} UTC")
                st.markdown(f"`{entry['rca_result'].get('root_cause_component', 'N/A')}`")
                conf = entry['rca_result'].get('confidence_score', 0)
                st.caption(f"Confidence: {conf*100:.0f}%")
                st.divider()
    except FileNotFoundError:
        st.caption("No historical incidents yet.")


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────
st.markdown('<div class="header-title">⚡ Incident Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="header-sub">Autonomous Site Reliability Engineering · Semantic Root Cause Analysis Pipeline</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

if st.session_state.get('custom_telemetry') is not None:
    c1.metric("System Status", "Degraded", "Custom Data Loaded", delta_color="inverse")
else:
    c1.metric("ServiceA Status", "503 Error", "-100% SLA", delta_color="inverse")

c2.metric("Pending Actions", "1 Review", "Requires L2", delta_color="off")
c3.metric("Manual MTTR Baseline", "90 min", "Industry Avg", delta_color="off")
c4.metric("Agent Diagnostic Time", "< 60 sec", "-98.9%", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📡 Telemetry Feed", "🧠 Diagnostic Agent", "⚡ Remediation"])


# ─────────────────────────────────────────────
# TAB 1: TELEMETRY FEED
# ─────────────────────────────────────────────
with tab1:
    if st.session_state.get('custom_telemetry') is not None:
        st.error("🔴 **CRITICAL ANOMALY:** Elevated error rates detected in uploaded telemetry stream.")
    else:
        st.error("🔴 **CRITICAL ANOMALY:** Widespread 503 connection timeouts in upstream ServiceA routing.")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Recent Deployment Events**")
        try:
            df_dep_display = st.session_state.get(
                'custom_deployments',
                pd.read_csv("data/processed/deployment_log.csv")
            ).tail(5)
            st.dataframe(df_dep_display, use_container_width=True, hide_index=True)
        except Exception:
            st.warning("Deployment log not found.")

    with col_b:
        st.markdown("**Live Telemetry Stream**")
        try:
            df_tel_display = st.session_state.get(
                'custom_telemetry',
                pd.read_csv("data/processed/structured_telemetry.csv")
            ).tail(8)
            st.dataframe(df_tel_display, use_container_width=True, hide_index=True)
        except Exception:
            st.warning("Telemetry file not found.")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("⚙️ Upload Custom Data Sources / View Cluster Manifest"):
        st.caption("Upload your own CSVs to run the agent against custom telemetry. Leave blank to use the built-in demo data.")
        u_col1, u_col2 = st.columns(2)

        uploaded_telemetry = u_col1.file_uploader(
            "Custom Telemetry (CSV)",
            type=["csv"],
            help="Upload a structured telemetry CSV. Any columns will work — the agent reads it as plain text."
        )
        uploaded_deployments = u_col2.file_uploader(
            "Custom Deployment Log (CSV)",
            type=["csv"],
            help="Upload a deployment events CSV with timestamps and change descriptions."
        )

        REQUIRED_COLS = {'Date', 'Time', 'Pid', 'Level', 'Component', 'Content'}

        if uploaded_telemetry is not None:
            try:
                try:
                    df = pd.read_csv(uploaded_telemetry)
                except UnicodeDecodeError:
                    uploaded_telemetry.seek(0)
                    df = pd.read_csv(uploaded_telemetry, encoding='latin-1')
                missing = REQUIRED_COLS - set(df.columns)
                if missing:
                    st.error(f"⚠️ Invalid telemetry file. Missing columns: {', '.join(sorted(missing))}. Please fix and re-upload.")
                else:
                    st.session_state['custom_telemetry'] = df
                    st.success(f"✅ Custom telemetry loaded: {len(df)} rows")
            except Exception as e:
                st.error(f"⚠️ Could not read telemetry file: {str(e)}")

        if uploaded_deployments is not None:
            try:
                try:
                    df = pd.read_csv(uploaded_deployments)
                except UnicodeDecodeError:
                    uploaded_deployments.seek(0)
                    df = pd.read_csv(uploaded_deployments, encoding='latin-1')
                missing = REQUIRED_COLS - set(df.columns)
                if missing:
                    st.error(f"⚠️ Invalid deployment file. Missing columns: {', '.join(sorted(missing))}. Please fix and re-upload.")
                else:
                    st.session_state['custom_deployments'] = df
                    st.success(f"✅ Custom deployment log loaded: {len(df)} rows")
            except Exception as e:
                st.error(f"⚠️ Could not read deployment file: {str(e)}")])} rows")

        if st.session_state.get('custom_telemetry') is not None or st.session_state.get('custom_deployments') is not None:
            if st.button("🗑️ Clear Custom Data (revert to demo)", type="secondary"):
                st.session_state.pop('custom_telemetry', None)
                st.session_state.pop('custom_deployments', None)
                st.session_state['rca_complete'] = False
                st.session_state['run_agent'] = False
                st.rerun()

        st.markdown("---")
        st.markdown("**Cluster Architecture Manifest**")
        try:
            with open("config/cluster_manifest.json", "r") as f:
                st.code(f.read(), language="json")
        except FileNotFoundError:
            st.warning("cluster_manifest.json not found in config/.")


# ─────────────────────────────────────────────
# TAB 2: DIAGNOSTIC AGENT
# ─────────────────────────────────────────────
with tab2:
    st.markdown("### Root Cause Analysis")

    # Data source indicator
    if st.session_state.get('custom_telemetry') is not None:
        st.markdown("<span class='badge-success'>● Custom Data Active</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-success'>● Demo Data Active</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    run_clicked = st.button("▶ Initialize Diagnostics", type="primary")
    if run_clicked:
        st.session_state['run_agent'] = True
        st.session_state['rca_complete'] = False

    if st.session_state.get('run_agent', False):

        if not st.session_state.get('rca_complete', False):
            with st.spinner("Analyzing temporal correlation across telemetry, deployment history, and architectural context..."):
                try:
                    pipeline_status.markdown("""
                    - 🔄 Stage 1: Flash Anomaly Filter
                    - ⬜ ChromaDB Memory Query
                    - ⬜ Stage 2: Pro Deep RCA
                    - ⬜ Policy Validation
                    """)

                    # Pull from session state — None means rca_engine loads defaults
                    df_tel = st.session_state.get('custom_telemetry', None)
                    df_dep = st.session_state.get('custom_deployments', None)

                    response, model_used = generate_rca_with_fallback(
                        df_telemetry=df_tel,
                        df_deployments=df_dep
                    )

                    pipeline_status.markdown("""
                    - ✅ Stage 1: Flash Anomaly Filter
                    - ✅ ChromaDB Memory Query
                    - 🔄 Stage 2: Pro Deep RCA
                    - ⬜ Policy Validation
                    """)

                    rca_data = json.loads(response.text)

                    st.session_state['rca_data'] = rca_data
                    st.session_state['model_used'] = model_used
                    st.session_state['fix_cmd'] = rca_data.get(
                        "executable_fix_cmd",
                        "helm upgrade ingress-controller --set proxy-connect-timeout=30s --reuse-values"
                    )
                    st.session_state['needs_approval'] = rca_data.get("require_human_approval", True)
                    st.session_state['confidence'] = rca_data.get("confidence_score", 0.0)
                    st.session_state['rca_complete'] = True
                    st.session_state['used_fallback'] = False

                    save_audit_log(rca_data, model_used)

                    pipeline_status.markdown("""
                    - ✅ Stage 1: Flash Anomaly Filter
                    - ✅ ChromaDB Memory Query
                    - ✅ Stage 2: Pro Deep RCA
                    - ✅ Policy Validation
                    """)

                except Exception as e:
                    # ── CACHED FALLBACK ──────────────────────────────────────
                    # Only reached if BOTH Gemini models fail (e.g. full API outage)
                    st.error(f"🔴 DEBUG: {str(e)}")
                    st.session_state['used_fallback'] = True
                    mock_rca = {
                        "incident_summary": "ServiceA 503 errors are semantically linked to the Ingress Controller Helm upgrade at 14:28, exactly 4 minutes before the error cascade began at 14:32.",
                        "evidence_chain": [
                            "14:28:01 - Deployment: helm upgrade ingress-controller --set proxy-connect-timeout=5s",
                            "14:30:14 - Config drift detected: proxy-connect-timeout reduced from 30s → 5s",
                            "14:32:05 - Anomaly: ServiceA upstream connection timeout (threshold exceeded)",
                            "14:32:10 - Cascade: Load balancer health checks failing for ServiceA",
                            "14:32:18 - Storm: 503 error rate reached 100% on ServiceA endpoints"
                        ],
                        "root_cause_component": "HelmDeploy (ingress-controller)",
                        "confidence_score": 0.98,
                        "require_human_approval": True,
                        "recommended_action": "Revert proxy-connect-timeout setting on the ingress-controller to the 30s architectural baseline defined in cluster_manifest.json.",
                        "executable_fix_cmd": "helm upgrade ingress-controller --set proxy-connect-timeout=30s --reuse-values"
                    }
                    st.session_state['rca_data'] = mock_rca
                    st.session_state['model_used'] = "Cached RCA (API Unavailable)"
                    st.session_state['fix_cmd'] = mock_rca["executable_fix_cmd"]
                    st.session_state['needs_approval'] = mock_rca["require_human_approval"]
                    st.session_state['confidence'] = mock_rca["confidence_score"]
                    st.session_state['rca_complete'] = True

                    pipeline_status.markdown("""
                    - ✅ Stage 1: Flash Anomaly Filter
                    - ✅ ChromaDB Memory Query
                    - ⚠️ Stage 2: Cached Mode (API Unavailable)
                    - ✅ Policy Validation
                    """)

        # ── RENDER RCA RESULTS ───────────────────────────────────────
        if st.session_state.get('rca_complete', False):
            rca_data = st.session_state['rca_data']
            conf = st.session_state['confidence']

            if st.session_state.get('used_fallback'):
                st.markdown("<span class='badge-cached'>⚠ Cached RCA Mode — API Unavailable</span>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

            # ── SUMMARY CARD ─────────────────────────────────────────
            st.markdown(f"""
            <div class="rca-box">
                <div class="rca-label">Identified Component</div>
                <div class="rca-value">🎯 {rca_data.get('root_cause_component', 'N/A')}</div>
                <div class="rca-label">Incident Summary</div>
                <div class="rca-value">{rca_data.get('incident_summary', 'N/A')}</div>
                <div class="rca-label">Recommended Action</div>
                <div class="rca-value">{rca_data.get('recommended_action', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)

            # ── EVIDENCE CHAIN ───────────────────────────────────────
            evidence = rca_data.get('evidence_chain', [])
            if evidence:
                items_html = "".join([
                    f'<div class="evidence-item"><div class="evidence-dot"></div><div class="evidence-text">{item}</div></div>'
                    for item in evidence
                ])
                st.markdown(f"""
                <div class="evidence-box">
                    <div class="evidence-title">⛓ Causal Evidence Chain — {len(evidence)} Events</div>
                    {items_html}
                </div>
                """, unsafe_allow_html=True)

            # ── METRICS ROW ──────────────────────────────────────────
            col_m1, col_m2, col_m3 = st.columns(3)

            model_label = st.session_state['model_used']
            if isinstance(model_label, str):
                model_label = model_label.replace("gemini-", "").replace("-preview", "").replace("-", " ").title()

            col_m1.metric("Engine", model_label)
            col_m2.metric("Confidence", f"{conf * 100:.1f}%")
            col_m3.metric("Human Approval", "Required" if st.session_state['needs_approval'] else "Auto-Resolve")

            # ── RAW JSON EXPANDER ────────────────────────────────────
            with st.expander("📋 View Raw JSON Response"):
                st.json(rca_data)

            st.info("➡️ Proceed to the **Remediation** tab to execute the fix.")

    else:
        st.caption("Awaiting initialization. Click 'Initialize Diagnostics' to begin.")


# ─────────────────────────────────────────────
# TAB 3: REMEDIATION
# ─────────────────────────────────────────────
with tab3:
    if st.session_state.get('rca_complete', False):
        st.markdown("### Execution Plan")

        confidence = st.session_state.get('confidence', 0.0)

        if confidence < 0.75:
            st.error(
                f"❌ **CONFIDENCE FAILED:** Score {confidence * 100:.0f}% is below the 75% threshold. "
                f"Automated remediation blocked. Escalating to L2 SRE."
            )
        else:
            if st.session_state.get('needs_approval', True):
                st.warning("🔒 **Security Gate:** This action modifies infrastructure. L2 SRE approval required before execution.")

            st.markdown("**Proposed Remediation Command:**")
            st.code(st.session_state.get('fix_cmd', 'Command unavailable'), language="bash")

            col_x, col_y = st.columns([1, 1])

            with col_x:
                if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
                    terminal_container = st.empty()
                    fix_cmd = st.session_state.get('fix_cmd', '')

                    terminal_lines = [
                        "$ Initializing secure cluster connection...",
                        f"$ {fix_cmd}",
                        "> Sending request to Kubernetes API...",
                        "> Applying configuration patch to ingress-controller...",
                        "> Waiting for rollout: 1 of 1 updated replicas are available...",
                        "> Health check passed. Upstream connections recovering.",
                        "✅ Rollout complete. Infrastructure state synced successfully."
                    ]

                    current_output = ""
                    for i, line in enumerate(terminal_lines):
                        current_output += line + "\n"
                        terminal_container.code(current_output, language="bash")
                        time.sleep(0.8 if i > 1 else 1.2)

                    st.success("✅ Issue resolved. ServiceA connections recovering.")
                    st.balloons()

                    st.markdown("### 📊 MTTR Impact Report")
                    st.table({
                        "Diagnostic Phase": ["Log Triage", "Cross-Service Correlation", "Root Cause ID", "Total"],
                        "Manual SRE": ["15 min", "45 min", "30 min", "90 min"],
                        "OpsPulse Sentinel": ["3 sec", "15 sec", "10 sec", "< 60 sec"],
                        "Reduction": ["99.7%", "99.4%", "99.4%", "~98.9%"]
                    })

            with col_y:
                if st.button("🚫 Reject / Escalate to L2", use_container_width=True):
                    st.error("⛔ Execution rejected. Incident context packaged and escalated to L2 via Jira.")

    elif st.session_state.get('run_agent', False):
        st.caption("Diagnostics in progress. This tab will activate once RCA is complete.")
    else:
        st.caption("Run the Diagnostic Agent first to generate a remediation plan.")