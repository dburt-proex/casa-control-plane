# AGENTS.md — Agent Registry and Governance Index

This file is the canonical registry for all Copilot agent profiles and instruction sets in the CASA control plane repository.

---

## Agent Profiles

| Agent | File | Scope |
|---|---|---|
| CASA Operator | `agents/casa-operator.agent.md` | Repo-wide governed execution agent |

---

## Instruction Files

| Scope | File | Applied To |
|---|---|---|
| Repo-wide | `.github/copilot-instructions.md` | All files |
| Backend | `instructions/backend.instructions.md` | Python source, API modules, config |
| Documentation | `instructions/docs.instructions.md` | Markdown files |
| Marketing | `instructions/marketing.instructions.md` | Marketing and pricing copy |

---

## Governance Structure

### Repo-Wide Rules

`.github/copilot-instructions.md` applies to all Copilot interactions in this repository. It defines:
- Task triage tiers (A / B / C)
- Change contract requirements
- Quality gates
- Governance boundaries
- Anti-dilution rules

### Path-Specific Rules

Files in `instructions/` extend the repo-wide rules for specific domains. Path-specific rules take precedence over repo-wide rules for files matching their `applyTo` glob patterns.

### Agent Profiles

Files in `agents/` define named operator profiles with a specific mission, access boundaries, and triage gate configuration. Agents are scoped to explicit access boundaries and must not act outside them.

---

## Triage Gate Summary

| Tier | Classification | Approval Requirement |
|---|---|---|
| A | Safe to execute autonomously | None |
| B | Requires review checkpoint | Human review before execution |
| C | Never execute without approval | Explicit written approval required |

Anything touching auth, secrets, money, infrastructure, irreversible state, or external publication is TIER B or TIER C.

---

## Review Gate Triggers

Pause and emit a REVIEW PACK before executing when work touches:
- Auth, secrets, or credentials
- Money, billing, or Stripe integration
- Infrastructure or deployment configuration
- External publication or customer-facing content
- Irreversible actions of any kind

---

## CASA Governance Constraints

All agents operating in this repository must observe:

1. All execution paths affecting policy, gating, risk scoring, or audit records route through `casa.evaluate()`
2. Gate state set is closed: `AUTO`, `REVIEW`, `HALT` only
3. Tier 3 actions always produce `HALT`
4. Policy changes must increment `policy_version`
5. Invariant drift is a critical failure — never suppress drift signals
6. Ledger entries are append-only and must not be modified or deleted

---

## Adding New Agents or Instructions

To add a new agent profile:
1. Create the file in `agents/<name>.agent.md`
2. Include valid YAML frontmatter with `name` and `description`
3. Define mission, triage gates, access boundaries, and reporting format
4. Register the agent in this file

To add new instruction files:
1. Create the file in `instructions/<scope>.instructions.md`
2. Include valid YAML frontmatter with `applyTo` glob pattern
3. Define scope, rules, and change policy
4. Register the file in this file

Instruction files that duplicate repo-wide rules without adding path-specific value should not be created.
