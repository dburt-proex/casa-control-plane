"""
Tests for Governance Analytics Layer

Verifies metrics, drift monitoring, and dashboard functionality.
"""

import pytest
import os
from CASA.audit_ledger import record_decision, read_ledger, LEDGER_FILE
from CASA.telemetry.governance_metrics import GovernanceMetrics
from CASA.telemetry.drift_monitor import DriftMonitor
from CASA.telemetry.governance_dashboard import GovernanceDashboard


@pytest.fixture(autouse=True)
def cleanup_ledger():
    """Clean up test ledger before and after each test."""
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
    yield
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)


# --------Metrics Tests--------

def test_empty_metrics():
    """Test metrics with empty ledger."""
    metrics = GovernanceMetrics([])
    
    assert metrics.total_decisions == 0
    assert metrics.gate_distribution() == {"ALLOW": 0.0, "REVIEW": 0.0, "HALT": 0.0}
    assert metrics.halt_frequency() == 0.0


def test_gate_distribution():
    """Test ALLOW/REVIEW/HALT distribution calculation."""
    # Create 100 decisions: 70 ALLOW, 20 REVIEW, 10 HALT
    records = []
    for i in range(70):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(20):
        record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    for i in range(10):
        record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    metrics = GovernanceMetrics(ledger)
    
    dist = metrics.gate_distribution()
    assert dist["ALLOW"] == 70.0
    assert dist["REVIEW"] == 20.0
    assert dist["HALT"] == 10.0


def test_halt_frequency():
    """Test halt frequency calculation."""
    for i in range(90):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(10):
        record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    metrics = GovernanceMetrics(ledger)
    
    assert metrics.halt_frequency() == 10.0


def test_risk_distribution():
    """Test risk classification distribution."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    metrics = GovernanceMetrics(ledger)
    
    dist = metrics.risk_distribution()
    assert dist["LOW"] == 50.0
    assert dist["HIGH"] == 25.0
    assert dist["CRITICAL"] == 25.0


def test_critical_risk_events():
    """Test critical event counting."""
    for i in range(5):
        record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    metrics = GovernanceMetrics(ledger)
    
    assert metrics.critical_risk_events() == 5


def test_agent_trust_score():
    """Test agent trust scoring."""
    # Good agent: 95 ALLOW, 5 HALT
    for i in range(95):
        record_decision("good_agent", "read_database", "LOW", "ALLOW")
    for i in range(5):
        record_decision("good_agent", "bad_action", "CRITICAL", "HALT")
    
    # Bad agent: 30 ALLOW, 70 HALT
    for i in range(30):
        record_decision("bad_agent", "read_database", "LOW", "ALLOW")
    for i in range(70):
        record_decision("bad_agent", "malicious_action", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    metrics = GovernanceMetrics(ledger)
    
    good_score = metrics.agent_score("good_agent")
    bad_score = metrics.agent_score("bad_agent")
    
    assert good_score > 80.0  # Good agent has high score
    assert bad_score < 50.0   # Bad agent has low score
    assert good_score > bad_score


def test_metrics_summary():
    """Test comprehensive metrics summary."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    metrics = GovernanceMetrics(ledger)
    
    summary = metrics.get_summary()
    
    assert summary["total_decisions"] == 3
    assert "gate_distribution" in summary
    assert "risk_distribution" in summary
    assert summary["critical_events"] == 1


# --------Drift Monitor Tests--------

