"""
Tests for performance-critical code paths.

Verifies that the optimizations introduced to fix slow/inefficient code
preserve correct behaviour:

  1. DecisionReplayEngine – O(1) dict index (no O(n²) linear scans in batch replay)
  2. policy_loader         – mtime-based cache (file is not re-read on every call)
  3. audit_ledger          – tail-read for previous hash (full ledger not loaded per write)
  4. GovernanceMetrics     – single-pass counters (critical_halted, most_reviewed_actions,
                            most_violated_agents use pre-computed values)
"""

import json
import os
import time

import pytest
from pathlib import Path

from CASA.audit_ledger import record_decision, read_ledger, LEDGER_FILE, _get_previous_hash
from CASA.decision_replay import DecisionReplayEngine
from CASA.ledger import log_event
from CASA.telemetry.governance_metrics import GovernanceMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_ledger(tmp_path, monkeypatch):
    """Redirect the ledger file to a temporary path for each test."""
    ledger = tmp_path / "ledger.log"
    monkeypatch.setattr("CASA.audit_ledger.LEDGER_FILE", str(ledger))

    # Also patch the ledger path used by log_event (casa/ledger.py hard-codes "ledger.log")
    import CASA.ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "log_event", _make_log_event(str(ledger)))

    yield str(ledger)


