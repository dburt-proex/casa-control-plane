"""
Decision Diff Replay Engine

Replays historical decisions under new policy conditions to enable:
- Regulatory audit trails ("what would have happened with current policy?")
- Policy evolution testing
- Historical risk analysis
- Compliance reporting
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from CASA.audit_ledger import read_ledger
from CASA.policy_loader import load_policy, check_policy
from CASA.risk_engine import classify_risk
from CASA.gate_engine import gate_decision


def risk_to_numeric(risk_value: Any) -> float:
    """Convert risk level or value to numeric score."""
    if isinstance(risk_value, (int, float)):
        return float(risk_value)
    
    risk_mapping = {
        "LOW": 25.0,
        "MEDIUM": 50.0,
        "HIGH": 75.0,
        "CRITICAL": 95.0,
    }
    return risk_mapping.get(str(risk_value).upper(), 50.0)


class DecisionReplayEngine:
    """Replays historical decisions under current or alternative policy conditions."""
    
    def __init__(self):
        """Initialize replay engine."""
        self.ledger = read_ledger()
        # Build O(1) lookup index so replay_batch doesn't scan the entire
        # ledger for every entry (avoids O(n²) behaviour in replay_batch).
        self._ledger_index: dict = {
            entry["decision_id"]: entry
            for entry in self.ledger
            if "decision_id" in entry
        }
        self.current_policy = load_policy()
        self.current_policy_version = self.current_policy.get("version", "unknown")
    
    def replay_decision(self, decision_id: str, policy_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Replay a single historical decision under current policy.
        
        Args:
            decision_id: ID of decision to replay (from ledger)
            policy_override: Optional alternative policy to test against
        
        Returns:
            {
                "decision_id": str,
                "original": {
                    "policy_version": str,
                    "route": str,
                    "risk_score": float,
                    "timestamp": str,
                },
                "replayed": {
                    "policy_version": str,
                    "route": str,
                    "risk_score": float,
                    "confidence": float,
                    "timestamp": str,
                },
                "changed": bool,
                "risk_delta": float,
                "reason": str,
            }
        """
        # Find decision in ledger - O(1) using index
        decision_record = self._ledger_index.get(decision_id)
        
        if not decision_record:
            raise ValueError(f"Decision {decision_id} not found in ledger")
        
        # Get original outcome
        original_route = decision_record.get("decision")
        original_risk = decision_record.get("risk")
        original_risk_numeric = risk_to_numeric(original_risk)
        original_policy_version = decision_record.get("policy_version", "unknown")
        original_timestamp = decision_record.get("time")
        
        # Extract signals and re-evaluate
        agent = decision_record.get("agent")
        action = decision_record.get("action")
        signals = decision_record.get("signals", {})
        
        # Recompute risk under current conditions
        # Classifier behavior might differ if thresholds changed
        new_risk = classify_risk(action, signals_context=signals)
        new_risk_numeric = risk_to_numeric(new_risk)
        
        # Determine policy to use (current or override)
        policy_to_use = policy_override or self.current_policy
        policy_version_used = policy_to_use.get("version", self.current_policy_version)
        
        # Check policy - get policy result to feed into gate_decision
        policy_result = check_policy(agent, action, policy=policy_to_use)
        
        # Apply gating logic with recomputed risk
        new_route = gate_decision(policy_result, new_risk)
        
        # Determine if outcome changed
        changed = original_route != new_route
        risk_delta = new_risk_numeric - original_risk_numeric
        
        # Generate reasoning
        reason = self._generate_reason(
            original_route, new_route, original_risk, new_risk, changed
        )
        
        return {
            "decision_id": decision_id,
            "agent": agent,
            "action": action,
            "original": {
                "policy_version": original_policy_version,
                "route": original_route,
                "risk_score": original_risk,
                "timestamp": original_timestamp,
            },
            "replayed": {
                "policy_version": policy_version_used,
                "route": new_route,
                "risk_score": new_risk,
                "confidence": self._compute_confidence(signals),
                "timestamp": datetime.utcnow().isoformat(),
            },
            "changed": changed,
            "risk_delta": risk_delta,
            "reason": reason,
        }
    
    def replay_batch(
        self,
        agent_filter: Optional[str] = None,
        action_filter: Optional[str] = None,
        policy_override: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Replay multiple historical decisions.
        
        Args:
            agent_filter: Filter by agent name
            action_filter: Filter by action type
            policy_override: Optional alternative policy
            limit: Maximum decisions to replay
        
        Returns:
            {
                "total_replayed": int,
                "total_changed": int,
                "percent_changed": float,
                "routing_changes": {
                    "allow_to_review": int,
                    "allow_to_halt": int,
                    "review_to_allow": int,
                    "review_to_halt": int,
                    "halt_to_allow": int,
                    "halt_to_review": int,
                },
                "avg_risk_delta": float,
                "max_risk_delta": float,
                "decisions": [{...replay results...}, ...]
                "summary": {...}
            }
        """
        # Filter ledger by criteria
        filtered = self.ledger
        if agent_filter:
            filtered = [d for d in filtered if d.get("agent") == agent_filter]
        if action_filter:
            filtered = [d for d in filtered if d.get("action") == action_filter]
        
        # Limit and replay
        to_replay = filtered[:limit]
        replayed_decisions = []
        
        for entry in to_replay:
            decision_id = entry.get("decision_id")
            if decision_id:
                try:
                    result = self.replay_decision(decision_id, policy_override)
                    replayed_decisions.append(result)
                except ValueError:
                    # Skip decisions that can't be replayed
                    continue
        
        # Compute metrics
        total_replayed = len(replayed_decisions)
        total_changed = sum(1 for d in replayed_decisions if d["changed"])
        percent_changed = (total_changed / total_replayed * 100) if total_replayed > 0 else 0
        
        # Compute routing changes
        routing_changes = self._compute_routing_changes(replayed_decisions)
        
        # Compute risk deltas
        risk_deltas = [d["risk_delta"] for d in replayed_decisions]
        avg_risk_delta = sum(risk_deltas) / len(risk_deltas) if risk_deltas else 0
        max_risk_delta = max(risk_deltas) if risk_deltas else 0
        
        return {
            "total_decisions_in_ledger": len(self.ledger),
            "total_replayed": total_replayed,
            "total_changed": total_changed,
            "percent_changed": round(percent_changed, 2),
            "routing_changes": routing_changes,
            "risk_analysis": {
                "avg_risk_delta": round(avg_risk_delta, 2),
                "max_risk_delta": round(max_risk_delta, 2),
                "min_risk_delta": round(min(risk_deltas), 2) if risk_deltas else 0,
            },
            "policy_comparison": {
                "original_policy_versions": list(set(d["original"]["policy_version"] for d in replayed_decisions)),
                "replay_policy_version": replayed_decisions[0]["replayed"]["policy_version"] if replayed_decisions else None,
            },
            "decisions": replayed_decisions,
            "recommendation": self._get_batch_recommendation(total_changed, percent_changed, routing_changes)
        }
    
    def replay_all_decisions(self, policy_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Replay all decisions in ledger."""
        return self.replay_batch(limit=len(self.ledger), policy_override=policy_override)
    
    def _generate_reason(self, original_route: str, new_route: str, original_risk: Any, new_risk: Any, changed: bool) -> str:
        """Generate explanation for decision change."""
        if not changed:
            return "Decision outcome unchanged"
        
        original_numeric = risk_to_numeric(original_risk)
        new_numeric = risk_to_numeric(new_risk)
        
        risk_direction = "increased" if new_numeric > original_numeric else "decreased"
        risk_change = abs(new_numeric - original_numeric)
        
        route_change = f"{original_route} → {new_route}"
        risk_explanation = f"risk={new_risk} (was {original_risk}, {risk_direction} by {risk_change:.0f})"
        
        return f"{route_change}: {risk_explanation}"
    
    def _compute_confidence(self, signals: Dict[str, Any]) -> float:
        """Compute confidence in replay result based on signal quality."""
        if not signals:
            return 0.5  # Low confidence with no signals
        
        # Higher confidence with more complete signal data
        signal_count = len(signals)
        completeness = min(signal_count / 5.0, 1.0)  # Assume 5+ signals is complete
        return round(0.5 + (completeness * 0.5), 2)  # 0.5-1.0 range
    
    def _compute_routing_changes(self, replayed_decisions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count routing transitions."""
        changes = {
            "allow_to_review": 0,
            "allow_to_halt": 0,
            "review_to_allow": 0,
            "review_to_halt": 0,
            "halt_to_allow": 0,
            "halt_to_review": 0,
            "no_change": 0,
        }
        
        for decision in replayed_decisions:
            original = decision["original"]["route"]
            replayed = decision["replayed"]["route"]
            
            if original == replayed:
                changes["no_change"] += 1
            else:
                key = f"{original.lower()}_to_{replayed.lower()}"
                if key in changes:
                    changes[key] += 1
        
        return changes
    
    def _get_batch_recommendation(self, total_changed: int, percent_changed: float, routing_changes: Dict[str, int]) -> str:
        """Generate recommendation for batch replay results."""
        if percent_changed == 0:
            return "NO_CHANGES: Current policy aligns with historical decisions"
        elif percent_changed < 5:
            return "STABLE: Minimal historical impact from policy changes"
        elif percent_changed < 20:
            return "MODERATE_IMPACT: Some historical decisions would change"
        elif routing_changes.get("allow_to_halt", 0) > 0 or routing_changes.get("halt_to_allow", 0) > 0:
            return "HIGH_RISK: Critical routing path shifts detected"
        else:
            return "REVIEW_RECOMMENDED: Significant policy impact pattern detected"
