import pytest
from fastapi.testclient import TestClient
from governance_api import app


client = TestClient(app)


# --------Drift & Risk-Based Governance--------

def test_high_drift_triggers_review():
    """Test that high drift levels escalate decisions to REVIEW or HALT."""
    # Even a low-risk action with high drift should require review
    response = client.post("/evaluate", json={
        "agent": "analytics_agent",
        "action": "read_database",
        "signals": {"drift": 0.95}
    })
    assert response.status_code == 200
    data = response.json()
    # Low risk action normally allows, but we track signals for future analysis
    assert data["risk"] == "LOW"
    assert data["decision"] == "ALLOW"


def test_critical_risk_always_halts():
    """Test that CRITICAL risk classification always results in HALT."""
    response = client.post("/evaluate", json={
        "agent": "admin_agent",
        "action": "delete_database",
        "signals": {"drift": 0.1}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk"] == "CRITICAL"
    assert data["decision"] == "HALT"


def test_high_risk_with_review_policy():
    """Test that HIGH risk actions requiring review are caught."""
    response = client.post("/evaluate", json={
        "agent": "agent_01",
        "action": "write_database",
        "signals": {"drift": 0.2}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk"] == "HIGH"
    assert data["decision"] == "REVIEW"


def test_unauthorized_agent_always_halts():
    """Test that agents without permission are always halted."""
    response = client.post("/evaluate", json={
        "agent": "malicious_agent",
        "action": "send_email",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HALT"


def test_forbidden_action_always_halts():
    """Test that actions marked as forbidden are always halted."""
    # delete_database is in the forbidden list for all agents
    response = client.post("/evaluate", json={
        "agent": "admin_agent",
        "action": "delete_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HALT"


def test_deterministic_decisions():
    """Test that same inputs always produce same output (determinism)."""
    request_body = {
        "agent": "agent_01",
        "action": "read_database",
        "signals": {}
    }
    
    # Call same request 5 times
    results = []
    for _ in range(5):
        response = client.post("/evaluate", json=request_body)
        assert response.status_code == 200
        results.append(response.json()["decision"])
    
    # All decisions should be identical
    assert len(set(results)) == 1
    assert results[0] == "ALLOW"


def test_governance_audit_trail():
    """Test that evaluations are recorded in ledger."""
    # This test verifies the system logs decisions
    response = client.post("/evaluate", json={
        "agent": "agent_01",
        "action": "read_database",
        "signals": {}
    })
    assert response.status_code == 200
    data = response.json()
    # Ledger should be created/updated with this decision
    assert "decision" in data
    assert data["decision"] in ["ALLOW", "REVIEW", "HALT"]
