"""
Policy Dry-Run Simulator

Simulates governance policy changes against historical ledger decisions
to predict impact and identify conflicts before production deployment.
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict
from CASA.audit_ledger import read_ledger
from CASA.policy_loader import check_policy, load_policy
from CASA.gate_engine import gate_decision
from CASA.risk_engine import classify_risk


class PolicySimulator:
    """Simulates policy changes against historical decisions."""
    
    def __init__(self, policy_candidate: Dict[str, Any], ledger_entries: List[Dict[str, Any]] = None):
        """Initialize simulator with candidate policy and historical decisions.
        
        Args:
            policy_candidate: New policy to test
            ledger_entries: Historical decisions (if None, loads from ledger)
        """
        self.policy_candidate = policy_candidate
        self.ledger_entries = ledger_entries or read_ledger()
        self.current_policy = load_policy()
    
    def simulate(self) -> Dict[str, Any]:
        """Run complete policy simulation against historical decisions.
        
        Returns:
            {
                "decisions_analyzed": int,
                "decisions_that_change": int,
                "original_distribution": {...},
                "simulated_distribution": {...},
                "routing_changes": {
                    "allow_to_review": int,
                    "allow_to_halt": int,
                    "review_to_allow": int,
                    "review_to_halt": int,
                    "halt_to_allow": int,
                    "halt_to_review": int,
                },
                "metric_changes": {
                    "halt_increase_pct": float,
                    "review_increase_pct": float,
                    "allow_decrease_pct": float,
                },
                "conflicts": [
                    {
                        "type": "permission_boundary",
                        "agent": str,
                        "action": str,
                        "original": str,
                        "simulated": str,
                    },
                    ...
                ],
                "risk_indicators": {...},
                "confidence": float,  # 0-100
                "recommendation": str,
            }
        """
        if not self.ledger_entries:
            return self._empty_report()
        
        # Re-evaluate each historical decision with candidate policy
        results = self._evaluate_all_decisions()
        
        # Compute metrics and conflicts
        metrics = self._compute_metrics(results)
        conflicts = self._identify_conflicts(results)
        risk_indicators = self._assess_risk(results)
        confidence = self._compute_confidence_score(results)
        
        return {
            "decisions_analyzed": len(self.ledger_entries),
            "decisions_that_change": sum(1 for r in results if r["changed"]),
            "original_distribution": self._get_distribution([r["original"] for r in results]),
            "simulated_distribution": self._get_distribution([r["simulated"] for r in results]),
            "routing_changes": metrics["routing_changes"],
            "metric_changes": metrics["metric_changes"],
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "risk_indicators": risk_indicators,
            "confidence": confidence,
            "recommendation": self._get_recommendation(metrics, conflicts, confidence),
        }
    
    def _evaluate_all_decisions(self) -> List[Dict[str, Any]]:
        """Evaluate each historical decision under both policies."""
        results = []
        
        for entry in self.ledger_entries:
            agent = entry.get("agent")
            action = entry.get("action")
            original_decision = entry.get("decision")
            
            # Compute original decision with current policy
            risk = classify_risk(action)
            current_result = check_policy(agent, action, policy=self.current_policy)
            original = gate_decision(current_result, risk)
            
            # Compute simulated decision with candidate policy
            candidate_result = check_policy(agent, action, policy=self.policy_candidate)
            simulated = gate_decision(candidate_result, risk)
            
            results.append({
                "agent": agent,
                "action": action,
                "risk": risk,
                "original": original,
                "simulated": simulated,
                "changed": original != simulated,
                "policy_result_before": current_result,
                "policy_result_after": candidate_result,
            })
        
        return results
    
    def _compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute routing changes and metrics."""
        routing_changes = defaultdict(int)
        original_counts = defaultdict(int)
        simulated_counts = defaultdict(int)
        
        for result in results:
            original = result["original"]
            simulated = result["simulated"]
            
            original_counts[original] += 1
            simulated_counts[simulated] += 1
            
            if original != simulated:
                key = f"{original.lower()}_to_{simulated.lower()}"
                routing_changes[key] += 1
        
        # Compute percentage changes
        total = len(results)
        original_halt_pct = 100 * original_counts.get("HALT", 0) / total if total > 0 else 0
        simulated_halt_pct = 100 * simulated_counts.get("HALT", 0) / total if total > 0 else 0
        halt_increase = simulated_halt_pct - original_halt_pct
        
        original_review_pct = 100 * original_counts.get("REVIEW", 0) / total if total > 0 else 0
        simulated_review_pct = 100 * simulated_counts.get("REVIEW", 0) / total if total > 0 else 0
        review_increase = simulated_review_pct - original_review_pct
        
        original_allow_pct = 100 * original_counts.get("ALLOW", 0) / total if total > 0 else 0
        simulated_allow_pct = 100 * simulated_counts.get("ALLOW", 0) / total if total > 0 else 0
        allow_change = simulated_allow_pct - original_allow_pct
        
        return {
            "routing_changes": dict(routing_changes),
            "metric_changes": {
                "halt_increase_pct": round(halt_increase, 1),
                "review_increase_pct": round(review_increase, 1),
                "allow_change_pct": round(allow_change, 1),
            },
        }
    
    def _identify_conflicts(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify policy conflicts and boundary issues."""
        conflicts = []
        
        for result in results:
            if result["changed"]:
                # Categorize the conflict
                conflict_type = self._categorize_conflict(result)
                conflicts.append({
                    "type": conflict_type,
                    "agent": result["agent"],
                    "action": result["action"],
                    "risk": result["risk"],
                    "original_decision": result["original"],
                    "simulated_decision": result["simulated"],
                    "original_policy_result": result["policy_result_before"],
                    "simulated_policy_result": result["policy_result_after"],
                })
        
        return conflicts
    
    def _categorize_conflict(self, result: Dict[str, Any]) -> str:
        """Categorize the type of conflict."""
        if result["policy_result_before"] != result["policy_result_after"]:
            # Policy evaluation changed
            if result["policy_result_after"] == "FORBIDDEN":
                return "permission_boundary_new_restriction"
            elif result["policy_result_before"] == "FORBIDDEN":
                return "permission_boundary_relaxed"
            else:
                return "permission_tier_shift"
        else:
            # Risk-based change
            return "risk_classification_impact"
    
    def _assess_risk(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risk implications of policy change."""
        critical_increases = sum(
            1 for r in results
            if r["original"] != "HALT" and r["simulated"] == "HALT" and r["risk"] == "CRITICAL"
        )
        
        critical_allows = sum(
            1 for r in results
            if r["original"] == "HALT" and r["simulated"] == "ALLOW" and r["risk"] == "CRITICAL"
        )
        
        high_now_allowed = sum(
            1 for r in results
            if r["original"] == "HALT" and r["simulated"] == "ALLOW" and r["risk"] == "HIGH"
        )
        
        return {
            "critical_now_blocked": critical_increases,
            "critical_now_allowed": critical_allows,
            "high_risk_now_allowed": high_now_allowed,
            "risk_profile_shift": "more_restrictive" if critical_increases > critical_allows else "more_permissive",
        }
    
    def _compute_confidence_score(self, results: List[Dict[str, Any]]) -> float:
        """Compute confidence in simulation (0-100).
        
        Based on: number of decisions analyzed and consistency.
        """
        if not results:
            return 0.0
        
        # Higher confidence with more decisions analyzed
        sample_size_confidence = min(100, len(results) / 10)  # 100+ decisions = full confidence
        
        # Lower confidence if many conflicts
        conflict_count = sum(1 for r in results if r["changed"])
        conflict_ratio = conflict_count / len(results)
        stability_confidence = max(0, 100 - (conflict_ratio * 50))  # 0% stability = 100 confidence loss
        
        # Average confidence factors
        return round((sample_size_confidence + stability_confidence) / 2, 1)
    
    def _get_distribution(self, decisions: List[str]) -> Dict[str, int]:
        """Get count distribution of decisions."""
        from collections import Counter
        counts = Counter(decisions)
        return {
            "ALLOW": counts.get("ALLOW", 0),
            "REVIEW": counts.get("REVIEW", 0),
            "HALT": counts.get("HALT", 0),
        }
    
    def _get_recommendation(self, metrics: Dict, conflicts: List, confidence: float) -> str:
        """Generate recommendation based on simulation results."""
        halt_increase = metrics["metric_changes"]["halt_increase_pct"]
        review_increase = metrics["metric_changes"]["review_increase_pct"]
        
        if confidence < 50:
            return "INSUFFICIENT_DATA: Analyze more historical decisions for confident assessment."
        
        if len(conflicts) > 50:
            return "HIGH_RISK: >50 conflicts detected. Recommend policy revision before deployment."
        
        if halt_increase > 15:
            return "WARNING: Policy would significantly increase halt rate ({}%). Review restrictions.".format(halt_increase)
        
        if halt_increase < -10:
            return "CAUTION: Policy would significantly relax restrictions ({}% fewer halts). Verify safety.".format(abs(halt_increase))
        
        if len(conflicts) > 20:
            return "REVIEW_RECOMMENDED: {} conflicts detected. Recommend manual review of edge cases.".format(len(conflicts))
        
        if review_increase > 20:
            return "OPERATIONAL_IMPACT: Review increase of {}% may impact throughput.".format(review_increase)
        
        return "READY_FOR_DEPLOYMENT: Policy change appears safe. Confidence: {}%.".format(int(confidence))
    
    def _empty_report(self) -> Dict[str, Any]:
        """Return empty report when no ledger data."""
        return {
            "decisions_analyzed": 0,
            "decisions_that_change": 0,
            "original_distribution": {"ALLOW": 0, "REVIEW": 0, "HALT": 0},
            "simulated_distribution": {"ALLOW": 0, "REVIEW": 0, "HALT": 0},
            "routing_changes": {},
            "metric_changes": {"halt_increase_pct": 0.0, "review_increase_pct": 0.0, "allow_change_pct": 0.0},
            "conflicts": [],
            "conflict_count": 0,
            "risk_indicators": {},
            "confidence": 0.0,
            "recommendation": "NO_DATA: No historical decisions in ledger.",
        }


def simulate_policy(policy_candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to run policy simulation.
    
    Args:
        policy_candidate: New policy version to test
    
    Returns:
        Simulation report with impact analysis
    """
    simulator = PolicySimulator(policy_candidate)
    return simulator.simulate()
