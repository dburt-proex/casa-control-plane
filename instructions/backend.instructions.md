---
applyTo: "**/*.py,governance_api.py,main.py,config.py,requirements.txt"
---

# Backend Instructions

These instructions apply to all Python source files, API modules, and backend configuration in this repository.

---

## Language and Framework

- Python 3.11+
- FastAPI for all API endpoints
- SQLAlchemy with SQLite (StaticPool for tests, file-backed for production)
- PyJWT for authentication tokens
- passlib/bcrypt for password hashing
- Pydantic for request/response schemas

---

## Code Style

- Follow PEP 8 strictly
- Use type annotations on all function signatures
- Prefer explicit over implicit
- Keep functions small and single-purpose
- No unused imports
- No commented-out code committed to main

---

## API Design Rules

- All endpoints must be explicitly typed (request body and response model)
- Authentication must use the existing JWT middleware — do not bypass or duplicate it
- All mutations (POST, PUT, DELETE) must produce an audit ledger entry
- Route handlers must not contain business logic; delegate to service or domain modules

---

## CASA Governance Integration

All execution paths that affect policy, gates, risk scoring, or audit records must route through the CASA control plane:

```python
result = casa.evaluate(action)

if result.gate == "AUTO":
    execute(action)
elif result.gate == "REVIEW":
    queue_for_approval(action)
else:
    block(action)
```

Direct tool calls or state mutations that bypass `casa.evaluate()` are not permitted.

---

## Audit Ledger

- Every governance decision must produce a ledger record
- Ledger entries must be append-only
- Required fields: `decision_id`, `timestamp`, `policy_version`, `action_signature`, `signals_snapshot`, `risk_score`, `confidence`, `gate_outcome`, `execution_result`, `previous_hash`
- Do not modify or delete existing ledger entries

---

## Policy and Invariants

- Policy changes must increment `policy_version`
- Invariant drift is a critical failure — do not suppress drift signals
- Tier 3 actions always route to HALT — no exceptions
- Gate state set is closed: AUTO, REVIEW, HALT only

---

## Testing

- All new backend functionality requires unit tests in `tests/`
- Use `StaticPool` (in-memory SQLite) for test database isolation
- Tests must not write to production ledger files
- Tests must be deterministic and side-effect free
- Target: every gate routing path has at least one explicit test case

---

## Dependencies

- Do not add new dependencies without explicit justification and review
- Update `requirements.txt` with pinned versions when adding dependencies
- Check for known vulnerabilities before adding any new package

---

## Security

- Never log raw credentials, secrets, or JWT tokens
- Validate all inputs at the API boundary using Pydantic
- Rate limiting and auth checks must remain in place on all protected routes
- Do not introduce new unauthenticated endpoints without explicit review (TIER B)
