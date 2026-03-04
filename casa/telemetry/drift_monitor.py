"""
Drift Monitor

Real-time monitoring of governance drift and anomaly detection.
Tracks deviations from expected governance patterns.
"""

from typing import Dict, List, Any
from collections import defaultdict
import statistics


class DriftMonitor:
    """Monitors governance drift in real-time."""
    
    def __init__(self, ledger_entries: List[Dict[str, Any]]):
        """Initialize with ledger entries."""
        self.entries = ledger_entries
    
    def halt_rate_by_agent(self) -> Dict[str, float]:
        """Get halt rate (%) for each agent.
        
        Returns:
            {
                "agent_01": 2.5,
                "malicious_agent": 45.0,
                ...
            }
        """
        agent_stats = defaultdict(lambda: {"total": 0, "halts": 0})
        
        for entry in self.entries:
            agent = entry.get("agent")
            if not agent:
                continue
            
            agent_stats[agent]["total"] += 1
            if entry.get("decision") == "HALT":
                agent_stats[agent]["halts"] += 1
        
        result = {}
        for agent, stats in agent_stats.items():
            if stats["total"] > 0:
                result[agent] = round(100 * stats["halts"] / stats["total"], 1)
        
        return result
    
    def drift_index(self) -> float:
        """Compute overall drift index (0-1 scale).
        
        Drift = deviation from expected behavior patterns
        0.0 = perfect stability
        1.0 = maximum divergence
        
        Returns:
            0.21  (21% drift)
        """
        if len(self.entries) < 2:
            return 0.0
        
        # Compute halt rates for each agent
        halt_rates = self.halt_rate_by_agent()
        
        if not halt_rates:
            return 0.0
        
        # Drift is deviation from mean halt rate
        try:
            mean_halt_rate = statistics.mean(halt_rates.values())
            variance = statistics.variance(halt_rates.values()) if len(halt_rates) > 1 else 0
            std_dev = statistics.stdev(halt_rates.values()) if len(halt_rates) > 1 else 0
            
            # Normalize to 0-1 scale
            drift = min(1.0, std_dev / 100.0)  # Max 100% deviation normalized to 1.0
            
            return round(drift, 2)
        except:
            return 0.0
    
    def anomaly_score(self, agent: str) -> float:
        """Compute anomaly score for an agent (0-100).
        
        Higher score = more anomalous behavior
        
        Returns:
            45.3  (agent is 45.3% anomalous)
        """
        agent_entries = [e for e in self.entries if e.get("agent") == agent]
        if not agent_entries:
            return 0.0
        
        halt_rate = self._agent_halt_rate(agent)
        
        # Anomaly based on deviation from expected (~5% halt rate)
        expected_halt_rate = 5.0
        deviation = abs(halt_rate - expected_halt_rate)
        
        # Cap at 100
        return min(100.0, round(deviation * 2, 1))
    
    def _agent_halt_rate(self, agent: str) -> float:
        """Get halt rate for a single agent."""
        agent_entries = [e for e in self.entries if e.get("agent") == agent]
        if not agent_entries:
            return 0.0
        
        halts = sum(1 for e in agent_entries if e.get("decision") == "HALT")
        return round(100 * halts / len(agent_entries), 1)
    
    def risky_agent_threshold_exceeded(self, threshold: float = 30.0) -> List[str]:
        """Get agents exceeding halt rate threshold.
        
        Args:
            threshold: halt rate percentage (default 30%)
        
        Returns:
            ["agent_01", "malicious_agent"]
        """
        halt_rates = self.halt_rate_by_agent()
        return [agent for agent, rate in halt_rates.items() if rate > threshold]
    
    def decision_pattern_stability(self) -> float:
        """Measure consistency of decision patterns (0-100).
        
        100 = perfectly stable
        0 = highly unstable
        
        Returns:
            87.5  (good stability)
        """
        if len(self.entries) < 10:
            return 100.0  # Too few samples to measure drift
        
        # Window-based stability: compare recent vs historical
        window_size = min(10, len(self.entries) // 2)
        
        recent = self.entries[-window_size:]
        historical = self.entries[:-window_size] if len(self.entries) > window_size else self.entries
        
        recent_allow_rate = sum(1 for e in recent if e.get("decision") == "ALLOW") / len(recent)
        historical_allow_rate = sum(1 for e in historical if e.get("decision") == "ALLOW") / len(historical) if historical else 0.5
        
        # Stability inversely proportional to rate change
        stability = max(0, 100 - (abs(recent_allow_rate - historical_allow_rate) * 200))
        
        return round(stability, 1)
    
    def get_drift_report(self) -> Dict[str, Any]:
        """Get comprehensive drift analysis."""
        return {
            "overall_drift_index": self.drift_index(),
            "decision_stability": self.decision_pattern_stability(),
            "halt_rates_by_agent": self.halt_rate_by_agent(),
            "anomalous_agents": self.risky_agent_threshold_exceeded(),
            "high_risk_indicators": {
                "high_drift_agents": [
                    {"agent": agent, "anomaly_score": self.anomaly_score(agent)}
                    for agent in self.risky_agent_threshold_exceeded()
                ]
            }
        }
