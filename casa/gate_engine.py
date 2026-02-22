from casa.policy_loader import load_policy, policy_hash
from casa.audit_ledger import record_decision
from dataclasses import dataclass
from casa.models import Signals
from casa.drift_monitor import DriftMonitor

drift_monitor = DriftMonitor()

@dataclass
class GateResult:
    outcome: str
    score: float
    confidence: float


def evaluate_gate(intent: dict, signals: Signals) -> GateResult:
    policy = load_policy()

    score = (
        signals.financial
        + signals.legal
        + signals.brand
        + signals.operational
        + signals.cognitive
    ) * 20

    confidence = max(0.0, 1 - (score / 100))

    if intent.get("tier") in policy["hard_halt_tiers"]:
        outcome = "HALT"
    elif score >= policy["review_threshold"]:
        outcome = "REVIEW"
    else:
        outcome = "ALLOW"

    result = GateResult(outcome, score, confidence)

    # Record to ledger with policy hash
    record_decision(
        intent,
        signals.__dict__,
        {
            "outcome": result.outcome,
            "score": result.score,
            "confidence": result.confidence,
            "policy_version": policy["version"],
            "policy_hash": policy_hash()
        }
    )

    return result