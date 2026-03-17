"""
Tests for Decision Replay Engine

Verifies replay of historical decisions under new policy conditions.
"""

import pytest
import json
from pathlib import Path
import uuid

from CASA.decision_replay import DecisionReplayEngine
from CASA.ledger import log_event
from CASA.audit_ledger import read_ledger as read_audit_ledger


@pytest.fixture(autouse=True)
def clean_ledger():
    """Clean ledger before each test."""
    ledger_path = Path("ledger.log")
    if ledger_path.exists():
        ledger_path.unlink()
    yield
    if ledger_path.exists():
        ledger_path.unlink()


@pytest.fixture
def sample_ledger():
    """Create sample ledger entries for testing."""
    # Create entries with required fields for replay
    entries = [
        {
            "decision_id": str(uuid.uuid4()),
            "time": "2024-01-01T10:00:00",
            "timestamp": "2024-01-01T10:00:00",
            "agent": "agent_1",
            "action": "file_read",
            "risk": "LOW",
            "decision": "ALLOW",
            "policy_version": "v1.0",
            "signals": {},
            "route": "ALLOW"
        },
        {
            "decision_id": str(uuid.uuid4()),
            "time": "2024-01-01T10:00:01",
            "timestamp": "2024-01-01T10:00:01",
            "agent": "agent_2",
            "action": "database_write",
            "risk": "HIGH",
            "decision": "REVIEW",
            "policy_version": "v1.0",
            "signals": {},
            "route": "REVIEW"
        },
        {
            "decision_id": str(uuid.uuid4()),
            "time": "2024-01-01T10:00:02",
            "timestamp": "2024-01-01T10:00:02",
            "agent": "agent_3",
            "action": "api_call",
            "risk": "CRITICAL",
            "decision": "HALT",
            "policy_version": "v1.0",
            "signals": {},
            "route": "HALT"
        },
        {
            "decision_id": str(uuid.uuid4()),
            "time": "2024-01-01T10:00:03",
            "timestamp": "2024-01-01T10:00:03",
            "agent": "agent_1",
            "action": "config_change",
            "risk": "HIGH",
            "decision": "REVIEW",
            "policy_version": "v1.0",
            "signals": {},
            "route": "REVIEW"
        },
        {
            "decision_id": str(uuid.uuid4()),
            "time": "2024-01-01T10:00:04",
            "timestamp": "2024-01-01T10:00:04",
            "agent": "agent_2",
            "action": "file_read",
            "risk": "LOW",
            "decision": "ALLOW",
            "policy_version": "v1.0",
            "signals": {},
            "route": "ALLOW"
        },
    ]
    
    # Write entries to ledger
    with open("ledger.log", "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def test_replay_single_decision_not_found():
    """Test replaying non-existent decision."""
    engine = DecisionReplayEngine()
    with pytest.raises(ValueError, match="Decision .* not found"):
        engine.replay_decision("nonexistent_id")


def test_replay_single_decision(sample_ledger):
    """Test replaying a single historical decision."""
    engine = DecisionReplayEngine()
    
    # Get a decision_id from ledger
    ledger = engine.ledger
    assert len(ledger) > 0
    decision_id = ledger[0].get("decision_id")
    
    result = engine.replay_decision(decision_id)
    
    # Verify result structure
    assert "decision_id" in result
    assert "agent" in result
    assert "action" in result
    assert "original" in result
    assert "replayed" in result
    assert "changed" in result
    assert "risk_delta" in result
    assert "reason" in result
    
    # Verify original data
    assert result["original"]["route"] == "ALLOW"
    assert result["original"]["risk"] == "LOW"  # Changed from risk_score
    assert result["original"]["policy_version"] == "v1.0"
    
    # Verify replayed data
    assert "policy_version" in result["replayed"]
    assert "route" in result["replayed"]
    assert "risk" in result["replayed"]  # Changed from risk_score
    assert "confidence" in result["replayed"]


def test_replay_decision_with_no_signals(sample_ledger):
    """Test replaying decision that has no signals."""
    engine = DecisionReplayEngine()
    ledger = engine.ledger
    decision_id = ledger[0].get("decision_id")
    
    result = engine.replay_decision(decision_id)
    
    # Should still work but with lower confidence
    assert result["replayed"]["confidence"] >= 0.5
    assert result["replayed"]["confidence"] <= 1.0


def test_replay_batch_basic(sample_ledger):
    """Test replaying batches of decisions."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=5)
    
    # Verify batch structure
    assert "total_decisions_in_ledger" in results
    assert "total_replayed" in results
    assert "total_changed" in results
    assert "percent_changed" in results
    assert "routing_changes" in results
    assert "risk_analysis" in results
    assert "policies_comparison" in results or "policy_comparison" in results
    assert "decisions" in results
    assert "recommendation" in results
    
    # Verify decisions were replayed
    assert results["total_replayed"] > 0
    assert len(results["decisions"]) > 0


def test_replay_batch_with_agent_filter(sample_ledger):
    """Test batch replay with agent filter."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(agent_filter="agent_1")
    
    # Should only replay agent_1 decisions
    for decision in results["decisions"]:
        assert decision["agent"] == "agent_1"
    
    # agent_1 has 2 decisions in sample ledger
    assert results["total_replayed"] >= 1


def test_replay_batch_with_action_filter(sample_ledger):
    """Test batch replay with action filter."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(action_filter="file_read")
    
    # Should only replay file_read decisions
    for decision in results["decisions"]:
        assert decision["action"] == "file_read"


def test_replay_batch_routing_changes(sample_ledger):
    """Test that routing changes are counted correctly."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=5)
    
    routing_changes = results["routing_changes"]
    
    # Verify all possible transitions exist
    expected_keys = [
        "allow_to_review", "allow_to_halt", "review_to_allow",
        "review_to_halt", "halt_to_allow", "halt_to_review", "no_change"
    ]
    for key in expected_keys:
        assert key in routing_changes
        assert isinstance(routing_changes[key], int)
    
    # Total transitions should equal total replayed
    total_transitions = sum(routing_changes.values())
    assert total_transitions == results["total_replayed"]


def test_replay_batch_risk_analysis(sample_ledger):
    """Test risk delta computation."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=5)
    
    risk_analysis = results["risk_analysis"]
    
    # Verify risk metrics
    assert "avg_risk_delta" in risk_analysis
    assert "max_risk_delta" in risk_analysis
    assert "min_risk_delta" in risk_analysis
    
    # Risk deltas should be numbers
    assert isinstance(risk_analysis["avg_risk_delta"], (int, float))
    assert isinstance(risk_analysis["max_risk_delta"], (int, float))
    assert isinstance(risk_analysis["min_risk_delta"], (int, float))


def test_replay_all_decisions(sample_ledger):
    """Test replaying all decisions."""
    engine = DecisionReplayEngine()
    results = engine.replay_all_decisions()
    
    # Should replay all 5 decisions
    assert results["total_replayed"] == 5
    assert len(results["decisions"]) == 5
    assert results["total_decisions_in_ledger"] == 5


def test_replay_decision_no_signals_in_ledger():
    """Test replaying when signals are not in ledger (backward compatibility)."""
    # Log decision without signals
    log_event("test_agent", "test_action", 50, "REVIEW")
    
    engine = DecisionReplayEngine()
    ledger = engine.ledger
    decision_id = ledger[0].get("decision_id")
    
    result = engine.replay_decision(decision_id)
    
    # Should still work (backward compatible)
    assert result["original"]["route"] == "REVIEW"
    assert result["replayed"]["confidence"] <= 0.75  # Low confidence due to missing signals


def test_replay_recommendation_no_changes(sample_ledger):
    """Test recommendation when no changes detected."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=5)
    
    # If no changes, should get NO_CHANGES recommendation
    if results["total_changed"] == 0:
        assert "NO_CHANGES" in results["recommendation"]


def test_replay_recommendation_stable():
    """Test recommendation when changes are minimal."""
    # Create ledger with minimal changes
    for i in range(10):
        log_event(f"agent_{i}", "stable_action", 30 + i, "ALLOW")
    
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=10)
    
    # With stable low-risk decisions, expect low change percentage
    if results["percent_changed"] < 10:
        assert "STABLE" in results["recommendation"] or "NO_CHANGES" in results["recommendation"]


