# AGENTS.md — Agent Registry and Governance Index

This file is the canonical registry for all Codex, Copilot, and supervised agent profiles and instruction sets in the CASA control plane repository.

---

## Codex Operating Contract

### Project Context

This repository is part of the CASA / PromptBP build system.

CASA is a governed control-plane architecture for AI-assisted execution. The project prioritizes deterministic behavior, auditable decisions, bounded implementation, and demo-ready proof over speculative feature expansion.

PromptBP is the instruction-control framework used to structure build prompts, reduce drift, and improve execution reliability.

### Codex Authority

Codex may:
- Inspect repository structure.
- Read relevant files.
- Propose implementation plans.
- Edit files only when explicitly scoped.
- Run tests, linters, and build commands.
- Create branches and pull request summaries.
- Produce documentation for completed work.

Codex may not:
- Merge pull requests.
- Deploy to production.
- Delete files without explicit instruction.
- Modify secrets, tokens, credentials, or environment variables.
- Change production configuration unless explicitly scoped.
- Remove routes, tests, or middleware without verifying dependencies.
- Rewrite architecture without review.
- Invent test results.
- Claim success without validation evidence.

### Required Workflow

For every task:

1. Restate the objective.
2. Identify the scoped files or directories.
3. Inspect before editing.
4. Make the smallest viable change.
5. Run relevant validation.
6. Report changed files.
7. Report tests and results.
8. Identify risks.
9. Provide rollback instructions.
10. Recommend the next bounded block.

### Gate Policy

Use CASA-style gate classification for all work.

ALLOW:
- Documentation updates.
- Read-only audits.
- Small low-risk fixes.
- Formatting changes.
- Non-functional cleanup.

REVIEW:
- API route changes.
- Database or persistence changes.
- Auth, permissions, or session logic.
- Frontend/backend contract changes.
- Test rewrites.
- Dependency changes.
- Deployment config changes.

HALT:
- Secrets or credentials.
- Production deploys.
- Destructive file deletion.
- Irreversible migrations.
- Security-sensitive changes without explicit authorization.
- Any change Codex cannot validate.

### Block-Boundary Execution

Never perform broad “fix everything” work.

Every implementation must define:

- Block name
- Scope
- Included files
- Excluded files
- Acceptance criteria
- Tests to run
- Rollback path
- Gate classification

### PR Output Standard

Every PR or proposed change must include:

- Summary
- Scope
- Explicit non-scope
- Files changed
- Tests run
- Test results
- CASA gate classification
- Risk notes
- Rollback plan
- Recommended next block

### Repository Priorities

Prioritize in this order:

1. Stable demo path.
2. Backend/frontend contract alignment.
3. Ledger and audit reliability.
4. Test coverage.
5. Clear documentation.
6. Monetizable proof artifact.

Avoid adding infrastructure before validating demo usefulness, buyer clarity, or revenue path.

### Default Constraint

When uncertain, stop and classify the issue as REVIEW instead of guessing.

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
2. Gate state set is closed: `ALLOW`, `REVIEW`, `HALT` only
3. High-risk actions always produce `HALT`
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
