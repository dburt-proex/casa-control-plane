"""
Governance Analytics Engine

Real-time metrics collection and analysis of governance decisions.
Transforms raw decisions into actionable intelligence about system safety.
"""

from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json


class GovernanceMetrics:
    """Collects and computes governance health metrics."""
    
    def __init__(self, ledger_entries: List[Dict[str, Any]]):
        """Initialize with ledger entries."""
        self.entries = ledger_entries
        self._compute_metrics()
    
    def _compute_metrics(self):
        """Compute all metrics from ledger."""
        if not self.entries:
            self._init_empty_metrics()
            return
        
        # Gate distribution
        decisions = [e.get("decision") for e in self.entries]
        self.gate_counts = Counter(decisions)
        self.total_decisions = len(decisions)
        
        # Risk distribution
        risks = [e.get("risk") for e in self.entries]
        self.risk_counts = Counter(risks)
        
        # Agent distribution
        agents = [e.get("agent") for e in self.entries]
        self.agent_counts = Counter(agents)
        
        # Action distribution
        actions = [e.get("action") for e in self.entries]
        self.action_counts = Counter(actions)
    
    def _init_empty_metrics(self):
        """Initialize empty metrics."""
        self.gate_counts = Counter()
        self.risk_counts = Counter()
        self.agent_counts = Counter()
        self.action_counts = Counter()
        self.total_decisions = 0
    
    def gate_distribution(self) -> Dict[str, float]:
        """Get percentage distribution of ALLOW/REVIEW/HALT.
        
        Returns:
            {
                "ALLOW": 78.5,
                "REVIEW": 18.2,
                "HALT": 3.3
            }
        """
        if self.total_decisions == 0:
            return {"ALLOW": 0.0, "REVIEW": 0.0, "HALT": 0.0}
        
        return {
            "ALLOW": round(100 * self.gate_counts.get("ALLOW", 0) / self.total_decisions, 1),
            "REVIEW": round(100 * self.gate_counts.get("REVIEW", 0) / self.total_decisions, 1),
            "HALT": round(100 * self.gate_counts.get("HALT", 0) / self.total_decisions, 1),
        }
    
    def halt_frequency(self) -> float:
        """Get percentage of halted decisions.
        
        Returns:
            4.2  (4.2% of decisions were halted)
        """
        if self.total_decisions == 0:
            return 0.0
        return round(100 * self.gate_counts.get("HALT", 0) / self.total_decisions, 1)
    
    def review_frequency(self) -> float:
        """Get percentage of review decisions."""
        if self.total_decisions == 0:
            return 0.0
        return round(100 * self.gate_counts.get("REVIEW", 0) / self.total_decisions, 1)
    
    def allow_frequency(self) -> float:
        """Get percentage of allowed decisions."""
        if self.total_decisions == 0:
            return 0.0
        return round(100 * self.gate_counts.get("ALLOW", 0) / self.total_decisions, 1)
    
    def risk_distribution(self) -> Dict[str, float]:
        """Get distribution of risk classifications.
        
        Returns:
            {
                "LOW": 45.0,
                "HIGH": 35.0,
                "CRITICAL": 20.0
            }
        """
        if self.total_decisions == 0:
            return {"LOW": 0.0, "HIGH": 0.0, "CRITICAL": 0.0}
        
        return {
            "LOW": round(100 * self.risk_counts.get("LOW", 0) / self.total_decisions, 1),
            "HIGH": round(100 * self.risk_counts.get("HIGH", 0) / self.total_decisions, 1),
            "CRITICAL": round(100 * self.risk_counts.get("CRITICAL", 0) / self.total_decisions, 1),
        }
    
    def critical_risk_events(self) -> int:
        """Count of CRITICAL risk decisions."""
        return self.risk_counts.get("CRITICAL", 0)
    
    def critical_halted(self) -> int:
        """Count of critical risk decisions that were halted."""
        count = 0
        for entry in self.entries:
            if entry.get("risk") == "CRITICAL" and entry.get("decision") == "HALT":
                count += 1
        return count
    
    def policy_violations(self) -> int:
        """Count of halted decisions (proxy for policy violations)."""
        return self.gate_counts.get("HALT", 0)
    
    def most_reviewed_actions(self, top_n: int = 5) -> List[tuple]:
        """Get actions requiring most reviews.
        
        Returns:
            [("write_database", 45), ("delete_database", 23), ...]
        """
        review_actions = defaultdict(int)
        for entry in self.entries:
            if entry.get("decision") == "REVIEW":
                review_actions[entry.get("action")] += 1
        
        return review_actions.items() if review_actions else []
    
    def most_violated_agents(self, top_n: int = 5) -> List[tuple]:
        """Get agents with most halted decisions.
        
        Returns:
            [("agent_01", 12), ("malicious_agent", 8), ...]
        """
        halted_agents = defaultdict(int)
        for entry in self.entries:
            if entry.get("decision") == "HALT":
                halted_agents[entry.get("agent")] += 1
        
        return halted_agents.items() if halted_agents else []
    
    def agent_score(self, agent: str) -> float:
        """Compute trust score for an agent (0-100).
        
        Based on: allow_rate / (allow_rate + halt_rate)
        Higher score = more trustworthy
        """
        agent_entries = [e for e in self.entries if e.get("agent") == agent]
        if not agent_entries:
            return 0.0
        
        allows = sum(1 for e in agent_entries if e.get("decision") == "ALLOW")
        halts = sum(1 for e in agent_entries if e.get("decision") == "HALT")
        
        if allows + halts == 0:
            return 0.0
        
        return round(100 * allows / (allows + halts), 1)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive governance health summary.
        
        Returns full dashboard data.
        """
        distribution = self.gate_distribution()
        risk_dist = self.risk_distribution()
        
        return {
            "total_decisions": self.total_decisions,
            "gate_distribution": {
                "ALLOW": int(distribution["ALLOW"]),
                "REVIEW": int(distribution["REVIEW"]),
                "HALT": int(distribution["HALT"]),
            },
            "halt_frequency": self.halt_frequency(),
            "review_frequency": self.review_frequency(),
            "allow_frequency": self.allow_frequency(),
            "risk_distribution": {
                "LOW": int(risk_dist["LOW"]),
                "HIGH": int(risk_dist["HIGH"]),
                "CRITICAL": int(risk_dist["CRITICAL"]),
            },
            "critical_events": self.critical_risk_events(),
            "critical_halted": self.critical_halted(),
            "policy_violations": self.policy_violations(),
            "top_reviewed_actions": dict(self.most_reviewed_actions()),
            "top_violating_agents": dict(self.most_violated_agents()),
        }
