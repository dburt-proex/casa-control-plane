import json
import os
from config import POLICY_FILE


# Module-level cache so repeated calls to load_policy() within the same
# process avoid redundant disk reads.  The cache is invalidated whenever the
# policy file's modification time changes so hot-reloads still work.
_policy_cache: dict | None = None
_policy_mtime: float | None = None


def load_policy() -> dict:
    global _policy_cache, _policy_mtime
    try:
        current_mtime = os.path.getmtime(POLICY_FILE)
    except FileNotFoundError:
        return {}

    if _policy_cache is None or current_mtime != _policy_mtime:
        with open(POLICY_FILE, "r") as f:
            _policy_cache = json.load(f)
        _policy_mtime = current_mtime

    return _policy_cache


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