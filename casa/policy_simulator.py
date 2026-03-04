import json
from CASA.risk_engine import classify_risk
from CASA.gate_engine import gate_decision
from CASA.policy_loader import check_policy


def load_ledger(path="ledger.log"):
    """Load historical governance decisions."""
    decisions = []

    with open(path, "r") as f:
        for line in f:
            try:
                decisions.append(json.loads(line))
            except Exception:
                continue

    return decisions


def simulate_policy(decisions, candidate_policy):
    """
    Re-run historical decisions against a new policy.
    """

    results = []

    for decision in decisions:

        # risk classification is currently based on action only
        risk = classify_risk(decision.get("action"))

        # policy evaluation against the candidate_policy
        policy_result = check_policy(
            decision.get("agent"),
            decision.get("action"),
            policy=candidate_policy,
        )

        new_gate = gate_decision(policy_result, risk)

        results.append({
            "original": decision.get("decision"),
            "simulated": new_gate
        })

    return results