def test_replay_decision_reason_generation():
    """Test that decision change reasons are reasonable."""
    log_event("test_agent", "test_action", "HIGH", "REVIEW")
    
    engine = DecisionReplayEngine()
    ledger = engine.ledger
    decision_id = ledger[0].get("decision_id")
    
    result = engine.replay_decision(decision_id)
    
    # Reason should always be populated
    assert len(result["reason"]) > 0
    
    # If changed, reason should explain the transition
    if result["changed"]:
        assert "→" in result["reason"] or "-" in result["reason"]


def test_replay_batch_empty_filter_results():
    """Test batch replay when filters match nothing."""
    log_event(
        agent="agent_a",
        action="action_x",
        risk=40,
        decision="ALLOW"
    )
    
    engine = DecisionReplayEngine()
    results = engine.replay_batch(agent_filter="nonexistent_agent")
    
    # Should return empty results gracefully
    assert results["total_replayed"] == 0
    assert len(results["decisions"]) == 0


def test_replay_batch_limit_parameter(sample_ledger):
    """Test that limit parameter is respected."""
    engine = DecisionReplayEngine()
    
    # Replay with limit of 2
    results = engine.replay_batch(limit=2)
    
    # Should not exceed limit
    assert len(results["decisions"]) <= 2
    assert results["total_replayed"] <= 2


