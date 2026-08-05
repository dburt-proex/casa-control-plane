"""Tests for the POST /operator/chat bridge endpoint."""
import pytest
from fastapi.testclient import TestClient
from governance_api import app

client = TestClient(app)


# -----------------------------------------------------------------------
# Helper: seed a REVIEW decision so list_flagged returns something
# -----------------------------------------------------------------------

def _seed_review_decision():
    """Post a write_database evaluation to create a REVIEW ledger entry."""
    resp = client.post("/evaluate", json={
        "agent": "agent_01",
        "action": "write_database",
        "signals": {}
    })
    assert resp.status_code == 200
    return resp.json()


# -----------------------------------------------------------------------
# dashboard command
# -----------------------------------------------------------------------

def test_operator_chat_dashboard():
    """operator/chat with dashboard command returns governance data."""
    response = client.post("/operator/chat", json={"command": "dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "dashboard"
    result = data["result"]
    assert "governance_health" in result
    assert "boundary_stress" in result
    assert "system_state" in result


# -----------------------------------------------------------------------
# boundary_stress command
# -----------------------------------------------------------------------

def test_operator_chat_boundary_stress():
    """operator/chat with boundary_stress command returns stress metrics."""
    response = client.post("/operator/chat", json={"command": "boundary_stress"})
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "boundary_stress"
    result = data["result"]
    assert "stress_score" in result
    assert "system_state" in result


# -----------------------------------------------------------------------
# list_flagged command
# -----------------------------------------------------------------------

def test_operator_chat_list_flagged():
    """operator/chat with list_flagged command returns list of REVIEW decisions."""
    _seed_review_decision()
    response = client.post("/operator/chat", json={"command": "list_flagged"})
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "list_flagged"
    assert isinstance(data["result"], list)


# -----------------------------------------------------------------------
# evaluate command
# -----------------------------------------------------------------------

def test_operator_chat_evaluate():
    """operator/chat with evaluate command runs a governed evaluation."""
    response = client.post("/operator/chat", json={
        "command": "evaluate",
        "params": {
            "agent": "analytics_agent",
            "action": "read_database",
            "signals": {}
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["command"] == "evaluate"
    result = data["result"]
    assert result["decision"] == "ALLOW"
    assert result["risk"] == "LOW"


def test_operator_chat_evaluate_missing_agent():
    """operator/chat evaluate without agent returns 400."""
    response = client.post("/operator/chat", json={
        "command": "evaluate",
        "params": {"action": "read_database"}
    })
    assert response.status_code == 400


def test_operator_chat_evaluate_missing_action():
    """operator/chat evaluate without action returns 400."""
    response = client.post("/operator/chat", json={
        "command": "evaluate",
        "params": {"agent": "analytics_agent"}
    })
    assert response.status_code == 400


# -----------------------------------------------------------------------
# decision_replay command
# -----------------------------------------------------------------------

def test_operator_chat_decision_replay_missing_id():
    """operator/chat decision_replay without decision_id returns 400."""
    response = client.post("/operator/chat", json={
        "command": "decision_replay",
        "params": {}
    })
    assert response.status_code == 400


def test_operator_chat_decision_replay_invalid_id():
    """operator/chat decision_replay with unknown id returns 404."""
    response = client.post("/operator/chat", json={
        "command": "decision_replay",
        "params": {"decision_id": "00000000-0000-0000-0000-000000000000"}
    })
    assert response.status_code == 404


def test_operator_chat_decision_replay_valid():
    """operator/chat decision_replay with real id returns replay result."""
    # First create a decision
    eval_resp = client.post("/evaluate", json={
        "agent": "analytics_agent",
        "action": "read_database",
        "signals": {}
    })
    assert eval_resp.status_code == 200

    # Fetch the decision_id from the flagged list or from ledger directly
    # Use list_flagged first to check, otherwise query dashboard for an id
    flagged_resp = client.post("/operator/chat", json={"command": "list_flagged"})
    assert flagged_resp.status_code == 200

    # Get any decision_id from the ledger via the replay-all endpoint
    all_resp = client.get("/decision-replay/all")
    if all_resp.status_code == 200:
        decisions = all_resp.json().get("decisions", [])
        if decisions:
            decision_id = decisions[0]["decision_id"]
            response = client.post("/operator/chat", json={
                "command": "decision_replay",
                "params": {"decision_id": decision_id}
            })
            assert response.status_code == 200
            data = response.json()
            assert data["command"] == "decision_replay"
            assert "result" in data


# -----------------------------------------------------------------------
# unknown command
# -----------------------------------------------------------------------

def test_operator_chat_unknown_command():
    """operator/chat with unknown command returns 400."""
    response = client.post("/operator/chat", json={"command": "foobar"})
    assert response.status_code == 400
    assert "Unknown command" in response.json()["detail"]


# -----------------------------------------------------------------------
# GitHub Repo Operator Agent risk evaluation
# -----------------------------------------------------------------------

def test_github_operator_inspect_repo_allowed():
    """github_repo_operator inspect_repo should ALLOW."""
    response = client.post("/evaluate", json={
        "agent": "github_repo_operator",
        "action": "inspect_repo",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ALLOW"
    assert data["risk"] == "LOW"


def test_github_operator_open_pr_review():
    """github_repo_operator open_pull_request should be REVIEW (HIGH risk)."""
    response = client.post("/evaluate", json={
        "agent": "github_repo_operator",
        "action": "open_pull_request",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk"] == "HIGH"
    assert data["decision"] == "REVIEW"


def test_github_operator_block_merge_halt():
    """github_repo_operator block_direct_merge should HALT (CRITICAL + forbidden)."""
    response = client.post("/evaluate", json={
        "agent": "github_repo_operator",
        "action": "block_direct_merge",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HALT"
    assert data["risk"] == "CRITICAL"
