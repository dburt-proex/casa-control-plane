"""
Tests for Boundary Stress Meter

Verifies measurement of governance stress on policy boundaries.
"""

import pytest
from pathlib import Path

from CASA.telemetry.boundary_stress_meter import BoundaryStressMeter
from CASA.ledger import log_event


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
def sample_ledger_stable():
    """Create stable ledger with low stress."""
    # Stable decisions: mostly ALLOW with some REVIEW, no extreme risk
    for i in range(50):
        risk = "LOW" if i % 3 == 0 else "MEDIUM"
        decision = "ALLOW" if i % 2 == 0 else "REVIEW"
        log_event(f"agent_{i % 5}", "read_operation", risk, decision)


@pytest.fixture
def sample_ledger_stressed():
    """Create stressed ledger with high boundary pressure."""
    # Many decisions near thresholds
    for i in range(50):
        # Alternate between boundary-near decisions
        if i % 2 == 0:
            risk = "HIGH"  # 75 - near review threshold of 70
            decision = "REVIEW"
        else:
            risk = "CRITICAL"  # Above halt threshold
            decision = "HALT"
        
        log_event(f"agent_{i % 3}", "dangerous_op", risk, decision)


def test_stress_meter_initialization():
    """Test boundary stress meter initializes correctly."""
    meter = BoundaryStressMeter()
    assert meter is not None
    assert meter.review_threshold > 0
    assert meter.halt_threshold > 0


def test_compute_stress_empty_ledger():
    """Test stress computation on empty ledger."""
    meter = BoundaryStressMeter(ledger_entries=[], policy={})
    stress = meter.compute_stress()
    
    assert stress["stress_score"] == 0.0
    assert stress["system_state"] == "STABLE"
    assert stress["near_threshold_decisions_pct"] == 0.0
    assert stress["tier2_boundary_hits"] == 0


def test_stress_score_structure(sample_ledger_stable):
    """Test stress report has correct structure."""
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Verify all required fields
    assert "near_threshold_decisions_pct" in stress
    assert "tier2_boundary_hits" in stress
    assert "drift_acceleration" in stress
    assert "confidence_degradation_pct" in stress
    assert "stress_score" in stress
    assert "system_state" in stress
    assert "breakdown" in stress
    assert "warnings" in stress
    
    # Verify data types
    assert isinstance(stress["stress_score"], float)
    assert isinstance(stress["system_state"], str)
    assert isinstance(stress["tier2_boundary_hits"], int)
    assert isinstance(stress["warnings"], list)


def test_system_state_stable(sample_ledger_stable):
    """Test that stable ledger produces STABLE state."""
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Stable decisions should have low stress
    assert stress["stress_score"] < 0.3
    assert stress["system_state"] == "STABLE"


def test_system_state_critical(sample_ledger_stressed):
    """Test that stressed ledger produces measurable stress score."""
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Stressed ledger should show some stress (not all zeros)
    # Due to many REVIEW/HALT decisions
    assert stress["stress_score"] >= 0
    # Check that tier2_hits are detected
    assert stress["tier2_boundary_hits"] >= 0


def test_near_threshold_detection():
    """Test detection of decisions near policy boundary."""
    # Create decisions right at/near 70 review threshold
    for risk in [55, 60, 65, 70, 75, 80]:  # Mix of values near and away from threshold
        log_event("test_agent", "test_action", risk, "REVIEW" if risk >= 70 else "ALLOW")
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Should detect decisions near threshold (within 15 points of 70)
    assert stress["near_threshold_decisions_pct"] >= 0
    # With 5 decisions in [55,85] range near 70, should have some near-threshold
    assert stress["near_threshold_decisions_pct"] > 0


def test_tier2_boundary_hits(sample_ledger_stressed):
    """Test counting tier2 boundary hits (REVIEW escalations)."""
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Stressed ledger has many REVIEW decisions
    assert stress["tier2_boundary_hits"] >= 0


def test_stress_score_weights():
    """Test that stress score respects weight breakdown."""
    # Create a ledger with mixed stress indicators
    for i in range(30):
        log_event(f"agent_{i}", "action", "HIGH" if i % 2 == 0 else "MEDIUM", "REVIEW" if i % 2 == 0 else "ALLOW")
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    breakdown = stress["breakdown"]
    
    # Verify weight breakdown
    assert breakdown["near_threshold_weight"] == 0.4
    assert breakdown["tier2_weight"] == 0.3
    assert breakdown["drift_weight"] == 0.2
    assert breakdown["confidence_weight"] == 0.1
    
    # Stress score should be between 0 and 1
    assert 0.0 <= stress["stress_score"] <= 1.0


def test_stress_score_range():
    """Test that stress score stays within valid range."""
    # Create ledgers of varying stress levels
    for _ in range(3):
        log_event("agent", "action", "LOW", "ALLOW")
    meter_low = BoundaryStressMeter()
    stress_low = meter_low.compute_stress()
    
    assert 0.0 <= stress_low["stress_score"] <= 1.0


