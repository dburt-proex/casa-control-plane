import streamlit as st
import requests
import pandas as pd
import os
import hashlib
import hmac

st.set_page_config(
    page_title="CASA Governance Dashboard",
    layout="wide"
)

# Configuration for local vs cloud deployment
# Local: http://127.0.0.1:5000
# Cloud: Set API_URL environment variable to your deployed API endpoint
API_URL = os.getenv("CASA_API_URL", "http://127.0.0.1:5000")

# Stripe configuration (set STRIPE_PAYMENT_LINK env var for live integration)
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "")

# ------------------------------------------------
# Login
# ------------------------------------------------

def _check_password(username: str, password: str) -> bool:
    """Verify username and password against environment-configured credentials.

    Credentials are supplied via environment variables:
      LOGIN_USERNAME      – allowed username (default: admin)
      LOGIN_PASSWORD_HASH – SHA-256 hex digest of the password (default: hash of "casa-demo")
    """
    expected_user = os.getenv("LOGIN_USERNAME", "admin")
    default_hash = hashlib.sha256(b"casa-demo").hexdigest()
    expected_hash = os.getenv("LOGIN_PASSWORD_HASH", default_hash)

    user_ok = username.strip() == expected_user
    pass_hash = hashlib.sha256(password.encode()).hexdigest()
    pass_ok = hmac.compare_digest(pass_hash, expected_hash)
    return user_ok and pass_ok


def show_login_form() -> bool:
    """Render login form and return True when the user is authenticated."""
    st.title("🔐 CASA Governance Dashboard")
    st.subheader("Please log in to continue")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if _check_password(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Incorrect username or password.")

    return st.session_state.get("authenticated", False)


# Guard: require authentication before rendering the dashboard
if not st.session_state.get("authenticated", False):
    show_login_form()
    st.stop()

st.title("CASA AI Governance Control Plane")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Logged-in user info and logout
    st.write(f"👤 **{st.session_state.get('username', 'User')}**")
    if st.button("Log out"):
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)
        st.rerun()

    st.divider()

    # Allow override of API URL for cloud deployment
    with st.expander("API Settings", expanded=False):
        api_url_input = st.text_input(
            "API Endpoint URL",
            value=API_URL,
            help="For local development: http://127.0.0.1:5000\nFor cloud deployment: your deployed API URL"
        )
        if api_url_input and api_url_input != API_URL:
            API_URL = api_url_input

    st.divider()

    # Stripe upgrade prompt (only shown when a payment link is configured)
    if STRIPE_PAYMENT_LINK:
        st.subheader("💳 Upgrade to Pro")
        st.write("Unlock unlimited decision history, advanced analytics, and dedicated support.")
        st.link_button("Upgrade now →", STRIPE_PAYMENT_LINK, use_container_width=True)
        st.divider()

    st.caption("CASA v1.0 - Enterprise Governance Dashboard")
    st.caption(f"📍 API: {API_URL}")


# Fetch API Data

def fetch_dashboard():
    try:
        return requests.get(f"{API_URL}/dashboard", timeout=5).json()
    except Exception as e:
        st.error(f"Failed to fetch dashboard data: {e}")
        return None

def fetch_stress():
    try:
        return requests.get(f"{API_URL}/boundary-stress", timeout=5).json()
    except Exception as e:
        st.error(f"Failed to fetch stress data: {e}")
        return None

def fetch_text_dashboard():
    try:
        return requests.get(f"{API_URL}/dashboard/text", timeout=5).text
    except Exception as e:
        st.error(f"Failed to fetch text dashboard: {e}")
        return None

# Add refresh button
col1, col2 = st.columns([10, 1])
with col2:
    if st.button("🔄 Refresh"):
        st.rerun()

dashboard = fetch_dashboard()
stress = fetch_stress()

if dashboard is None or stress is None:
    st.error("❌ Unable to connect to CASA API")
    
    if API_URL == "http://127.0.0.1:5000":
        st.warning("**Local Deployment:** API server not running")
        st.info("""
        Start the API server locally:
        ```bash
        python -m uvicorn governance_api:app --host 127.0.0.1 --port 5000
        ```
        Then refresh this page.
        """)
    else:
        st.warning("**Cloud Deployment:** Unable to reach API endpoint")
        st.info(f"""
        Current API URL: `{API_URL}`
        
        **Options:**
        1. Deploy CASA API to your cloud provider (Heroku, AWS, Azure, etc.)
        2. Use the sidebar to configure a custom API endpoint
        3. Run locally with: `python -m uvicorn governance_api:app --host 127.0.0.1 --port 5000`
        
        Then set environment variable: `CASA_API_URL=your-api-url`
        """)
    st.stop()

