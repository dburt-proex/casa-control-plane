import datetime
import json


def log_event(agent, action, risk, decision):

    entry = {
        "time": datetime.datetime.utcnow().isoformat(),
        "agent": agent,
        "action": action,
        "risk": risk,
        "decision": decision
    }

    with open("ledger.log", "a") as f:
        f.write(json.dumps(entry) + "\n")


# backwards compatibility alias
record_decision = log_event