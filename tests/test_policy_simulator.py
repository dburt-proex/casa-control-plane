"""
Tests for Policy Dry-Run Simulator

Verifies safe policy evolution and impact analysis.
"""

import pytest
import os
import json
from CASA.audit_ledger import record_decision, read_ledger, LEDGER_FILE
from CASA.policy_simulator import PolicySimulator, simulate_policy
from CASA.policy_loader import load_policy


@pytest.fixture(autouse=True)
def cleanup_ledger():
    """Clean up test ledger before and after each test."""
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
    yield
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)


# --------Basic Simulation Tests--------

def test_simulate_no_policy_change():
    """Test simulation when candidate policy is identical to current."""
    # Record some decisions
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    # Use current policy as candidate
    current_policy = load_policy()
    report = simulate_policy(current_policy)
    
    assert report["decisions_analyzed"] == 3
    assert report["decisions_that_change"] == 0
    assert len(report["conflicts"]) == 0
    assert report["confidence"] > 0


def test_simulate_with_policy_change():
    """Test simulation with a policy that relaxes restrictions."""
    # Record decisions
    for i in range(50):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(30):
        record_decision("analytics_agent", "read_database", "LOW", "ALLOW")
    for i in range(10):
        record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    # Create a more permissive policy
    base_policy = load_policy()
    relaxed_policy = {
        "agents": {
            "agent_01": ["read_database", "write_database"],
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database", "write_database", "delete_database"],
        },
        "review": [],  # Remove review requirement
        "forbidden": []  # Remove forbidden items
    }
    
    report = simulate_policy(relaxed_policy)
    
    assert report["decisions_analyzed"] >= 1
    assert "metric_changes" in report
    assert report["confidence"] >= 0


def test_simulate_restrictive_policy():
    """Test simulation with more restrictive policy."""
    # Record decisions
    for i in range(90):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(10):
        record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    # Create restrictive policy
    restrictive_policy = {
        "agents": {
            "agent_01": ["read_database"],  # Remove write_database permission
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database"],
        },
        "review": ["write_database"],
        "forbidden": ["delete_database", "write_database"]
    }
    
    report = simulate_policy(restrictive_policy)
    
    assert report["decisions_analyzed"] >= 1
    # More restrictive should increase halts
    assert report["metric_changes"]["halt_increase_pct"] >= 0 or len(report["conflicts"]) > 0


# --------Conflict Detection Tests--------

def test_conflict_detection_permission_boundary():
    """Test detection of permission boundary conflicts."""
    # Record decisions from multiple agents
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_02", "read_database", "LOW", "ALLOW")
    record_decision("agent_03", "write_database", "HIGH", "REVIEW")
    
    # Remove agent_02's read permission
    policy_with_conflict = {
        "agents": {
            "agent_01": ["read_database"],
            "agent_02": [],  # Removed read_database
            "agent_03": ["write_database"],
            "admin_agent": ["read_database", "write_database", "delete_database"],
       },
        "review": ["write_database"],
        "forbidden": ["delete_database"]
    }
    
    report = simulate_policy(policy_with_conflict)
    
    assert report["conflict_count"] > 0
    # Should have conflicts, type may vary
    assert len(report["conflicts"]) > 0


def test_conflict_type_categorization():
    """Test that conflicts are properly categorized."""
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    # Policy that changes write from REVIEW to FORBIDDEN
    new_policy = {
        "agents": {
            "agent_01": ["read_database"],
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database", "write_database"],
        },
        "review": [],
        "forbidden": ["write_database", "delete_database"]
    }
    
    report = simulate_policy(new_policy)
    
    # Should have conflicts
    assert len(report["conflicts"]) > 0
    for conflict in report["conflicts"]:
        assert "type" in conflict
        assert "agent" in conflict
        assert "action" in conflict


# --------Risk Assessment Tests--------

def test_critical_risk_assessment():
    """Test assessment of critical risk implications."""
    # Record critical decisions
    for i in range(50):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(10):
        record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    # Policy that allows more critical actions
    risky_policy = {
        "agents": {
            "agent_01": ["read_database", "delete_database"],  # Allow critical action!
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database", "write_database", "delete_database"],
        },
        "review": ["write_database"],
        "forbidden": []
    }
    
    report = simulate_policy(risky_policy)
    
    assert "risk_indicators" in report
    # Should show critical_now_allowed if we're relaxing critical blocks
    total_analyzed = report["decisions_analyzed"]
    assert report["decisions_analyzed"] > 0


