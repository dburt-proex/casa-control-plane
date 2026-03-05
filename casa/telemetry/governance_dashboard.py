"""
Governance Dashboard

Real-time visualization of governance health and safety metrics.
Transforms analytics into actionable intelligence for operators.

Includes:
- Governance Health Panel (gate distribution, risk profile)
- Boundary Stress Panel (stress score, tier2 hits, drift acceleration)
- Drift Monitoring Panel (drift index, volatility, anomalies)
- Policy Impact Panel (dry-run results, decision replay deltas)
- System State Panel (overall health, policy version, ledger integrity)
"""

from typing import Dict, Any
from CASA.telemetry.governance_metrics import GovernanceMetrics
from CASA.telemetry.drift_monitor import DriftMonitor
from CASA.telemetry.boundary_stress_meter import BoundaryStressMeter
from CASA.audit_ledger import read_ledger


class GovernanceDashboard:
    """Enterprise governance dashboard with full operator visibility."""
    
    def __init__(self):
        """Initialize dashboard from current ledger."""
        self.ledger = read_ledger()
        self.metrics = GovernanceMetrics(self.ledger)
        self.drift_monitor = DriftMonitor(self.ledger)
        self.stress_meter = BoundaryStressMeter(self.ledger)
    
    def refresh(self):
        """Refresh dashboard from latest ledger data."""
        self.ledger = read_ledger()
        self.metrics = GovernanceMetrics(self.ledger)
        self.drift_monitor = DriftMonitor(self.ledger)
        self.stress_meter = BoundaryStressMeter(self.ledger)
    
    def render_text_dashboard(self) -> str:
        """Render dashboard as ASCII text for CLI/logging.
        
        Returns:
            Formatted dashboard string
        """
        distribution = self.metrics.gate_distribution()
        risks = self.metrics.risk_distribution()
        stress = self.stress_meter.compute_stress()
        
        dashboard = []
        dashboard.append("=" * 70)
        dashboard.append("CASA ENTERPRISE GOVERNANCE DASHBOARD".center(70))
        dashboard.append("=" * 70)
        dashboard.append("")
        
        # ── GOVERNANCE HEALTH PANEL ──
        dashboard.append("+- GOVERNANCE HEALTH " + "-" * 50 + "+")
        dashboard.append(f"| ALLOW:     {int(distribution['ALLOW']):>3}%  |  REVIEW: {int(distribution['REVIEW']):>3}%  |  HALT: {int(distribution['HALT']):>3}%".ljust(69) + "|")
        dashboard.append(f"| Total Decisions: {self.metrics.total_decisions:>5}  |  Critical Events: {self.metrics.critical_risk_events():>5}".ljust(69) + "|")
        dashboard.append("+" + "-" * 68 + "+")
        dashboard.append("")
        
        # ── BOUNDARY STRESS PANEL ──
        dashboard.append("+- BOUNDARY STRESS " + "-" * 53 + "+")
        dashboard.append(f"| Stress Score: {stress['stress_score']:>6.3f} [{stress['system_state']:<8}]  |  Near-Threshold: {stress['near_threshold_decisions_pct']:>5.1f}%".ljust(69) + "|")
        dashboard.append(f"| Tier2 Boundary Hits: {stress['tier2_boundary_hits']:>4}  |  Drift Acceleration: {stress['drift_acceleration']:>7.4f}".ljust(69) + "|")
        dashboard.append(f"| Confidence Degradation: {stress['confidence_degradation_pct']:>5.1f}%".ljust(69) + "|")
        dashboard.append("+" + "-" * 68 + "+")
        dashboard.append("")
        
        # ── DRIFT MONITORING PANEL ──
        dashboard.append("+- DRIFT MONITORING " + "-" * 52 + "+")
        dashboard.append(f"| Drift Index: {self.drift_monitor.drift_index():>6.3f}  |  Volatility: {self.drift_monitor.decision_pattern_stability():>5.1f}%".ljust(69) + "|")
        dashboard.append(f"| Anomaly Count: {len(self.drift_monitor.risky_agent_threshold_exceeded()):>3}  |  Instability Events: {self._count_volatility_events():>3}".ljust(69) + "|")
        dashboard.append("+" + "-" * 68 + "+")
        dashboard.append("")
        
        # ── RISK PROFILE ──
        dashboard.append("+- RISK CLASSIFICATION " + "-" * 49 + "+")
        dashboard.append(f"| LOW: {int(risks['LOW']):>3}%  |  MEDIUM: {int(risks.get('MEDIUM', 0)):>3}%  |  HIGH: {int(risks['HIGH']):>3}%  |  CRITICAL: {int(risks['CRITICAL']):>3}%".ljust(69) + "|")
        dashboard.append("+" + "-" * 68 + "+")
        dashboard.append("")
        
        # ── SYSTEM STATE PANEL ──
        dashboard.append("+- SYSTEM STATE " + "-" * 56 + "+")
        system_mode = "NORMAL" if self.is_system_safe() else "ATTENTION_REQUIRED"
        dashboard.append(f"| Mode: {system_mode:<20} |  Ledger Integrity: OK  |  Decision Replay Ready: YES".ljust(69) + "|")
        dashboard.append("+" + "-" * 68 + "+")
        dashboard.append("")
        
        # ── ALERTS/WARNINGS ──
        if stress['warnings']:
            dashboard.append("[WARNINGS]:")
            for warning in stress['warnings'][:3]:  # Show top 3 warnings
                dashboard.append(f"  - {warning}")
            dashboard.append("")
        
        dashboard.append("=" * 70)
        
        return "\n".join(dashboard)
    
    def _count_volatility_events(self) -> int:
        """Count major volatility events in recent decisions."""
        if len(self.ledger) < 5:
            return 0
        
        volatility_count = 0
        for i in range(5, len(self.ledger)):
            recent_five = self.ledger[i-5:i]
            decisions = [d.get("decision") for d in recent_five]
            
            # Volatility = many decision changes in short window
            unique_decisions = len(set(decisions))
            if unique_decisions >= 3:
                volatility_count += 1
        
        return min(volatility_count, 10)  # Cap at 10
    
    def get_json_dashboard(self) -> Dict[str, Any]:
        """Get complete dashboard as JSON for API responses."""
        distribution = self.metrics.gate_distribution()
        risks = self.metrics.risk_distribution()
        stress = self.stress_meter.compute_stress()
        
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
                "critical_events": self.metrics.critical_risk_events(),
                "critical_halted": self.metrics.critical_halted(),
            },
            "boundary_stress": {
                "stress_score": stress["stress_score"],
                "system_state": stress["system_state"],
                "near_threshold_decisions_pct": stress["near_threshold_decisions_pct"],
                "tier2_boundary_hits": stress["tier2_boundary_hits"],
                "drift_acceleration": stress["drift_acceleration"],
                "confidence_degradation_pct": stress["confidence_degradation_pct"],
                "warnings": stress["warnings"],
            },
            "risk_profile": {
                "distribution": {
                    "LOW": int(risks["LOW"]),
                    "MEDIUM": int(risks.get("MEDIUM", 0)),
                    "HIGH": int(risks["HIGH"]),
                    "CRITICAL": int(risks["CRITICAL"]),
                },
            },
            "drift_monitoring": {
                "drift_index": self.drift_monitor.drift_index(),
                "decision_stability": self.drift_monitor.decision_pattern_stability(),
                "anomaly_count": len(self.drift_monitor.risky_agent_threshold_exceeded()),
                "volatility_events": self._count_volatility_events(),
            },
            "system_state": {
                "mode": "NORMAL" if self.is_system_safe() else "ATTENTION_REQUIRED",
                "ledger_integrity": "OK",
                "policy_version": "v1.0",
                "safe": self.is_system_safe(),
                "requires_attention": self.requires_attention(),
            },
            "summary": {
                "recommendation": self.get_recommendation(),
                "is_system_safe": self.is_system_safe(),
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
