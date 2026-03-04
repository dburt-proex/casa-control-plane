"""
Governance Dashboard

Real-time visualization of governance health and safety metrics.
Transforms analytics into actionable intelligence for operators.
"""

from typing import Dict, Any
from CASA.telemetry.governance_metrics import GovernanceMetrics
from CASA.telemetry.drift_monitor import DriftMonitor
from CASA.audit_ledger import read_ledger


class GovernanceDashboard:
    """Real-time governance health dashboard."""
    
    def __init__(self):
        """Initialize dashboard from current ledger."""
        self.ledger = read_ledger()
        self.metrics = GovernanceMetrics(self.ledger)
        self.drift_monitor = DriftMonitor(self.ledger)
    
    def refresh(self):
        """Refresh dashboard from latest ledger data."""
        self.ledger = read_ledger()
        self.metrics = GovernanceMetrics(self.ledger)
        self.drift_monitor = DriftMonitor(self.ledger)
    
    def render_text_dashboard(self) -> str:
        """Render dashboard as ASCII text for CLI/logging.
        
        Returns:
            Formatted dashboard string
        """
        distribution = self.metrics.gate_distribution()
        risks = self.metrics.risk_distribution()
        
        dashboard = []
        dashboard.append("=" * 60)
        dashboard.append("CASA GOVERNANCE DASHBOARD")
        dashboard.append("=" * 60)
        dashboard.append("")
        
        # Gate Distribution
        dashboard.append("DECISION DISTRIBUTION")
        dashboard.append(f"  ALLOW:  {int(distribution['ALLOW']):>3}%")
        dashboard.append(f"  REVIEW: {int(distribution['REVIEW']):>3}%")
        dashboard.append(f"  HALT:   {int(distribution['HALT']):>3}%")
        dashboard.append("")
        
        # Risk Distribution
        dashboard.append("RISK CLASSIFICATION")
        dashboard.append(f"  LOW:      {int(risks['LOW']):>3}%")
        dashboard.append(f"  HIGH:     {int(risks['HIGH']):>3}%")
        dashboard.append(f"  CRITICAL: {int(risks['CRITICAL']):>3}%")
        dashboard.append("")
        
        # Governance Metrics
        dashboard.append("GOVERNANCE METRICS")
        dashboard.append(f"  Total Decisions:      {self.metrics.total_decisions}")
        dashboard.append(f"  Halt Frequency:       {self.metrics.halt_frequency()}%")
        dashboard.append(f"  Review Frequency:     {self.metrics.review_frequency()}%")
        dashboard.append(f"  Critical Events:      {self.metrics.critical_risk_events()}")
        dashboard.append(f"  Critical Halted:      {self.metrics.critical_halted()}")
        dashboard.append("")
        
        # Drift Metrics
        dashboard.append("DRIFT & STABILITY")
        dashboard.append(f"  Drift Index:          {self.drift_monitor.drift_index()}")
        dashboard.append(f"  Decision Stability:   {self.drift_monitor.decision_pattern_stability()}%")
        dashboard.append("")
        
        # Risk Indicators
        dashboard.append("ANOMALIES & RISKS")
        high_risk = self.drift_monitor.risky_agent_threshold_exceeded()
        if high_risk:
            dashboard.append(f"  High-Risk Agents:     {', '.join(high_risk)}")
            for agent in high_risk:
                score = self.drift_monitor.anomaly_score(agent)
                dashboard.append(f"    - {agent}: {score}% anomaly")
        else:
            dashboard.append("  High-Risk Agents:     NONE")
        
        dashboard.append("")
        dashboard.append("=" * 60)
        
        return "\n".join(dashboard)
    
    def get_json_dashboard(self) -> Dict[str, Any]:
        """Get dashboard as JSON for API responses."""
        distribution = self.metrics.gate_distribution()
        risks = self.metrics.risk_distribution()
        
        return {
            "timestamp": self._get_timestamp(),
            "governance_health": {
                "total_decisions": self.metrics.total_decisions,
                "decision_distribution": {
                    "ALLOW": int(distribution["ALLOW"]),
                    "REVIEW": int(distribution["REVIEW"]),
                    "HALT": int(distribution["HALT"]),
                },
                "halt_frequency": self.metrics.halt_frequency(),
                "review_frequency": self.metrics.review_frequency(),
            },
            "risk_profile": {
                "distribution": {
                    "LOW": int(risks["LOW"]),
                    "HIGH": int(risks["HIGH"]),
                    "CRITICAL": int(risks["CRITICAL"]),
                },
                "critical_events": self.metrics.critical_risk_events(),
                "critical_halted": self.metrics.critical_halted(),
            },
            "stability_metrics": {
                "drift_index": self.drift_monitor.drift_index(),
                "decision_stability": self.drift_monitor.decision_pattern_stability(),
            },
            "anomalies": {
                "high_risk_agents": self.drift_monitor.risky_agent_threshold_exceeded(),
                "agent_halt_rates": self.drift_monitor.halt_rate_by_agent(),
            },
            "summary": {
                "system_safe": self.is_system_safe(),
                "requires_attention": self.requires_attention(),
                "recommendation": self.get_recommendation(),
            }
        }
    
    def is_system_safe(self) -> bool:
        """Determine if system is operating safely (simple heuristic)."""
        halt_freq = self.metrics.halt_frequency()
        drift = self.drift_monitor.drift_index()
        stability = self.drift_monitor.decision_pattern_stability()
        
        # Safe if: low halts, low drift, high stability
        return halt_freq < 10.0 and drift < 0.4 and stability > 70.0
    
    def requires_attention(self) -> bool:
        """Determine if system requires operational attention."""
        high_risk = self.drift_monitor.risky_agent_threshold_exceeded(threshold=25.0)
        return len(high_risk) > 0 or self.metrics.halt_frequency() > 20.0
    
    def get_recommendation(self) -> str:
        """Get recommendation for operators."""
        if self.is_system_safe():
            return "System operating normally. No action required."
        
        if self.metrics.halt_frequency() > 25.0:
            return "ALERT: High halt rate. Review policy or agent behavior."
        
        if self.drift_monitor.drift_index() > 0.5:
            return "WARNING: High drift detected. Investigate anomalous agents."
        
        if self.drift_monitor.decision_pattern_stability() < 60.0:
            return "WARNING: Decision patterns unstable. Monitor for degradation."
        
        return "Review system metrics. Some thresholds exceeded."
    
    def _get_timestamp(self) -> str:
        """Get current timestamp ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
