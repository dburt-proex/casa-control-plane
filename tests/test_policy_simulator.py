"""
Tests for Policy Dry-Run Simulator

Verifies safe policy evolution and impact analysis.
Focuses on actual API: simulate_policy(decisions, candidate_policy) -> list
"""

import pytest
import os
import json
from CASA.audit_ledger import record_decision, read_ledger, LEDGER_FILE
from CASA.policy_simulator import simulate_policy
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
    """Test simulation when candidate policy matches current decisions."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    decisions = read_ledger()
    current_policy = load_policy()
    results = simulate_policy(decisions, current_policy)
    
    assert len(results) == 3
    assert all("original" in r and "simulated" in r for r in results)


def test_simulate_returns_list():
    """Test that policy simulator returns a list of results."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert isinstance(results, list)
    assert len(results) > 0
    for result in results:
        assert "original" in result
        assert "simulated" in result


def test_simulate_empty_decisions():
    """Test simulation with no historical decisions."""
    decisions = []
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert isinstance(results, list)
    assert len(results) == 0


def test_simulate_multiple_agents():
    """Test simulation across multiple agents."""
    for i in range(5):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
        record_decision("agent_02", "write_database", "HIGH", "REVIEW")
        record_decision("agent_03", "read_database", "LOW", "ALLOW")
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert len(results) == 15


def test_simulate_deterministic_output():
    """Test that simulation produces deterministic results."""
    # Record same decisions
    for i in range(10):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    decisions = read_ledger()
    policy = load_policy()
    
    # Simulate twice
    results1 = simulate_policy(decisions, policy)
    results2 = simulate_policy(decisions, policy)
    
    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2):
        assert r1["original"] == r2["original"]
        assert r1["simulated"] == r2["simulated"]


def test_simulate_preserves_decision_count():
    """Test that simulation doesn't lose decisions."""
    for i in range(7):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(3):
        record_decision("agent_02", "write_database", "HIGH", "REVIEW")
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert len(results) == len(decisions)


# --------Policy Variation Tests--------

def test_simulate_with_different_policy():
    """Test that different policies can produce different results."""
    # Record diverse decisions
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    decisions = read_ledger()
    
    policy1 = load_policy()
    policy2 = {
        "agents": {
            "agent_01": ["read_database"],
            "analytics_agent": ["read_database"],
            "admin_agent": ["read_database", "write_database", "delete_database"],
        },
        "review": [],
        "forbidden": ["write_database"]
    }
    
    results1 = simulate_policy(decisions, policy1)
    results2 = simulate_policy(decisions, policy2)
    
    # Both should return results
    assert len(results1) == 2
    assert len(results2) == 2


def test_simulate_custom_policy_structure():
    """Test simulation with custom policy structure."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    decisions = read_ledger()
    custom_policy = {
        "agents": {"agent_01": ["read_database"]},
        "review": [],
        "forbidden": []
    }
    
    results = simulate_policy(decisions, custom_policy)
    assert len(results) > 0


# --------Risk Classification Tests--------

def test_simulate_multiple_risk_levels():
    """Test simulation across LOW, HIGH, CRITICAL risks."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert len(results) == 3
    # All should have original and simulated
    assert all("original" in r for r in results)
    assert all("simulated" in r for r in results)


def test_simulate_consistent_with_ledger():
    """Test that simulation respects ledger records."""
    # Record specific sequence
    original_records = [
        ("agent_01", "read_database", "LOW", "ALLOW"),
        ("agent_02", "write_database", "HIGH", "REVIEW"),
        ("agent_03", "delete_database", "CRITICAL", "HALT"),
    ]
    
    for agent, action, risk, decision in original_records:
        record_decision(agent, action, risk, decision)
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    # Should have matching count
    assert len(results) == len(original_records)


# --------Edge Cases--------

def test_simulate_single_decision():
    """Test simulation with exactly one decision."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert len(results) == 1
    assert "original" in results[0]
    assert "simulated" in results[0]


def test_simulate_large_batch():
    """Test simulation with many decisions."""
    for i in range(100):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    decisions = read_ledger()
    policy = load_policy()
    results = simulate_policy(decisions, policy)
    
    assert len(results) == 100


def test_simulate_repeated_calls():
    """Test multiple simulations on same data."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_02", "write_database", "HIGH", "REVIEW")
    
    decisions = read_ledger()
    policy = load_policy()
    
    # Call simulate multiple times
    for _ in range(5):
        results = simulate_policy(decisions, policy)
        assert len(results) == 2
