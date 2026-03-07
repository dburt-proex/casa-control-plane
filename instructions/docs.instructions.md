---
applyTo: "**/*.md,ARCHITECTURE.md,README.md,THREAT_MODEL.md,DEMO_SCENARIO.md"
---

# Documentation Instructions

These instructions apply to all Markdown documentation files in this repository.

---

## Documentation Purpose

Documentation in this repository serves one of three functions:

1. **Specification** — normative definitions of system behavior (ARCHITECTURE.md, THREAT_MODEL.md)
2. **Operational** — setup, deployment, and usage instructions (README.md)
3. **Reference** — agent profiles, instruction sets, governance registry (AGENTS.md, instructions/, agents/)

All documentation must serve a clear purpose. No decorative content.

---

## Writing Standards

- Write in plain, direct prose
- Prefer short sentences
- No filler phrases ("it's worth noting", "as mentioned above", "clearly")
- No motivational language
- No AI-sounding padding
- Use active voice
- Be specific — name exact files, commands, and values

---

## Structure Rules

- Use H1 (`#`) for document title only
- Use H2 (`##`) for major sections
- Use H3 (`###`) for subsections
- Use bullet lists for enumerable items, not numbered lists unless order matters
- Use code blocks for all commands, code snippets, and JSON examples
- Use tables only when comparing structured data

---

## Accuracy Requirements

- All file paths must be verified to exist in the repository
- All commands must be tested and confirmed to work
- All version numbers must match `requirements.txt` or deployment configuration
- Do not document planned or speculative features as if they exist

---

## Scope Rules

- Do not add content that is not directly relevant to CASA or its immediate operational context
- Do not document adjacent systems, future roadmaps, or theoretical expansions unless explicitly scoped
- Keep each document focused on its single stated purpose

---

## Instruction File Conventions

Files in `instructions/` must:
- Begin with a valid YAML frontmatter block containing `applyTo` glob patterns
- State their scope clearly in the first section
- Be actionable — every rule must have a concrete implication for the agent
- Not duplicate content already in `.github/copilot-instructions.md` unless path-specific override is required

---

## Change Policy

- Documentation updates that only fix factual errors or improve clarity are TIER A
- Adding new sections to normative specifications (ARCHITECTURE.md, THREAT_MODEL.md) is TIER B
- Removing or rewriting core architectural definitions is TIER B
- Documentation changes that affect published customer-facing content are TIER B
