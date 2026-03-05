import datetime
import json
import uuid


def log_event(agent, action, risk, decision, signals=None, policy_version=None):
    """Log governance decision with optional signals and policy tracking.
    
    Args:
        agent: Agent performing action
        action: Action being taken
        risk: Risk classification
        decision: Gate outcome (ALLOW/REVIEW/HALT)
        signals: Optional signal context for decision replay
        policy_version: Optional policy version used for decision
    """
    entry = {
        "decision_id": str(uuid.uuid4()),
        "time": datetime.datetime.utcnow().isoformat(),
        "agent": agent,
        "action": action,
        "risk": risk,
        "decision": decision,
        "signals": signals or {},
        "policy_version": policy_version or "unknown"
    }

    with open("ledger.log", "a") as f:
        f.write(json.dumps(entry) + "\n")


# backwards compatibility alias
record_decision = log_event