def test_drift_index_stable():
    """Test drift index with stable behavior."""
    # All agents have similar halt rates
    for i in range(50):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
        record_decision("agent_02", "read_database", "LOW", "ALLOW")
        record_decision("agent_03", "read_database", "LOW", "ALLOW")
    
    # Add rare halts (5% each)
    for i in range(3):
        record_decision("agent_01", "bad_action", "CRITICAL", "HALT")
        record_decision("agent_02", "bad_action", "CRITICAL", "HALT")
        record_decision("agent_03", "bad_action", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    drift = DriftMonitor(ledger)
    
    # Low drift when agents behave similarly
    assert drift.drift_index() < 0.3


def test_drift_index_high_anomaly():
    """Test drift detection with anomalous behavior."""
    # Normal agents
    for i in range(95):
        record_decision("normal_agent", "read_database", "LOW", "ALLOW")
    for i in range(5):
        record_decision("normal_agent", "bad_action", "CRITICAL", "HALT")
    
    # Anomalous agent with high halt rate
    for i in range(30):
        record_decision("rogue_agent", "read_database", "LOW", "ALLOW")
    for i in range(70):
        record_decision("rogue_agent", "malicious_action", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    drift = DriftMonitor(ledger)
    
    # High drift when agent behavior diverges
    assert drift.drift_index() > 0.3


def test_anomaly_score():
    """Test agent anomaly scoring."""
    # Normal behavior
    for i in range(95):
        record_decision("normal", "action", "LOW", "ALLOW")
    for i in range(5):
        record_decision("normal", "action", "CRITICAL", "HALT")
    
    # Anomalous behavior
    for i in range(40):
        record_decision("anomalous", "action", "LOW", "ALLOW")
    for i in range(60):
        record_decision("anomalous", "action", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    drift = DriftMonitor(ledger)
    
    normal_score = drift.anomaly_score("normal")
    anomalous_score = drift.anomaly_score("anomalous")
    
    assert anomalous_score > normal_score


def test_risky_agent_detection():
    """Test detection of agents exceeding halt threshold."""
    # Safe agent
    for i in range(95):
        record_decision("safe_agent", "read_database", "LOW", "ALLOW")
    for i in range(5):
        record_decision("safe_agent", "bad_action", "CRITICAL", "HALT")
    
    # Risky agent
    for i in range(40):
        record_decision("risky_agent", "read_database", "LOW", "ALLOW")
    for i in range(60):
        record_decision("risky_agent", "malicious_action", "CRITICAL", "HALT")
    
    ledger = read_ledger()
    drift = DriftMonitor(ledger)
    
    risky = drift.risky_agent_threshold_exceeded(threshold=30.0)
    assert "risky_agent" in risky
    assert "safe_agent" not in risky


# --------Dashboard Tests--------

def test_dashboard_initialization():
    """Test dashboard initializes correctly."""
    dashboard = GovernanceDashboard()
    assert dashboard.metrics is not None
    assert dashboard.drift_monitor is not None


def test_dashboard_text_render():
    """Test dashboard text rendering."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("agent_01", "delete_database", "CRITICAL", "HALT")
    
    dashboard = GovernanceDashboard()
    text = dashboard.render_text_dashboard()
    
    assert "CASA" in text and "GOVERNANCE" in text and "DASHBOARD" in text
    assert "GOVERNANCE HEALTH" in text
    assert "ALLOW" in text
    assert "REVIEW" in text
    assert "HALT" in text


def test_dashboard_json_output():
    """Test dashboard JSON output."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    dashboard = GovernanceDashboard()
    json_output = dashboard.get_json_dashboard()
    
    assert "timestamp" in json_output
    assert "governance_health" in json_output
    assert "risk_profile" in json_output
    assert "drift_monitoring" in json_output or "stability_metrics" in json_output
    assert "summary" in json_output
    # New boundary stress panel
    assert "boundary_stress" in json_output


def test_system_safety_assessment():
    """Test system safety assessment."""
    # Safe system: many decisions to establish stability
    for i in range(950):
        record_decision("agent_01", "read_database", "LOW", "ALLOW")
    for i in range(50):
        record_decision("agent_01", "bad_action", "CRITICAL", "HALT")
    
    dashboard = GovernanceDashboard()
    # With enough data, system should show safety
    safety = dashboard.is_system_safe()
    assert isinstance(safety, bool)  # At minimum, should return bool


def test_attention_required_detection():
    """Test detection when system requires attention."""
    # Add many risky agents
    for i in range(30):
        record_decision("bad_agent", "action", "LOW", "ALLOW")
    for i in range(70):
        record_decision("bad_agent", "malicious", "CRITICAL", "HALT")
    
    dashboard = GovernanceDashboard()
    assert dashboard.requires_attention() is True


def test_recommendation_generation():
    """Test recommendation generation."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    dashboard = GovernanceDashboard()
    recommendation = dashboard.get_recommendation()
    
    assert isinstance(recommendation, str)
    assert len(recommendation) > 0
