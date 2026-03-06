# Copilot Instructions for CASA Control Plane

## Project Overview

CASA (Control Awareness System Architecture) is a **deterministic governance control plane** for autonomous and semi-autonomous AI systems. It installs enforceable execution boundaries between AI reasoning and real-world action, ensuring every agent decision is authorized, auditable, and replayable.

## Repository Structure

```
casa-control-plane/
├── casa/                     # Core governance library
│   ├── gate_engine.py        # Deterministic gate: returns AUTO / REVIEW / HALT
│   ├── risk_engine.py        # Risk classification and scoring (0–100)
│   ├── policy_loader.py      # Loads and validates policy.json
│   ├── audit_ledger.py       # Append-only IDEL audit log
│   ├── ledger.py             # Low-level ledger helpers
│   ├── decision_replay.py    # Replay engine for recorded decisions
│   ├── policy_simulator.py   # Simulates policy outcomes without side effects
│   ├── policy_diff.py        # Compares policy versions
│   ├── router.py             # Execution router (AUTO → run, REVIEW → escalate, HALT → block)
│   ├── middleware.py         # ASGI middleware for CASA integration
│   ├── evaluator.py          # Agent action evaluation logic
│   └── telemetry/            # Drift monitoring, boundary stress, metrics
├── tests/                    # pytest test suite (one file per module)
├── governance_api.py         # FastAPI server — main API surface
├── streamlit_app.py          # Streamlit dashboard UI
├── policy.json               # Active governance policy definition
├── config.py                 # Environment variable configuration
├── demo_setup.py             # Generates stable demo data
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── render.yaml               # Render deployment blueprint
└── Procfile                  # Heroku deployment config
```

## Tech Stack

- **Python 3.11**
- **FastAPI 0.115** — REST API (`governance_api.py`)
- **Uvicorn** — ASGI server
- **Pydantic v2** — request/response validation
- **Streamlit 1.39** — dashboard (`streamlit_app.py`)
- **pytest** — testing framework
- **pandas** — data processing in telemetry/dashboard

## Build and Run

```bash
# Install dependencies
pip install -r requirements.txt

# Generate demo data
python demo_setup.py stable

# Start the governance API (terminal 1)
uvicorn governance_api:app --host 127.0.0.1 --port 5000

# Start the Streamlit dashboard (terminal 2)
streamlit run streamlit_app.py
# → http://localhost:8501  login: admin / casa-demo
```

## Running Tests

```bash
# Run the full test suite
pytest tests/

# Run a specific module
pytest tests/test_governance_api.py -v
```

Tests use `fastapi.testclient.TestClient` for API tests. There is no separate test database — tests run against in-memory state. Keep each test file focused on a single module.

## Core Architectural Concepts

### Gate Outcomes (closed set — do not add new states)
| State    | Meaning                          |
|----------|----------------------------------|
| `ALLOW`  | Low risk — execute automatically |
| `REVIEW` | Human approval required          |
| `HALT`   | Execution blocked                |

### Gate Engine Logic (`casa/gate_engine.py`)
```python
if policy_result == "FORBIDDEN" or risk == "CRITICAL":
    return "HALT"
if risk == "HIGH" or policy_result == "REVIEW":
    return "REVIEW"
return "ALLOW"
```

Hard violations always override scoring — never route around them.

### Audit Ledger (IDEL)
Every decision must record: `policy_version`, `signals_snapshot`, `risk_score`, `confidence`, `gate_outcome`, `execution_result`, and `previous_hash`. The ledger is append-only. Never delete or mutate ledger entries.

### Safety States
`NORMAL` → `DEGRADED` → `SAFE_MODE`. In `SAFE_MODE`, irreversible actions are prohibited.

## Coding Conventions

- **Python style:** Follow PEP 8. Use type hints on all function signatures.
- **Pydantic models:** Define request/response models with Pydantic v2 in the same file as the endpoint, or in a `models.py` if shared.
- **Determinism first:** Gate engine, risk engine, and routing logic must be purely deterministic — no randomness or external I/O.
- **Immutability:** Never modify ledger entries or replay records after they are written.
- **No new gate states:** The `AUTO / REVIEW / HALT` set is closed. Do not add states.
- **Policy changes require versioning:** Any change to `policy.json` must bump `policy_version`.
- **Tests required:** Every new module in `casa/` must have a corresponding test file in `tests/`.
- **Environment variables via `config.py`:** Read all configuration from `config.py`, not directly from `os.environ`.

## Security Guidelines

- **Never log secrets** (API keys, password hashes, tokens) in the audit ledger or application logs.
- **Authentication:** Dashboard authentication uses SHA-256 password hashes stored in environment variables — do not store plaintext passwords.
- **CORS:** `CORS_ORIGINS` defaults to `*` in development. In production deployments, set it to the specific dashboard origin.
- **Input validation:** All API inputs must be validated with Pydantic models before reaching business logic.

## Environment Variables

| Variable              | Service   | Description                              | Default               |
|-----------------------|-----------|------------------------------------------|-----------------------|
| `CASA_API_URL`        | Dashboard | URL of the deployed CASA API             | `http://127.0.0.1:5000` |
| `CORS_ORIGINS`        | API       | Comma-separated allowed origins          | `*`                   |
| `LOGIN_USERNAME`      | Dashboard | Dashboard login username                 | `admin`               |
| `LOGIN_PASSWORD_HASH` | Dashboard | SHA-256 hex digest of the password       | hash of `casa-demo`   |
| `STRIPE_PAYMENT_LINK` | Dashboard | Stripe payment link URL for Pro plan     | _(none)_              |
| `STRIPE_PUBLISHABLE_KEY` | Dashboard | Stripe publishable key                | _(none)_              |

## What to Avoid

- Do not introduce new execution states beyond `ALLOW`, `REVIEW`, and `HALT`.
- Do not bypass the gate engine — all agent actions must pass through it.
- Do not mutate or delete audit ledger entries.
- Do not add dependencies outside `requirements.txt` without updating that file.
- Do not add `print()` debug statements to production modules in `casa/` or `governance_api.py`.
- Do not store secrets in source code or commit them to the repository.