def _make_log_event(ledger_path: str):
    """Return a log_event variant that writes to ledger_path."""
    import datetime, uuid, json

    def _log_event(agent, action, risk, decision, signals=None, policy_version=None):
        entry = {
            "decision_id": str(uuid.uuid4()),
            "time": datetime.datetime.utcnow().isoformat(),
            "agent": agent,
            "action": action,
            "risk": risk,
            "decision": decision,
            "signals": signals or {},
            "policy_version": policy_version or "unknown",
        }
        with open(ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    return _log_event


# ---------------------------------------------------------------------------
# 1. DecisionReplayEngine – O(1) dict index
# ---------------------------------------------------------------------------

class TestDecisionReplayIndex:
    def _populate(self, log_fn, n: int = 20):
        for i in range(n):
            log_fn(
                agent=f"agent_{i % 3}",
                action="read_database",
                risk="LOW",
                decision="ALLOW",
                signals={"sensitive": False},
                policy_version="v1.0",
            )

    def test_index_built_on_init(self, clean_ledger, monkeypatch):
        """DecisionReplayEngine._ledger_index is a dict keyed by decision_id."""
        import CASA.ledger as ledger_mod
        # Redirect audit_ledger reads to our temp file
        import CASA.audit_ledger as al
        al_path = clean_ledger
        monkeypatch.setattr(al, "LEDGER_FILE", al_path)

        self._populate(ledger_mod.log_event, 10)

        # Also patch DecisionReplayEngine to read from the right file
        import CASA.decision_replay as dr
        monkeypatch.setattr(dr, "read_ledger", lambda: al.read_ledger())

        engine = DecisionReplayEngine()

        assert hasattr(engine, "_ledger_index"), "Engine must expose _ledger_index"
        assert isinstance(engine._ledger_index, dict)
        # Every ledger entry that has a decision_id must appear in the index
        assert len(engine._ledger_index) == len(engine.ledger)

    def test_index_enables_lookup_by_id(self, clean_ledger, monkeypatch):
        """decision_id keys in _ledger_index map to the correct entries."""
        import CASA.ledger as ledger_mod
        import CASA.audit_ledger as al
        import CASA.decision_replay as dr

        al_path = clean_ledger
        monkeypatch.setattr(al, "LEDGER_FILE", al_path)
        monkeypatch.setattr(dr, "read_ledger", lambda: al.read_ledger())

        self._populate(ledger_mod.log_event, 5)

        engine = DecisionReplayEngine()
        for entry in engine.ledger:
            did = entry["decision_id"]
            assert did in engine._ledger_index
            assert engine._ledger_index[did]["decision_id"] == did

    def test_replay_decision_uses_index(self, clean_ledger, monkeypatch):
        """replay_decision returns a result for a known decision_id."""
        import CASA.ledger as ledger_mod
        import CASA.audit_ledger as al
        import CASA.decision_replay as dr

        al_path = clean_ledger
        monkeypatch.setattr(al, "LEDGER_FILE", al_path)
        monkeypatch.setattr(dr, "read_ledger", lambda: al.read_ledger())

        ledger_mod.log_event(
            agent="agent_x",
            action="read_database",
            risk="LOW",
            decision="ALLOW",
            signals={"sensitive": False},
            policy_version="v1.0",
        )

        engine = DecisionReplayEngine()
        decision_id = engine.ledger[0]["decision_id"]
        result = engine.replay_decision(decision_id)

        assert result["decision_id"] == decision_id
        assert "original" in result
        assert "replayed" in result

    def test_replay_decision_raises_for_unknown_id(self, clean_ledger, monkeypatch):
        """replay_decision raises ValueError for an unknown decision_id."""
        import CASA.audit_ledger as al
        import CASA.decision_replay as dr

        al_path = clean_ledger
        monkeypatch.setattr(al, "LEDGER_FILE", al_path)
        monkeypatch.setattr(dr, "read_ledger", lambda: al.read_ledger())

        engine = DecisionReplayEngine()
        with pytest.raises(ValueError):
            engine.replay_decision("nonexistent-id-12345")


# ---------------------------------------------------------------------------
# 2. policy_loader – mtime-based cache
# ---------------------------------------------------------------------------

class TestPolicyCaching:
    def _reset_cache(self, monkeypatch):
        """Reset module-level cache state so each test starts clean."""
        import CASA.policy_loader as pl
        monkeypatch.setattr(pl, "_policy_cache", None)
        monkeypatch.setattr(pl, "_policy_mtime", None)

    def test_load_policy_returns_correct_content(self, tmp_path, monkeypatch):
        """load_policy returns the parsed policy file contents."""
        import CASA.policy_loader as pl

        policy_file = tmp_path / "policy.json"
        policy_file.write_text(json.dumps({"version": "v_cache_test", "agents": {}}))

        monkeypatch.setattr(pl, "POLICY_FILE", str(policy_file))
        self._reset_cache(monkeypatch)

        result = pl.load_policy()
        assert result["version"] == "v_cache_test"

    def test_cache_returns_same_object_without_file_change(self, tmp_path, monkeypatch):
        """Successive calls without file modification return the same cached object."""
        import CASA.policy_loader as pl

        policy_file = tmp_path / "policy.json"
        policy_file.write_text(json.dumps({"version": "v1", "agents": {}}))

        monkeypatch.setattr(pl, "POLICY_FILE", str(policy_file))
        self._reset_cache(monkeypatch)

        first = pl.load_policy()
        second = pl.load_policy()

        # Must be the exact same object (no second disk read)
        assert first is second

    def test_cache_invalidated_on_file_change(self, tmp_path, monkeypatch):
        """Cache is refreshed when the policy file's mtime changes."""
        import CASA.policy_loader as pl

        policy_file = tmp_path / "policy.json"
        policy_file.write_text(json.dumps({"version": "v1", "agents": {}}))

        monkeypatch.setattr(pl, "POLICY_FILE", str(policy_file))
        self._reset_cache(monkeypatch)

        first = pl.load_policy()
        assert first["version"] == "v1"

        # Wait briefly then overwrite the file so its mtime is genuinely newer.
        time.sleep(0.05)
        policy_file.write_text(json.dumps({"version": "v2", "agents": {}}))

        second = pl.load_policy()
        assert second["version"] == "v2"
        assert second is not first

    def test_missing_file_returns_empty_dict(self, tmp_path, monkeypatch):
        """load_policy returns {} gracefully when the policy file is missing."""
        import CASA.policy_loader as pl

        monkeypatch.setattr(pl, "POLICY_FILE", str(tmp_path / "nonexistent.json"))
        self._reset_cache(monkeypatch)

        result = pl.load_policy()
        assert result == {}


# ---------------------------------------------------------------------------
# 3. audit_ledger – _get_previous_hash (tail-read, no full-file parse)
# ---------------------------------------------------------------------------

class TestGetPreviousHash:
    def test_returns_zero_for_empty_ledger(self, tmp_path, monkeypatch):
        import CASA.audit_ledger as al
        ledger_path = str(tmp_path / "ledger.log")
        monkeypatch.setattr(al, "LEDGER_FILE", ledger_path)
        assert al._get_previous_hash() == "0"

    def test_returns_zero_for_missing_file(self, tmp_path, monkeypatch):
        import CASA.audit_ledger as al
        monkeypatch.setattr(al, "LEDGER_FILE", str(tmp_path / "no_file.log"))
        assert al._get_previous_hash() == "0"

    def test_returns_hash_of_last_entry(self, tmp_path, monkeypatch):
        import CASA.audit_ledger as al

        ledger_path = str(tmp_path / "ledger.log")
        monkeypatch.setattr(al, "LEDGER_FILE", ledger_path)

        al.record_decision("agent_a", "read_database", "LOW", "ALLOW")
        al.record_decision("agent_b", "write_database", "HIGH", "REVIEW")

        entries = al.read_ledger()
        expected_hash = entries[-1]["hash"]

        assert al._get_previous_hash() == expected_hash

    def test_hash_chain_intact_after_multiple_writes(self, tmp_path, monkeypatch):
        """Hash chain produced using _get_previous_hash must pass integrity check."""
        import CASA.audit_ledger as al

        ledger_path = str(tmp_path / "ledger.log")
        monkeypatch.setattr(al, "LEDGER_FILE", ledger_path)

        for i in range(10):
            al.record_decision(f"agent_{i}", "read_database", "LOW", "ALLOW")

        result = al.verify_ledger_integrity()
        assert result["valid"] is True
        assert result["total_entries"] == 10


# ---------------------------------------------------------------------------
# 4. GovernanceMetrics – single-pass counters
# ---------------------------------------------------------------------------

class TestGovernanceMetricsSinglePass:
    def _build_entries(self, halts=5, reviews=3, allows=10,
                       critical_halts=2, non_critical_halts=3):
        """Construct minimal ledger-like entries for testing."""
        entries = []
        # critical halts
        for _ in range(critical_halts):
            entries.append({"decision": "HALT", "risk": "CRITICAL",
                             "agent": "bad_agent", "action": "delete_database"})
        # non-critical halts
        for _ in range(non_critical_halts):
            entries.append({"decision": "HALT", "risk": "HIGH",
                             "agent": "risky_agent", "action": "write_database"})
        # reviews
        for _ in range(reviews):
            entries.append({"decision": "REVIEW", "risk": "MEDIUM",
                             "agent": "agent_1", "action": "write_database"})
        # allows
        for _ in range(allows):
            entries.append({"decision": "ALLOW", "risk": "LOW",
                             "agent": "agent_2", "action": "read_database"})
        return entries

    def test_critical_halted_count(self):
        entries = self._build_entries(critical_halts=3, non_critical_halts=2)
        metrics = GovernanceMetrics(entries)
        assert metrics.critical_halted() == 3

    def test_critical_halted_zero(self):
        entries = self._build_entries(critical_halts=0)
        metrics = GovernanceMetrics(entries)
        assert metrics.critical_halted() == 0

    def test_most_reviewed_actions_populated(self):
        entries = self._build_entries(reviews=4)
        metrics = GovernanceMetrics(entries)
        reviewed = dict(metrics.most_reviewed_actions())
        assert reviewed.get("write_database", 0) == 4

    def test_most_reviewed_actions_empty_when_no_reviews(self):
        entries = [{"decision": "ALLOW", "risk": "LOW",
                    "agent": "a", "action": "read_database"}]
        metrics = GovernanceMetrics(entries)
        assert list(metrics.most_reviewed_actions()) == []

    def test_most_violated_agents_populated(self):
        entries = self._build_entries(critical_halts=2, non_critical_halts=3)
        metrics = GovernanceMetrics(entries)
        halted = dict(metrics.most_violated_agents())
        # bad_agent has 2 CRITICAL HALTs, risky_agent has 3 non-critical HALTs
        assert halted.get("bad_agent", 0) == 2
        assert halted.get("risky_agent", 0) == 3

    def test_most_violated_agents_empty_when_no_halts(self):
        entries = [{"decision": "ALLOW", "risk": "LOW",
                    "agent": "a", "action": "read_database"}]
        metrics = GovernanceMetrics(entries)
        assert list(metrics.most_violated_agents()) == []

    def test_empty_metrics_initialises_derived_counters(self):
        metrics = GovernanceMetrics([])
        assert metrics.critical_halted() == 0
        assert list(metrics.most_reviewed_actions()) == []
        assert list(metrics.most_violated_agents()) == []
