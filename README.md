# CASA  
## Control Awareness System Architecture  
Deterministic Governance Control Plane for Autonomous Systems

---

## Overview

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
