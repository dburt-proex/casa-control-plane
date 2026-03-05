# CASA  
## Control Awareness System Architecture  
Deterministic Governance Control Plane for Autonomous Systems

---

## 🚀 Demo Site

> **Live demo:** Deploy with the one-click buttons below, then open the Streamlit dashboard.
>
> Default login — **username:** `admin` **password:** `casa-demo`
>
> [![Deploy API to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
> &nbsp;&nbsp;
> [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/cloud)

---

## Quick Start (local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate demo data
python demo_setup.py stable

# 3. Start the CASA API
uvicorn governance_api:app --host 127.0.0.1 --port 5000

# 4. In a second terminal, start the Streamlit dashboard
streamlit run streamlit_app.py
#    → open http://localhost:8501
#    → login: admin / casa-demo
```

---

## Cloud Deployment

### Option A — Render (recommended)

1. Fork this repo
2. In [Render](https://render.com), create a new **Blueprint** and point it at your fork
3. Render will read `render.yaml` and create both services automatically
4. Set the environment variables below in the Render dashboard

### Option B — Heroku

```bash
heroku create your-casa-api
git push heroku main
heroku config:set CORS_ORIGINS=https://your-dashboard.streamlit.app
```

### Option C — Streamlit Community Cloud (dashboard only)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select `streamlit_app.py`
3. Add secrets under **Advanced settings**:
   ```
   CASA_API_URL = "https://your-api.onrender.com"
   LOGIN_USERNAME = "admin"
   LOGIN_PASSWORD_HASH = "<sha256 hex of your password>"
   STRIPE_PAYMENT_LINK = "https://buy.stripe.com/..."
   ```

---

## Environment Variables

| Variable | Service | Description | Default |
|---|---|---|---|
| `CASA_API_URL` | Dashboard | URL of the deployed CASA API | `http://127.0.0.1:5000` |
| `CORS_ORIGINS` | API | Comma-separated allowed origins | `*` |
| `LOGIN_USERNAME` | Dashboard | Dashboard login username | `admin` |
| `LOGIN_PASSWORD_HASH` | Dashboard | SHA-256 hex digest of the password | hash of `casa-demo` |
| `STRIPE_PUBLISHABLE_KEY` | Dashboard | Stripe publishable key | _(none)_ |
| `STRIPE_PAYMENT_LINK` | Dashboard | Stripe payment link URL for Pro plan | _(none)_ |

Generate a password hash:
```bash
python -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
```

---

## Stripe Integration

The dashboard includes a **Plans & Pricing** section powered by Stripe.

1. In your [Stripe dashboard](https://dashboard.stripe.com), create a **Payment Link** for the Pro plan
2. Copy the payment link URL
3. Set `STRIPE_PAYMENT_LINK=https://buy.stripe.com/...` in your deployment environment
4. Optionally set `STRIPE_PUBLISHABLE_KEY` to display a Stripe-powered badge

---



CASA is a deterministic control plane that governs autonomous and semi-autonomous AI systems.

It installs enforceable execution boundaries between reasoning and real-world action.

CASA ensures that:

- All actions are explicitly authorized
- High-risk operations require escalation
- Boundary violations are blocked deterministically
- Every decision is replayable
- Governance is version-controlled and machine-detectable

CASA operates **above orchestration** and **below human authority**.

It is infrastructure — not a wrapper, not a model, and not a compliance checklist.

---

## Core Thesis

Autonomy becomes deployable when:

1. Control boundaries are explicit  
2. Risk signals are measurable  
3. Routing is deterministic  
4. Decisions are reconstructable  

Without architectural control, governance degrades under optimization pressure.

---

## Closed Gate States

CASA enforces a closed execution state set:

- `AUTO` — Low risk, allowed to execute  
- `REVIEW` — Human approval required  
- `HALT` — Execution blocked  

No other execution state exists.

---

## System Architecture
Human Authority
│
Policy Layer
│
AI Reasoning System
│
CASA Control Plane
│
Execution Router
│
Tools / APIs / State Changes
│
Immutable Audit Ledger

Agents never execute tools directly.  
All execution passes through CASA.

---

## Architectural Layers

### Layer 1 — Instruction Control
Locks intent and binds constraints prior to execution.

### Layer 2 — Signal Instrumentation
Extracts measurable governance signals:
- Drift indicators
- Tool risk
- Permission risk
- Data exposure risk
- Context volatility

### Layer 3 — Risk & Confidence Model
Computes:
- `risk_score` (0–100 composite)
- `confidence` (0–1 bounded)

Hard violations override scoring.

### Layer 4 — Deterministic Gate Engine

```python
if hard_violation:
    return HALT
elif risk_score >= review_threshold:
    return REVIEW
elif confidence < min_confidence:
    return REVIEW
else:
    return AUTO
Layer 5 — Execution Router

Routes actions based strictly on gate outcome.

Layer 6 — Immutable Audit Ledger (IDEL)

Every decision records:

policy_version

signals_snapshot

risk_score

confidence

gate_outcome

execution_result

previous_hash

Ledger is append-only and replayable.

Layer 7 — Safety State Machine

System states:

NORMAL

DEGRADED

SAFE_MODE

SAFE_MODE prohibits irreversible actions.

Invariant Drift

CASA formalizes Invariant Drift as a system-level failure mode.

Invariant drift occurs when the effective invariant set changes over time without a versioned policy update.

CASA detects drift using:

Invariant Retention Ratio (IRR)

Boundary Consistency Score (BCS)

Gate Determinism Rate (GDR)

Evidence Completeness (EC)

Drift signals may escalate routing from AUTO → REVIEW or trigger HALT.

Control Boundary Model

Tier classification:

Tier 0 — Always allowed

Tier 1 — Constrained

Tier 2 — Requires review

Tier 3 — Always blocked

Tier 3 always results in HALT.

Boundaries are machine-enforceable.

What CASA Guarantees

CASA guarantees:

Explicit execution boundaries

Deterministic routing

Replayable decision records

Version-bound governance

Machine-detectable violations

CASA does not guarantee:

Outcome correctness

Perfect safety

Automatic legal compliance

It guarantees controlled autonomy — not correctness.
Minimal deployment structure
Agent
  ↓
CASA Gateway
  ↓
Signal Extraction
  ↓
Gate Engine
  ↓
Execution Router
  ↓
Audit Ledger
Repository Structure
casa/
  invariant/
  signal_layer/
  gate_engine.py
  policy_loader.py
  audit_ledger.py
  models.py
  tests/

Invariant drift logic resides under casa/invariant/.

Maturity Model

C0 — Experimental

C1 — Manual approval

C2 — Deterministic gating

C3 — Evidence-based scaling

C4 — Self-governing autonomy

Progression is ratcheted. Regression requires explicit override.

Status

Active development.
Control-plane architecture under iterative hardening.