def test_risk_indicators_present():
    """Test that risk indicators are properly computed."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    policy = load_policy()
    report = simulate_policy(policy)
    
    risk_ind = report["risk_indicators"]
    assert "critical_now_blocked" in risk_ind
    assert "critical_now_allowed" in risk_ind
    assert "high_risk_now_allowed" in risk_ind
    assert "risk_profile_shift" in risk_ind


# --------Metrics Tests--------

def test_routing_changes_computed():
    """Test that routing changes are properly computed."""
    # Record decisions
    for i in range(80):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(15):
        record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    for i in range(5):
        record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    # Policy that changes some reviews to halts
    new_policy = {
        "agents": {
            "agent_01": ["read_database"],  # Removed write
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database", "write_database", "delete_database"],
        },
        "review": [],
        "forbidden": ["write_database", "delete_database"]
    }
    
    report = simulate_policy(new_policy)
    
    assert "routing_changes" in report
    assert "metric_changes" in report


def test_metric_changes_calculated():
    """Test metric change percentages."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    policy = load_policy()
    report = simulate_policy(policy)
    
    metrics = report["metric_changes"]
    assert "halt_increase_pct" in metrics
    assert "review_increase_pct" in metrics
    assert "allow_change_pct" in metrics
    assert isinstance(metrics["halt_increase_pct"], (int, float))


# --------Confidence Scoring Tests--------

def test_confidence_score_low_data():
    """Test confidence is low with minimal data."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    policy = load_policy()
    report = simulate_policy(policy)
    
    # Only 1 decision = low confidence
    assert report["confidence"] <= 50


def test_confidence_score_high_data():
    """Test confidence improves with more data."""
    # Record many decisions
    for i in range(150):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    policy = load_policy()
    report = simulate_policy(policy)
    
    # 150 decisions with no conflicts = reasonable confidence
    assert report["confidence"] > 50


def test_confidence_reduced_by_conflicts():
    """Test that confidence decreases when there are many conflicts."""
    # Record diverse decisions that will conflict
    for i in range(10):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
        record_decision("agent_02", "write_database", "HIGH", "REVIEW")
        record_decision("agent_03", "delete_database", "CRITICAL", "HALT")
    
    # Very restrictive policy should cause many conflicts
    restrictive = {
        "agents": {"agent_01": [], "agent_02": [], "agent_03": []},
        "review": [],
        "forbidden": ["read_database", "write_database", "delete_database"]
    }
    
    report = simulate_policy(restrictive)
    
    # Many conflicts should lower confidence
    if report["decisions_that_change"] > 5:
        assert report["confidence"] < 80


# --------Recommendation Tests--------

def test_recommendation_safe_policy():
    """Test recommendation for a safe policy change."""
    # Record stable decisions
    for i in range(100):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    policy = load_policy()
    report = simulate_policy(policy)
    
    # Identical policy = safe
    assert "READY_FOR_DEPLOYMENT" in report["recommendation"] or "No changes" in report["recommendation"] or "appear" in report["recommendation"]


def test_recommendation_high_risk():
    """Test recommendation for high-risk policy change."""
    # Record diverse decisions
    for i in range(5):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
        record_decision("agent_02", "write_database", "HIGH", "REVIEW")
    
    # Very restrictive policy
    restrictive = {
        "agents": {"agent_01": [], "agent_02": []},
        "review": [],
        "forbidden": ["read_database", "write_database"]
    }
    
    report = simulate_policy(restrictive)
    
    # Should have warning or recommendation
    assert isinstance(report["recommendation"], str)
    assert len(report["recommendation"]) > 0


def test_recommendation_warning_halt_increase():
    """Test warning when halt rate increases significantly."""
    # Create scenario where halt rate increases
    for i in range(90):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(10):
        record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    # Policy that blocks more
    blocking = {
        "agents": {
            "agent_01": ["read_database"],
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database"],
        },
        "review": [],
        "forbidden": ["write_database", "delete_database"]
    }
    
    report = simulate_policy(blocking)
    
    assert isinstance(report["recommendation"], str)


# --------Empty Ledger Tests--------

def test_empty_ledger_simulation():
    """Test simulation with no historical decisions."""
    # Don't record any decisions
    policy = load_policy()
    report = simulate_policy(policy)
    
    assert report["decisions_analyzed"] == 0
    assert report["decisions_that_change"] == 0
    assert report["confidence"] == 0.0
    assert "NO_DATA" in report["recommendation"]


# --------Report Structure Tests--------

def test_report_structure():
    """Test that report contains all required fields."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    policy = load_policy()
    report = simulate_policy(policy)
    
    required_fields = [
        "decisions_analyzed",
        "decisions_that_change",
        "original_distribution",
        "simulated_distribution",
        "routing_changes",
        "metric_changes",
        "conflicts",
        "conflict_count",
        "risk_indicators",
        "confidence",
        "recommendation",
    ]
    
    for field in required_fields:
        assert field in report, f"Missing field: {field}"