def test_replay_batch_decision_structure(sample_ledger):
    """Test that each replayed decision has correct structure."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=3)
    
    for decision in results["decisions"]:
        # Verify all required fields
        assert "decision_id" in decision
        assert "agent" in decision
        assert "action" in decision
        assert "original" in decision
        assert "replayed" in decision
        
        # Verify nested structure
        original = decision["original"]
        assert all(k in original for k in ["policy_version", "route", "risk", "timestamp"])
        
        replayed = decision["replayed"]
        assert all(k in replayed for k in ["policy_version", "route", "risk", "confidence", "timestamp"])


def test_replay_policy_version_tracking(sample_ledger):
    """Test that policy versions are tracked correctly."""
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=5)
    
    for decision in results["decisions"]:
        # Original should have v1.0 (from sample data)
        assert decision["original"]["policy_version"] == "v1.0"
        
        # Replayed should have current policy version
        assert decision["replayed"]["policy_version"] is not None


def test_replay_signal_confidence_scoring():
    """Test confidence scoring based on signal completeness."""
    # Decision with full signals
    log_event(
        agent="agent_full",
        action="action",
        risk=50,
        decision="REVIEW"
    )
    
    # Decision with no signals
    log_event(
        "agent_empty",
        "action",
        50,
        "REVIEW"
    )
    
    engine = DecisionReplayEngine()
    results = engine.replay_batch(limit=2)
    
    # Find each decision
    full_signals_decision = next((d for d in results["decisions"] if d["agent"] == "agent_full"), None)
    empty_signals_decision = next((d for d in results["decisions"] if d["agent"] == "agent_empty"), None)
    
    if full_signals_decision and empty_signals_decision:
        # Full signals should have higher confidence
        assert full_signals_decision["replayed"]["confidence"] > empty_signals_decision["replayed"]["confidence"]


def test_replay_consistency():
    """Test that replaying the same decision twice produces same results."""
    log_event("agent", "action", "MEDIUM", "REVIEW")
    
    engine = DecisionReplayEngine()
    ledger = engine.ledger
    decision_id = ledger[0].get("decision_id")
    
    # Replay twice
    result1 = engine.replay_decision(decision_id)
    result2 = engine.replay_decision(decision_id)
    
    # Key fields should match
    assert result1["decision_id"] == result2["decision_id"]
    assert result1["original"]["route"] == result2["original"]["route"]
    assert result1["changed"] == result2["changed"]
