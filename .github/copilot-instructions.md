# CASA Copilot Instructions

These instructions apply to all Copilot interactions across this repository.

---

## Repository Identity

This repository contains **CASA** — a deterministic governance control plane for autonomous AI systems.

CASA enforces execution boundaries between AI reasoning and real-world actions using deterministic gating (AUTO / REVIEW / HALT), immutable audit ledgers, and policy-versioned signal evaluation.

---

## Core Operating Principles

1. **Proof before expansion.** Ship bounded, verifiable improvements. No speculative additions.
2. **Governed execution over speed.** Every meaningful change must preserve system integrity.
3. **Smallest viable deliverable.** Do exactly what is needed for the stated objective. No scope creep.
4. **Architecture must stay legible.** No unnecessary abstraction, no framework novelty.

---

## Mandatory Task Triage

Classify every request before acting:

**TIER A — Execute autonomously**
- Small bug fixes
- Documentation cleanup
- Tests for existing behavior
- Issue grooming
- Refactors that do not change behavior
- File organization, templates, summaries
- Commit preparation and PR descriptions

**TIER B — Execute with review checkpoint**
- Architecture changes
- Dependency changes
- Schema changes
- Auth and middleware logic
- Environment configuration
- CI/CD changes
- External integrations
- Anything customer-facing or affecting pricing

**TIER C — Never execute without explicit approval**
- Secret or credential handling
- Production data writes
- Infra provisioning
- Billing and payment logic
- Security policy changes
- Irreversible migrations
- Legal or compliance assertions presented as fact

---

## Change Contract

Before any non-trivial change, state:
- **Objective** — what this change achieves
- **Files touched** — exact paths
- **Expected impact** — behavior change
- **Risks** — failure modes
- **Rollback path** — exact reversal steps

If rollback is unclear, stop and request review.

---

## Quality Gates

Before finalizing any code or change:
- Check for syntax issues
- Check edge cases and boundary conditions
- Check imports and dependency consistency
- Check naming consistency with existing patterns
- Check for hidden scope expansion
- Check for unnecessary complexity
- Confirm success criteria were actually met

---

## Governance Boundaries

Pause and emit a REVIEW PACK instead of executing when work touches:
- Auth, secrets, or credentials
- Money, billing, or Stripe integration
- Infrastructure or deployment configuration
- External publication or customer-facing content
- Irreversible actions of any kind

---

## Anti-Dilution Rules

- Do not perform cosmetic optimization.
- Do not add complexity without leverage.
- Do not expand scope unless it materially improves the outcome.
- Do not hallucinate APIs, libraries, or repository structure.
- If a fact is unknown, state it explicitly and work with bounded assumptions.

---

## Path-Specific Instructions

| Scope | Instructions File |
|---|---|
| Backend (Python, API, core) | `instructions/backend.instructions.md` |
| Documentation | `instructions/docs.instructions.md` |
| Marketing content | `instructions/marketing.instructions.md` |

---

## Agent Profiles

| Agent | File |
|---|---|
| CASA Operator | `agents/casa-operator.agent.md` |

See `AGENTS.md` for full registry.
