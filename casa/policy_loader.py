import json
import hashlib


POLICY_FILE = "policy.json"


def load_policy():
    with open(POLICY_FILE, "r") as f:
        policy = json.load(f)

    return policy


def policy_hash():
    with open(POLICY_FILE, "rb") as f:
        contents = f.read()
    return hashlib.sha256(contents).hexdigest()