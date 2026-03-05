"""
Boundary Stress Meter

Measures how close governance decisions operate to policy limits.

Exposes systemic risk before boundaries are crossed.

Think: "AI governance flight instrumentation"
"""

from typing import Dict, List, Any
from CASA.audit_ledger import read_ledger
from CASA.policy_loader import load_policy
from CASA.telemetry.drift_monitor import DriftMonitor


class BoundaryStressMeter:
    """Measures stress on governance policy boundaries."""
    
    def __init__(self, ledger_entries: List[Dict[str, Any]] = None, policy: Dict[str, Any] = None):
        """Initialize stress meter.
        
        Args:
            ledger_entries: Historical decisions (if None, reads from ledger)
            policy: Policy configuration (if None, loads current policy)
        """
        self.ledger = ledger_entries or read_ledger()
        self.policy = policy or load_policy()
        self.drift_monitor = DriftMonitor(self.ledger)
        
        # Extract policy thresholds
        self.review_threshold = self._extract_threshold("review", 70)
        self.halt_threshold = self._extract_threshold("halt", 85)
        self.min_confidence = self.policy.get("min_confidence", 0.7)
    
    def compute_stress(self) -> Dict[str, Any]:
        """Compute complete boundary stress metrics.
        
        Returns:
            {
                "near_threshold_decisions_pct": float,
                "tier2_boundary_hits": int,
                "drift_acceleration": float,
                "confidence_degradation_pct": float,
                "stress_score": float,
                "system_state": str,
                "breakdown": {...},
                "warnings": [...],
            }
        """
        if not self.ledger:
            return self._empty_stress_report()
        
        # Compute individual metrics
        near_threshold_pct = self._compute_near_threshold_decisions()
        tier2_hits = self._compute_tier2_boundary_hits()
        drift_acceleration = self._compute_drift_acceleration()
        confidence_degradation = self._compute_confidence_degradation()
        
        # Aggregate stress score
        stress_score = (
            0.4 * (near_threshold_pct / 100.0) +  # Normalize to 0-1
            0.3 * min(tier2_hits / 100.0, 1.0) +  # Normalize hits to 0-1
            0.2 * min(abs(drift_acceleration), 1.0) +  # Normalize drift to 0-1
            0.1 * (confidence_degradation / 100.0)  # Normalize to 0-1
        )
        
        stress_score = min(stress_score, 1.0)  # Cap at 1.0
        
        return {
            "near_threshold_decisions_pct": round(near_threshold_pct, 2),
            "tier2_boundary_hits": tier2_hits,
            "drift_acceleration": round(drift_acceleration, 4),
            "confidence_degradation_pct": round(confidence_degradation, 2),
            "stress_score": round(stress_score, 3),
            "system_state": self._get_system_state(stress_score),
            "breakdown": {
                "near_threshold_weight": 0.4,
                "tier2_weight": 0.3,
                "drift_weight": 0.2,
                "confidence_weight": 0.1,
            },
            "warnings": self._generate_warnings(
                near_threshold_pct, tier2_hits, drift_acceleration, confidence_degradation
            ),
        }
    
    def _compute_near_threshold_decisions(self) -> float:
        """Compute percentage of decisions operating near review boundary.
        
        near_threshold = abs(risk_score - review_threshold) <= threshold_margin
        """
        if not self.ledger:
            return 0.0
        
        threshold_margin = 15  # decisions within 15 points of boundary
        near_threshold_count = 0
        
        for entry in self.ledger:
            risk = entry.get("risk")
            if isinstance(risk, str):
                risk_map = {"LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 95}
                risk_score = risk_map.get(risk, 50)
            else:
                risk_score = risk
            
            # Check if near review threshold
            if abs(risk_score - self.review_threshold) <= threshold_margin:
                near_threshold_count += 1
        
        return (near_threshold_count / len(self.ledger)) * 100 if self.ledger else 0.0
    
    def _compute_tier2_boundary_hits(self) -> int:
        """Count actions triggering review due to policy tier rules.
        
        Tier2 hits = actions that resulted in REVIEW when they wouldn't normally.
        """
        tier2_hits = 0
        
        for entry in self.ledger:
            decision = entry.get("decision")
            risk = entry.get("risk")
            
            # A "tier2 hit" is a decision bumped to REVIEW by policy even if risk is lower
            if decision == "REVIEW":
                if isinstance(risk, str):
                    risk_map = {"LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 95}
                    risk_score = risk_map.get(risk, 50)
                else:
                    risk_score = risk
                
                # If risk is below high threshold but still REVIEW, it's a tier2 hit
                if risk_score < 75:
                    tier2_hits += 1
        
        return tier2_hits
    
    def _compute_drift_acceleration(self) -> float:
        """Detect sudden change in drift index trend.
        
        drift_acceleration = drift_t - drift_t_minus_5
        """
        # Get drift index over time
        drift_indices = []
        time_window = min(10, len(self.ledger))
        
        # Split ledger into recent chunks and compute drift for each
        if self.ledger:
            chunk_size = max(1, len(self.ledger) // time_window)
            
            for i in range(0, len(self.ledger), chunk_size):
                chunk = self.ledger[i:i+chunk_size]
                if chunk:
                    monitor = DriftMonitor(chunk)
                    drift_indices.append(monitor.drift_index())
        
        # Compute acceleration as difference between recent and older drift
        if len(drift_indices) >= 2:
            recent_drift = drift_indices[-1]
            old_drift = drift_indices[0]
            acceleration = recent_drift - old_drift
            return acceleration
        
        return 0.0
    
    def _compute_confidence_degradation(self) -> float:
        """Measure percentage of decisions with confidence < min_confidence."""
        confidence_degradation_count = 0
        
        # Estimate confidence based on decision patterns
        for entry in self.ledger:
            decision = entry.get("decision")
            risk = entry.get("risk")
            
            # Estimate confidence: ALLOW = high confidence, HALT = high confidence, REVIEW = medium
            if decision == "REVIEW":
                estimated_confidence = 0.6
            elif decision in ["ALLOW", "HALT"]:
                estimated_confidence = 0.85
            else:
                estimated_confidence = 0.7
            
            if estimated_confidence < self.min_confidence:
                confidence_degradation_count += 1
        
        return (confidence_degradation_count / len(self.ledger)) * 100 if self.ledger else 0.0
    
    def _get_system_state(self, stress_score: float) -> str:
        """Determine system state from stress score.
        
        0.0 → STABLE
        0.5 → CAUTION
        0.75 → CRITICAL
        """
        if stress_score < 0.3:
            return "STABLE"
        elif stress_score < 0.6:
            return "CAUTION"
        else:
            return "CRITICAL"
    
    def _generate_warnings(
        self,
        near_threshold_pct: float,
        tier2_hits: int,
        drift_acceleration: float,
        confidence_degradation: float
    ) -> List[str]:
        """Generate warnings based on stress metrics."""
        warnings = []
        
        if near_threshold_pct > 20:
            warnings.append(f"High near-threshold rate: {near_threshold_pct:.1f}% of decisions operating near policy boundary")
        
        if tier2_hits > 50:
            warnings.append(f"Elevated tier2 boundary hits: {tier2_hits} decisions escalated due to policy rules")
        
        if drift_acceleration > 0.3:
            warnings.append(f"Drift acceleration detected: +{drift_acceleration:.3f} indicates system instability")
        
        if drift_acceleration < -0.2:
            warnings.append(f"Rapid drift recovery: -{abs(drift_acceleration):.3f} indicates system re-stabilization")
        
        if confidence_degradation > 15:
            warnings.append(f"Confidence degradation: {confidence_degradation:.1f}% of decisions below min confidence")
        
        return warnings
    
    def _extract_threshold(self, threshold_type: str, default: float) -> float:
        """Extract threshold from policy configuration."""
        thresholds = self.policy.get("thresholds", {})
        
        if isinstance(thresholds, dict):
            return thresholds.get(f"{threshold_type}_threshold", default)
        
        return default
    
    def _empty_stress_report(self) -> Dict[str, Any]:
        """Return empty stress report when no decisions."""
        return {
            "near_threshold_decisions_pct": 0.0,
            "tier2_boundary_hits": 0,
            "drift_acceleration": 0.0,
            "confidence_degradation_pct": 0.0,
            "stress_score": 0.0,
            "system_state": "STABLE",
            "breakdown": {
                "near_threshold_weight": 0.4,
                "tier2_weight": 0.3,
                "drift_weight": 0.2,
                "confidence_weight": 0.1,
            },
            "warnings": [],
        }
