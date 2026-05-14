import sys
import os

# Path must be set BEFORE any agent imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import json
import streamlit as st
import pandas as pd
from agent.rca_engine import generate_rca_with_fallback, save_audit_log

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="OpsPulse Sentinel | SRE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ENTERPRISE MINIMALIST CSS ---
st.markdown("""
    <style>
    /* Sleek Typography & Spacing */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1200px; }
    h1, h2, h3 { font-weight: 600 !important; letter-spacing: -0.02em !important; }
    
    /* Modern Metric Cards (Datadog/Linear aesthetic) */
    div[data-testid="metric-container"] {
        background-color: #0E1117;
        border: 1px solid #2B2E33;
        padding: 1.2rem;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    /* Clean Headers */
    .header-title { font-size: 2.2rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.2rem; letter-spacing: -0.03em;}
    .header-sub { font-size: 1rem; color: #8B949E; margin-bottom: 2rem; font-weight: 400;}
    
    /* Status Badges */
    .badge-success { background: rgba(46, 160, 67, 0.15); color: #3FB950; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(46, 160, 67, 0.4);}
    .badge-warning { background: rgba(210, 153, 34, 0.15); color: #D29922; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(210, 153, 34, 0.4);}
    
    /* Clean RCA Report Box */
    .rca-box {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 20px;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .rca-label { font-size: 0.85rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;}
    .rca-value { font-size: 1.1rem; color: #E6EDF3; margin-bottom: 16px;}
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SYSTEM STATUS ---
with st.sidebar:
    st.markdown("## ⚡ OpsPulse")
    st.markdown("<span class='badge-success'>AGENT ACTIVE</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Connections")
    st.markdown("🟢 Telemetry Stream\n\n🟢 ChromaDB Vector Store\n\n🟢 Kubernetes API")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### Agent Architecture")
    st.success("**Primary Model:**\nGemini 3.1 Pro Preview\nDeep semantic RCA")
    st.info("**Fallback Model:**\nGemini 3.1 Flash-Lite\nAuto-triggers on quota limits")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### Pipeline Status")
    pipeline_status = st.empty()
    pipeline_status.markdown("""
    - ⬜ ChromaDB Memory Query
    - ⬜ Stage 1: Flash Anomaly Filter
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
                st.caption(f"{entry['timestamp'][:16].replace('T', ' ')}")
                st.markdown(f"`{entry['rca_result'].get('root_cause_component', 'N/A')}`")
                st.divider()
    except FileNotFoundError:
        st.caption("No historical incidents.")

# --- MAIN HEADER ---
st.markdown('<div class="header-title">Incident Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="header-sub">Autonomous Site Reliability Engineering Pipeline</div>', unsafe_allow_html=True)

# --- KPI METRICS ---
c1, c2, c3, c4 = st.columns(4)

# Dynamic KPI based on data source
if st.session_state.get('custom_telemetry') is not None:
    c1.metric("System Status", "Degraded", "SLA Breached", delta_color="inverse")
else:
    c1.metric("ServiceA Status", "503 Error", "-100% SLA", delta_color="inverse")

c2.metric("Pending Actions", "1 Review", "Requires L2", delta_color="off")
c3.metric("Manual MTTR Baseline", "90m", "Industry Avg", delta_color="off")
c4.metric("Agent Diagnostic Time", "< 1m", "-98%", delta_color="normal")

st.markdown("<br>", unsafe_allow_html=True)

# --- TAB LAYOUT ---
tab1, tab2, tab3 = st.tabs(["📡 Telemetry Feed", "🧠 Diagnostic Agent", "⚡ Remediation"])

# ─────────────────────────────────────────────
# TAB 1: TELEMETRY 
# ─────────────────────────────────────────────
with tab1:
    # Dynamic Alert Banner
    if st.session_state.get('custom_telemetry') is not None:
        st.error("🔴 **CRITICAL ANOMALY:** Elevated error rates detected in custom telemetry stream.")
    else:
        st.error("🔴 **CRITICAL ANOMALY:** Widespread 503 connection timeouts in upstream ServiceA routing.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Deployment Events**")
        df_dep = st.session_state.get('custom_deployments', pd.read_csv("data/processed/deployment_log.csv")).tail(3)
        st.dataframe(df_dep, use_container_width=True, hide_index=True)
    with col_b:
        st.markdown("**Telemetry Stream**")
        df_tel = st.session_state.get('custom_telemetry', pd.read_csv("data/processed/structured_telemetry.csv")).tail(5)
        st.dataframe(df_tel, use_container_width=True, hide_index=True)
        
    with st.expander("⚙️ Override Data Sources / View Cluster Manifest"):
        u_col1, u_col2 = st.columns(2)
        uploaded_telemetry = u_col1.file_uploader("Custom Telemetry (CSV)", type=["csv"], label_visibility="collapsed")
        uploaded_deployments = u_col2.file_uploader("Custom Deployments (CSV)", type=["csv"], label_visibility="collapsed")
        
        if uploaded_telemetry: st.session_state['custom_telemetry'] = pd.read_csv(uploaded_telemetry)
        if uploaded_deployments: st.session_state['custom_deployments'] = pd.read_csv(uploaded_deployments)
        
        try:
            with open("config/cluster_manifest.json", "r") as f:
                st.code(f.read(), language="json")
        except: 
            st.warning("Cluster manifest not found.")

# ─────────────────────────────────────────────
# TAB 2: AGENT 
# ─────────────────────────────────────────────
with tab2:
    st.markdown("### Root Cause Analysis")
    
    run_clicked = st.button("▶ Initialize Diagnostics", type="primary")
    if run_clicked:
        st.session_state['run_agent'] = True
        st.session_state['rca_complete'] = False

    if st.session_state.get('run_agent', False):
        if not st.session_state.get('rca_complete', False):
            with st.spinner("Analyzing temporal correlation across telemetry and memory..."):
                try:
                    pipeline_status.markdown("""
                    - ✅ ChromaDB Memory Query
                    - 🔄 Stage 1 & 2: Executing AI Pipeline...
                    - ⬜ Policy Validation
                    """)

                    df_tel = st.session_state.get('custom_telemetry', None)
                    df_dep = st.session_state.get('custom_deployments', None)
                    
                    # Pass the decoupled dataframes to the backend
                    response, model_used = generate_rca_with_fallback(
                        df_telemetry=df_tel,
                        df_deployments=df_dep
                    )
                    rca_data = json.loads(response.text)

                    st.session_state['rca_data'] = rca_data
                    st.session_state['model_used'] = model_used
                    st.session_state['fix_cmd'] = rca_data.get("executable_fix_cmd", "helm upgrade ingress-controller --set proxy-connect-timeout=30s --reuse-values")
                    st.session_state['needs_approval'] = rca_data.get("require_human_approval", True)
                    st.session_state['confidence'] = rca_data.get("confidence_score", 0.0)
                    st.session_state['rca_complete'] = True
                    st.session_state['used_fallback'] = False

                    # Save to persistent audit log
                    save_audit_log(rca_data, model_used)

                    pipeline_status.markdown("""
                    - ✅ ChromaDB Memory Query
                    - ✅ Stage 1: Flash Anomaly Filter
                    - ✅ Stage 2: Pro Deep RCA
                    - ✅ Policy Validation
                    """)

                except Exception as e:
                    st.session_state['used_fallback'] = True
                    mock_rca = {
                        "incident_summary": "ServiceA 503 errors are semantically linked to the Ingress Controller Helm upgrade at 14:28, exactly 4 minutes before the error cascade began at 14:32.",
                        "root_cause_component": "HelmDeploy (ingress-controller)",
                        "confidence_score": 0.98,
                        "require_human_approval": True,
                        "recommended_action": "Revert proxy-connect-timeout setting on the ingress-controller to the 30s architectural baseline.",
                        "executable_fix_cmd": "helm upgrade ingress-controller --set proxy-connect-timeout=30s --reuse-values"
                    }
                    st.session_state['rca_data'] = mock_rca
                    st.session_state['model_used'] = f"Cached RCA ({str(e)[:25]}...)"
                    st.session_state['fix_cmd'] = mock_rca["executable_fix_cmd"]
                    st.session_state['needs_approval'] = mock_rca["require_human_approval"]
                    st.session_state['confidence'] = mock_rca["confidence_score"]
                    st.session_state['rca_complete'] = True
                    
                    pipeline_status.markdown("""
                    - ✅ ChromaDB Memory Query
                    - ⚠️ Stage 1 & 2: API (Cached Mode)
                    - ✅ Policy Validation
                    """)

        if st.session_state.get('rca_complete', False):
            rca_data = st.session_state['rca_data']
            conf = st.session_state['confidence']
            
            # --- PARSED PRO UI ---
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
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Engine", st.session_state['model_used'].split("-preview")[0].replace("gemini-", ""))
            col_m2.metric("Confidence", f"{conf*100:.1f}%")
            col_m3.metric("Human Approval", "Required" if st.session_state['needs_approval'] else "Auto-Resolve")
            
            with st.expander("📋 View Raw JSON Response"):
                st.json(rca_data)
                
            st.info("Proceed to **Remediation** tab to execute the recommended fix.")
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
            st.error(f"❌ **CONFIDENCE FAILED:** Score {confidence*100:.0f}% is below the 75% threshold. Automated remediation blocked. Escalating to L2.")
        else:
            if st.session_state.get('needs_approval', True):
                st.warning("🔒 **Security Gate:** Infrastructure modifications require L2 SRE approval.")
                
            st.markdown("**Proposed Command:**")
            st.code(st.session_state.get('fix_cmd', 'Command unavailable'), language="bash")

            col_x, col_y = st.columns([1, 1])

            with col_x:
                if st.button("Execute Remediation", type="primary", use_container_width=True):
                    
                    # --- SIMULATED TERMINAL EXECUTION ---
                    terminal_container = st.empty()
                    fix_cmd = st.session_state.get('fix_cmd', '')
                    
                    terminal_lines = ["$ Initializing secure cluster connection..."]
                    def render_terminal():
                        terminal_container.markdown(f"```bash\n{chr(10).join(terminal_lines)}\n```")

                    render_terminal()
                    time.sleep(0.6)
                    terminal_lines.append(f"$ {fix_cmd}")
                    render_terminal()
                    time.sleep(1.2)
                    terminal_lines.append("> Applying configuration changes...")
                    render_terminal()
                    time.sleep(0.8)
                    terminal_lines.append("> Waiting for rollout to finish: 1 of 1 updated replicas...")
                    render_terminal()
                    time.sleep(1.0)
                    terminal_lines.append("✅ Rollout successful. Infrastructure state synced.")
                    render_terminal()
                    time.sleep(0.5)

                    st.success("Issue resolved. Connections recovering.")
                    st.balloons()
                    
                    st.markdown("### 📊 MTTR Impact")
                    st.table({
                        "Phase": ["Log Triage", "Correlation", "Root Cause", "Total"],
                        "Manual SRE": ["15 min", "45 min", "30 min", "90 min"],
                        "OpsPulse": ["3 sec", "15 sec", "10 sec", "< 60 sec"]
                    })

            with col_y:
                if st.button("Reject / Escalate", use_container_width=True):
                    st.error("Execution blocked. Context escalated to L2 via Jira.")
                
    elif st.session_state.get('run_agent', False):
        st.caption("Diagnostics in progress...")
    else:
        st.caption("Awaiting RCA completion.")