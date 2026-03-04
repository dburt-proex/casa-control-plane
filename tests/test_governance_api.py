import pytest
from fastapi.testclient import TestClient
from governance_api import app


client = TestClient(app)


# --------Health Check--------

def test_health_check():
    """Test that health endpoint returns running status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "CASA Governance API running"


# --------Governance Evaluation--------

def test_evaluate_allowed_action():
    """Test that authorized agent can perform allowed action."""
    response = client.post("/evaluate", json={
        "agent": "analytics_agent",
        "action": "read_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ALLOW"
    assert data["risk"] == "LOW"


def test_evaluate_requires_review():
    """Test that write_database requires review."""
    response = client.post("/evaluate", json={
        "agent": "agent_01",
        "action": "write_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "REVIEW"
    assert data["risk"] == "HIGH"


def test_evaluate_forbidden_action():
    """Test that forbidden action is halted."""
    response = client.post("/evaluate", json={
        "agent": "agent_01",
        "action": "delete_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HALT"


def test_evaluate_critical_risk_halts():
    """Test that CRITICAL risk always halts."""
    response = client.post("/evaluate", json={
        "agent": "admin_agent",
        "action": "delete_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HALT"
    assert data["risk"] == "CRITICAL"


def test_evaluate_unauthorized_agent():
    """Test that unauthorized agent gets HALT."""
    response = client.post("/evaluate", json={
        "agent": "unauthorized_agent",
        "action": "write_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HALT"


def test_evaluate_returns_correct_fields():
    """Test that evaluation response has all required fields."""
    response = client.post("/evaluate", json={
        "agent": "agent_01",
        "action": "read_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert "agent" in data
    assert "action" in data
    assert "risk" in data
    assert "decision" in data


# --------Policy Dry-Run--------

def test_dryrun_missing_file():
    """Test policy dryrun with non-existent file."""
    response = client.post("/policy/dryrun", json={
        "policy_candidate_path": "nonexistent.json"
    })
    # Should return 404 since file doesn't exist
    assert response.status_code == 404


# --------Risk Classification--------

def test_risk_levels():
    """Test that actions are classified with correct risk levels."""
    test_cases = [
        ("read_database", "LOW"),
        ("send_email", "LOW"),
        ("write_database", "HIGH"),
        ("delete_database", "CRITICAL"),
    ]
    
    for action, expected_risk in test_cases:
        response = client.post("/evaluate", json={
            "agent": "admin_agent",
            "action": action,
            "signals": {}
        })
        assert response.status_code == 200
        assert response.json()["risk"] == expected_risk