# -----------------------------
# System Status
# -----------------------------

st.header("System Status")

col1, col2, col3, col4 = st.columns(4)

col1.metric("System Mode", dashboard.get("system_mode", "UNKNOWN"))
col2.metric("Policy Version", dashboard.get("policy_version", "N/A"))
col3.metric("Ledger Integrity", dashboard.get("ledger_integrity", "N/A"))

stress_score = stress.get("stress_score", 0)
stress_color = "🟢" if stress_score < 0.3 else "🟡" if stress_score < 0.6 else "🔴"
col4.metric("Boundary Stress", f"{stress_color} {round(stress_score, 2)}")

# Display system state
system_state = stress.get("system_state", "UNKNOWN")
if system_state == "STABLE":
    st.success(f"✓ System State: {system_state}")
elif system_state == "CAUTION":
    st.warning(f"⚠ System State: {system_state}")
else:
    st.error(f"✗ System State: {system_state}")

# -----------------------------
# Gate Distribution
# -----------------------------

st.header("Gate Decisions")

gate_dist = dashboard.get("gate_distribution", {})
gate_data = {
    "Gate": ["ALLOW", "REVIEW", "HALT"],
    "Percent": [
        gate_dist.get("allow", 0),
        gate_dist.get("review", 0),
        gate_dist.get("halt", 0)
    ]
}

df = pd.DataFrame(gate_data)

col1, col2 = st.columns([2, 1])
with col1:
    st.bar_chart(df.set_index("Gate"))

with col2:
    st.metric("Total Decisions", dashboard.get("total_decisions", 0))
    st.metric("ALLOW Rate", f"{gate_dist.get('allow', 0):.1f}%")
    st.metric("REVIEW Rate", f"{gate_dist.get('review', 0):.1f}%")
    st.metric("HALT Rate", f"{gate_dist.get('halt', 0):.1f}%")

# -----------------------------
# Boundary Stress Panel
# -----------------------------

st.header("Boundary Stress Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Near Threshold %",
    f"{stress.get('near_threshold_decisions_pct', 0):.1f}%",
    help="Decisions operating close to policy boundaries"
)
col2.metric(
    "Tier2 Hits",
    stress.get("tier2_boundary_hits", 0),
    help="Secondary boundary violations detected"
)
col3.metric(
    "Drift Acceleration",
    f"{stress.get('drift_acceleration', 0):.2f}",
    help="Rate of change in agent behavior"
)
col4.metric(
    "Confidence Drop %",
    f"{stress.get('confidence_degradation_pct', 0):.1f}%",
    help="Decline in decision confidence"
)

# Show warnings if any
warnings = stress.get("warnings", [])
if warnings:
    st.warning(f"⚠️ {len(warnings)} Warning(s) Generated:")
    for warning in warnings:
        st.write(f"  • {warning}")

# Stress breakdown
st.subheader("Stress Score Breakdown")
breakdown = stress.get("breakdown", {})
cols = st.columns(4)
for i, (metric, value) in enumerate(breakdown.items()):
    cols[i % 4].write(f"**{metric}**: {value:.3f}")

# -----------------------------
# Drift Monitoring
# -----------------------------

st.header("Drift Monitoring")

drift = dashboard.get("drift", {})

col1, col2, col3 = st.columns(3)

col1.metric(
    "Drift Index Avg",
    f"{drift.get('avg', 0):.3f}",
    help="Average behavioral drift across agents"
)
col2.metric(
    "Volatility Events",
    drift.get("volatility_events", 0),
    help="Sudden changes in decision pattern"
)
col3.metric(
    "Anomalies Detected",
    drift.get("anomaly_count", 0),
    help="Statistically anomalous decisions"
)

if drift.get("max", 0) > 0.5:
    st.warning(f"⚠️ High drift detected (max: {drift.get('max', 0):.3f})")

# -----------------------------
# Decision Replay Impact
# -----------------------------

st.header("Policy Impact Analysis")

replay = dashboard.get("replay", {})

col1, col2, col3 = st.columns(3)

col1.metric(
    "Decisions Replayed",
    replay.get("total", 0),
    help="Historical decisions tested under current policy"
)
col2.metric(
    "Routing Changes",
    replay.get("routing_changes", 0),
    help="Decisions that would route differently"
)
col3.metric(
    "Policy Delta %",
    f"{replay.get('policy_delta', 0):.1f}%",
    help="Percentage of decisions affected by policy changes"
)

