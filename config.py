
POLICY_FILE = "policy.json"

RISK_MATRIX = {
    # Legacy database actions
    "read_database": "LOW",
    "send_email": "LOW",
    "write_database": "HIGH",
    "delete_database": "CRITICAL",
    # GitHub Repo Operator Agent actions
    "inspect_repo": "LOW",
    "propose_file_change": "MEDIUM",
    "create_branch": "LOW",
    "open_pull_request": "HIGH",
    "apply_label": "LOW",
    "block_direct_merge": "CRITICAL",
}
