"""
GitHub Repo Operator Agent

Demonstrates a real governed workflow: every repository mutation is evaluated
by the CASA governance engine before execution.  Actions with HIGH risk are
routed through the REVIEW gate so a human can approve or halt them.

Governed actions:
  - inspect_repo        LOW risk  → ALLOW
  - propose_file_change MEDIUM risk → ALLOW (may be REVIEW depending on policy)
  - create_branch       LOW risk  → ALLOW
  - open_pull_request   HIGH risk → REVIEW
  - apply_label         LOW risk  → ALLOW
  - block_direct_merge  CRITICAL risk → HALT

Usage:
    python example_agent.py
"""

import os
import sys

from CASA.middleware import casa_guard


AGENT_ID = "github_repo_operator"


# ---------------------------------------------------------------------------
# Simulated GitHub tool functions
# ---------------------------------------------------------------------------

def inspect_repo():
    """Read repository metadata and recent commits."""
    print("[github] Inspecting repository: dburt-proex/casa-control-plane")
    print("[github] Branch: master | Open PRs: 3 | Last commit: 2m ago")


def propose_file_change():
    """Suggest a diff to an existing file."""
    print("[github] Proposing change: update README.md → add deployment badge")


def create_branch():
    """Create a feature branch from HEAD."""
    print("[github] Creating branch: feature/update-readme")


def open_pull_request():
    """Open a PR against the base branch (requires human review gate)."""
    print("[github] Opening pull request: 'Update README deployment badge'")


def apply_label():
    """Apply a label to an open issue or PR."""
    print("[github] Applying label 'ready-for-review' to PR #42")


def block_direct_merge():
    """Block a direct push to a protected branch (CRITICAL / HALT)."""
    print("[github] HALT: Direct merge to protected branch blocked.")


# ---------------------------------------------------------------------------
# Agent run loop
# ---------------------------------------------------------------------------

def run():
    """Run all agent actions through the CASA governance gate."""
    actions = [
        ("inspect_repo",        inspect_repo),
        ("propose_file_change", propose_file_change),
        ("create_branch",       create_branch),
        ("open_pull_request",   open_pull_request),
        ("apply_label",         apply_label),
        ("block_direct_merge",  block_direct_merge),
    ]

    print("=" * 60)
    print("CASA GitHub Repo Operator Agent".center(60))
    print("=" * 60)

    for action_name, tool_fn in actions:
        print(f"\n[agent] Requesting: {action_name}")
        casa_guard(AGENT_ID, action_name, tool_fn)


if __name__ == "__main__":
    run()