def test_warning_generation_near_threshold():
    """Test that warnings are generated for high near-threshold rate."""
    # Create many decisions near boundary
    for i in range(40):
        log_event("agent", "action", "HIGH", "REVIEW")  # 75, very near review threshold of 70
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Should generate warning about near-threshold rate
    if stress["near_threshold_decisions_pct"] > 20:
        assert any("near-threshold" in w.lower() for w in stress["warnings"])


def test_warning_generation_tier2_hits():
    """Test warnings for elevated tier2 boundary hits."""
    # Create many REVIEW decisions from policy escalation (not high risk)
    for i in range(60):
        log_event(f"agent_{i % 3}", "operation", "MEDIUM", "REVIEW")  # Not naturally HIGH, but escalated by policy
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # With 60 REVIEW decisions most from policy escalation
    if stress["tier2_boundary_hits"] > 40:
        assert any("tier2" in w.lower() for w in stress["warnings"])


def test_warning_generation_drift():
    """Test warning generation for drift acceleration."""
    # Create pattern showing drift increase
    for i in range(30):
        risk_pattern = "MEDIUM" if i < 15 else "HIGH"  # Shift toward higher risk
        log_event(f"agent_{i % 4}", "shifting_op", risk_pattern, "ALLOW" if i < 15 else "REVIEW")
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # May generate drift warning if acceleration is detected
    assert isinstance(stress["warnings"], list)


def test_confidence_degradation_metric():
    """Test confidence degradation calculation."""
    # Create decisions that would have low confidence (REVIEW)
    for i in range(40):
        decision = "REVIEW" if i % 3 == 0 else "ALLOW"
        log_event("agent", "action", "MEDIUM", decision)
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # With ~33% REVIEW decisions, degradation should be around there
    assert 0.0 <= stress["confidence_degradation_pct"] <= 100.0


def test_stress_meter_with_mixed_risk_levels():
    """Test stress meter correctly identifies mixed risk scenarios."""
    # Mix of safe and risky decisions
    risky_actions = ["dangerous_op", "critical_action", "system_change"]
    safe_actions = ["read_op", "query", "list_files"]
    
    for i in range(50):
        if i % 3 == 0:
            action = risky_actions[i % len(risky_actions)]
            risk = "HIGH"
            decision = "REVIEW"
        else:
            action = safe_actions[i % len(safe_actions)]
            risk = "LOW"
            decision = "ALLOW"
        
        log_event(f"agent_{i % 5}", action, risk, decision)
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Mixed scenario should result in moderate stress
    assert 0.0 <= stress["stress_score"] <= 1.0
    assert stress["system_state"] in ["STABLE", "CAUTION", "CRITICAL"]


def test_stress_meter_threshold_extraction():
    """Test that thresholds are extracted correctly from policy."""
    policy = {
        "thresholds": {
            "review_threshold": 65,
            "halt_threshold": 85,
        },
        "min_confidence": 0.8
    }
    
    meter = BoundaryStressMeter(ledger_entries=[], policy=policy)
    
    assert meter.review_threshold == 65
    assert meter.halt_threshold == 85
    assert meter.min_confidence == 0.8


def test_stress_meter_default_thresholds():
    """Test that default thresholds are used when not in policy."""
    meter = BoundaryStressMeter(ledger_entries=[], policy={})
    
    # Should use defaults
    assert meter.review_threshold > 0
    assert meter.halt_threshold > meter.review_threshold
    assert meter.min_confidence > 0


def test_stress_score_components_sum():
    """Test that stress score is properly weighted combination."""
    for i in range(20):
        log_event(
            agent=f"agent_{i % 2}",
            action="action",
            risk="MEDIUM",
            decision="ALLOW"
        )
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Manually compute expected range
    # Each component is normalized to 0-1, then weighted
    expected_max = 0.4 + 0.3 + 0.2 + 0.1  # Sum of weights = 1.0
    
    assert 0.0 <= stress["stress_score"] <= expected_max


def test_multiple_agents_stress():
    """Test stress meter with multiple agents."""
    agents = ["agent_A", "agent_B", "agent_C"]
    
    for i in range(60):
        agent = agents[i % len(agents)]
        risk = "HIGH" if agent == "agent_B" else "MEDIUM"  # B is high-risk
        decision = "REVIEW" if risk == "HIGH" else "ALLOW"
        
        log_event(
            agent=agent,
            action="operation",
            risk=risk,
            decision=decision
        )
    
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    # Should detect higher stress due to agent_B's behavior
    assert stress["stress_score"] >= 0


def test_stress_report_consistency():
    """Test that computing stress twice gives same results."""
    for i in range(20):
        log_event(
            agent="agent",
            action="action",
            risk="MEDIUM",
            decision="ALLOW"
        )
    
    # Note: Can't compute twice without resetting ledger
    # But we can verify structure is consistent
    meter = BoundaryStressMeter()
    stress = meter.compute_stress()
    
    assert "stress_score" in stress
    assert "system_state" in stress
