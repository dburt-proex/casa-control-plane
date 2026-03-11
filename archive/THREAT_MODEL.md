# CASA Threat Model Specification

Control Awareness System Architecture
Detinistic Governance Control Plane for Autonomous Systems

Version: 0.1.0
Status: Draft – Normative Threat Model

---

# 1. Purpose

This document defines the formal threat model for CASA.

The objective is to enumerate system-level failure modes that threaten deterministic governance and bounded autonomy.

The threat model focuses on execution control failure — not model misalignment, not ethics, and not policy philosophy.

CASA assumes:

* Agents can reason unpredictably
* Tools can return adversarial or malformed outputs
* Context may mutate across steps
* Optimization pressure exists

The control plane must remain deterministic under these conditions.

---

# 2. Trust Boundaries

## 2.1 Trusted

* Policy definitions (versioned)
* Gate engine logic
* Risk computation logic
* Audit ledger append mechanism

## 2.2 Semi-Trusted

* Tool responses
* Execution results

## 2.3 Untrusted

* Agent reasoning
* Prompt outputs
* External API data
* User-provided content

CASA treats all reasoning output as untrusted until gated.

---

# 3. Primary Threat Classes

## T1 — Execution Without Gate

**Description:**
Agent executes tool or state mutation without passing through CASA gate.

**Impact:**
Total governance bypass.

**Mitigation Layer:**

* Enforced execution router
* No direct tool bindings
* Gateway-only execution pattern

**Failure Severity:** Critical

---

## T2 — Invariant Drift

**Description:**
Policy-defined invariants degrade across steps without version change.

**Impact:**
Silent boundary erosion.

**Indicators:**

* IRR decrease
* Boundary reclassification
* Evidence loss

**Mitigation Layer:**

* Signal Layer drift metrics
* Drift escalation rules
* SAFE_MODE activation

**Failure Severity:** High

---

## T3 — Boundary Reclassification

**Description:**
Tier mapping changes for identical action signature.

**Impact:**
Tier 2 treated as Tier 1, or Tier 3 downgraded.

**Mitigation Layer:**

* Deterministic tier resolution
* Boundary consistency metric

**Failure Severity:** Critical if Tier 3 impacted

---

## T4 — Evidence Suppression

**Description:**
Required proof artifacts omitted but action allowed.

**Impact:**
Audit trail invalidation.

**Mitigation Layer:**

* Evidence completeness metric
* Hard HALT for Tier 2+ without proof

**Failure Severity:** Critical

---

## T5 — Non-Deterministic Routing

**Description:**
Identical inputs produce different gate outcomes.

**Impact:**
Loss of replayability and predictability.

**Mitigation Layer:**

* Closed state set
* Deterministic logic
* Gate determinism rate metric

**Failure Severity:** Critical

---

## T6 — Ledger Corruption

**Description:**
Audit entries altered or removed.

**Impact:**
Loss of forensic reconstruction.

**Mitigation Layer:**

* Append-only writes
* Hash linkage
* Periodic integrity validation

**Failure Severity:** Critical

---

## T7 — Context Saturation Decay

**Description:**
Earlier constraints fall out of context window.

**Impact:**
Implicit drift.

**Mitigation Layer:**

* Policy binding per decision
* Explicit invariant binding in signal extraction

**Failure Severity:** Medium

---

# 4. Adversarial Scenarios

## Scenario A — Tool Injection

Tool returns instruction-like output attempting to override policy.

Mitigation:

* Treat tool output as data only
* Re-run through signal layer
* Apply invariant checks

---

## Scenario B — Multi-Agent Disagreement

Agents resolve tiers differently.

Mitigation:

* Centralized tier resolution
* Policy-bound classification

---

## Scenario C — Optimization Pressure

Agent attempts to skip review to increase speed.

Mitigation:

* Gate closed state set
* Hard review thresholds

---

# 5. System Integrity Guarantees

CASA guarantees:

1. No execution without gate authorization
2. Tier 3 always HALT
3. Tier 2 requires approval artifact
4. All decisions produce ledger record
5. Same inputs → same outcome

If any guarantee fails, governance integrity is compromised.

---

# 6. Residual Risk

CASA does not eliminate:

* Incorrect reasoning
* Malicious human override
* Legal non-compliance outside defined policy
* Strategic misconfiguration of policy

CASA enforces boundaries; it does not define them.

---

# 7. Incident Classification

| Class | Description                  | Action             |
| ----- | ---------------------------- | ------------------ |
| C1    | Minor signal anomaly         | Log                |
| C2    | Drift threshold crossed      | Escalate to REVIEW |
| C3    | Hard invariant violation     | HALT               |
| C4    | Systemic determinism failure | SAFE_MODE          |

---

# 8. Governance Escalation Model

Repeated C3 or C4 incidents trigger:

* SAFE_MODE
* Mandatory human audit
* Policy review requirement

---

# 9. Conclusion

The CASA threat model centers on deterministic execution control.

Threat mitigation is structural, not advisory.

Governance fails when execution authority becomes ambiguous.

CASA exists to prevent ambiguity.
