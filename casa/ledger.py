import datetime
import json
import uuid

from CASA import postgres_ledger


def log_event(agent, action, risk, decision, signals=None, policy_version=None):
    """Log governance decision with optional signals and policy tracking.

    Writes to Postgres when DATABASE_URL is set; always writes to ledger.log
    as a durable fallback so the file-backed read path continues to work in
    environments without a database.

    Args:
        agent: Agent performing action
        action: Action being taken
        risk: Risk classification
        decision: Gate outcome (ALLOW/REVIEW/HALT)
        signals: Optional signal context for decision replay
        policy_version: Optional policy version used for decision
    """
    decision_id = str(uuid.uuid4())
    entry = {
        "decision_id": decision_id,
        "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "risk": risk,
        "decision": decision,
        "signals": signals or {},
        "policy_version": policy_version or "unknown"
    }

    # Attempt durable Postgres write first
    postgres_ledger.write_decision(
        decision_id=decision_id,
        agent=agent,
        action=action,
        risk=risk,
        decision=decision,
        signals=signals or {},
        policy_version=policy_version or "unknown",
    )

    # Always append to file ledger (survives restart when disk is persistent;
    # serves as local cache / fallback when DB is unavailable)
    with open("ledger.log", "a") as f:
        f.write(json.dumps(entry) + "\n")


# backwards compatibility alias
record_decision = log_event