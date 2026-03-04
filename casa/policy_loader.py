import json
from config import POLICY_FILE


def load_policy():
    with open(POLICY_FILE, "r") as f:
        return json.load(f)


def check_policy(agent, action, policy=None):

    if policy is None:
        policy = load_policy()

    agent_permissions = policy.get("agents", {}).get(agent, [])

    if action not in agent_permissions:
        return "FORBIDDEN"

    if action in policy.get("forbidden", []):
        return "FORBIDDEN"

    if action in policy.get("review", []):
        return "REVIEW"

    return "ALLOW"