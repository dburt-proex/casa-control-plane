---
applyTo: "**/marketing/**,**/pricing/**,**/landing/**,**/copy/**"
---

# Marketing Instructions

These instructions apply to all marketing content, pricing copy, and customer-facing materials in this repository.

---

## Scope

Marketing content in this repository includes:
- Pricing plan descriptions
- Product positioning statements
- Landing page copy
- Demo scenario scripts
- Feature descriptions intended for external audiences

---

## Accuracy Rules

- Every claim about CASA capabilities must be verifiable against the actual implementation
- Do not assert guarantees that exceed what the system architecturally provides
- CASA guarantees **control over execution**, not correctness of agent reasoning or ethical completeness
- Do not present planned features as shipped
- Do not use superlatives ("best", "only", "first") without verified evidence

---

## Tone and Style

- Direct and specific — state what the product does, not what it aspires to do
- No buzzword stacking ("AI-powered enterprise-grade next-gen")
- No vague benefit claims without a concrete mechanism
- Prefer short sentences and active voice
- Write for a technical buyer who will verify claims

---

## Positioning Constraints

CASA may be positioned accurately as:
- A deterministic governance control plane for autonomous AI systems
- A system that enforces execution boundaries between AI reasoning and real-world actions
- Infrastructure for bounded autonomy with measurable risk and replayable audit trails

Do not position CASA as:
- A model alignment solution
- A legal compliance guarantee
- An ethical AI certification

---

## Pricing Content

- Pricing changes are TIER B — require review before publication
- Stripe integration details must not be embedded in public marketing copy
- Plan limits and feature gates must match the current `config.py` and deployment configuration

---

## Change Policy

- Fixing factual errors in marketing copy is TIER A
- Revising positioning statements or value propositions is TIER B
- Any copy intended for external publication (landing page, paid ads, press) is TIER B
- Legal or compliance assertions presented as fact are TIER C — never execute without explicit approval