# Risk delta
col1, col2 = st.columns(2)
col1.metric(
    "Risk Delta",
    f"{replay.get('avg_risk_delta', 0):+.2f}",
    help="Average change in risk assessment"
)
col2.metric(
    "Confidence Shift",
    f"{replay.get('avg_confidence_shift', 0):+.1f}%",
    help="Average change in decision confidence"
)

# -----------------------------
# Risk Classification
# -----------------------------

st.header("Risk Profile")

risk_profile = dashboard.get("risk_profile", {})

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "LOW Risk %",
    f"{risk_profile.get('low', 0):.1f}%"
)
col2.metric(
    "MEDIUM Risk %",
    f"{risk_profile.get('medium', 0):.1f}%"
)
col3.metric(
    "HIGH Risk %",
    f"{risk_profile.get('high', 0):.1f}%"
)
col4.metric(
    "CRITICAL Risk %",
    f"{risk_profile.get('critical', 0):.1f}%"
)

# Risk trend
if risk_profile.get("critical", 0) > 5:
    st.error(f"🔴 CRITICAL risk elevated at {risk_profile.get('critical', 0):.1f}%")
elif risk_profile.get("high", 0) > 15:
    st.warning(f"🟡 HIGH risk at {risk_profile.get('high', 0):.1f}%")
else:
    st.success(f"✓ Risk profile nominal")

# -----------------------------
# Ledger Health
# -----------------------------

st.header("Ledger Status")

ledger = dashboard.get("ledger", {})

col1, col2, col3 = st.columns(3)

col1.metric(
    "Ledger Blocks",
    ledger.get("blocks", 0),
    help="Number of decision blocks recorded"
)
col2.metric(
    "Tamper Events",
    ledger.get("tamper_events", 0),
    help="Detected integrity violations (should be 0)"
)
col3.metric(
    "Integrity Status",
    "✓ VERIFIED" if ledger.get("tamper_events", 0) == 0 else "✗ COMPROMISED",
    help="Cryptographic ledger verification"
)

# Integrity warning
if ledger.get("tamper_events", 0) > 0:
    st.error("🔴 LEDGER INTEGRITY COMPROMISED - Immediate investigation required!")

# Ledger chain status
if ledger.get("chain_status", ""):
    st.info(f"Chain Status: {ledger.get('chain_status', 'Unknown')}")

# Hash verification
if ledger.get("hash_verified", False):
    st.success("✓ SHA-256 Hash Chain Verified")
else:
    st.warning("⚠️ Hash chain verification pending")

# -----------------------------
# Text Dashboard
# -----------------------------

st.header("Raw Text Dashboard")

text_dashboard = fetch_text_dashboard()
if text_dashboard:
    st.code(text_dashboard, language="text")

# -----------------------------
# Pricing / Stripe
# -----------------------------

st.header("💳 Plans & Pricing")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🆓 Free")
    st.write("**$0 / month**")
    st.write("- Up to 1,000 governance decisions/month")
    st.write("- Basic dashboard")
    st.write("- Community support")
    st.write("- 7-day ledger retention")
    st.write("---")
    st.caption("Current plan")

with col2:
    st.subheader("🚀 Pro")
    st.write("**$99 / month**")
    st.write("- Unlimited governance decisions")
    st.write("- Full analytics dashboard")
    st.write("- Priority email support")
    st.write("- 1-year ledger retention")
    st.write("- Policy dry-run simulator")
    if STRIPE_PAYMENT_LINK:
        st.link_button("Upgrade to Pro →", STRIPE_PAYMENT_LINK, use_container_width=True, type="primary")
    else:
        st.info("Contact us to upgrade")

with col3:
    st.subheader("🏢 Enterprise")
    st.write("**Custom pricing**")
    st.write("- Everything in Pro")
    st.write("- Dedicated SLA")
    st.write("- On-premise deployment")
    st.write("- Regulatory compliance pack")
    st.write("- Custom integrations")
    st.link_button("Contact Sales →", "mailto:sales@casa-governance.ai", use_container_width=True)

st.markdown("---")
st.caption("🔒 Payments securely processed by [Stripe](https://stripe.com)")

# -----------------------------
# Footer
# -----------------------------

st.divider()

if all([
    stress.get("stress_score", 0) < 0.3,
    ledger.get("tamper_events", 0) == 0,
    system_state == "STABLE"
]):
    st.success("✓ CASA Governance System Fully Operational")
else:
    st.warning("⚠️ System requires attention - review metrics above")

st.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("CASA AI Governance Control Plane v1.0")
