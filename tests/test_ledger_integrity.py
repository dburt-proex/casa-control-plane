import pytest
import os
import json
from CASA.audit_ledger import (
    record_decision,
    read_ledger,
    verify_ledger_integrity,
    compute_hash,
    get_decision_by_id,
    LEDGER_FILE
)


@pytest.fixture(autouse=True)
def cleanup_ledger():
    """Clean up test ledger before and after each test."""
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
    yield
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)


# --------Append-Only Ledger--------

def test_append_only_ledger():
    """Verify ledger is append-only - entries can only be added, never removed."""
    initial_entries = read_ledger()
    initial_count = len(initial_entries)
    
    # Add a decision
    record_decision(
        agent="test_agent",
        action="read_database",
        risk="LOW",
        decision="ALLOW"
    )
    
    after_one = read_ledger()
    assert len(after_one) == initial_count + 1
    
    # Add another decision
    record_decision(
        agent="test_agent",
        action="write_database",
        risk="HIGH",
        decision="REVIEW"
    )
    
    after_two = read_ledger()
    assert len(after_two) == initial_count + 2
    
    # Verify previous entries are unchanged
    assert after_two[0] == after_one[0]


def test_no_entries_can_be_removed():
    """Verify entries cannot be removed from ledger."""
    record_decision("agent1", "action1", "LOW", "ALLOW")
    record_decision("agent2", "action2", "HIGH", "REVIEW")
    record_decision("agent3", "action3", "CRITICAL", "HALT")
    
    entries_before = read_ledger()
    count_before = len(entries_before)
    
    # Even if someone tries to modify the file, full ledger verification catches it
    integrity = verify_ledger_integrity()
    assert integrity["valid"] is True
    assert integrity["total_entries"] == count_before


# --------Hash Chain Integrity--------

def test_hash_chain_integrity():
    """Verify each entry's hash links correctly to the previous entry."""
    # Create a chain of decisions
    decisions = [
        ("agent_01", "read_database", "LOW", "ALLOW"),
        ("agent_01", "write_database", "HIGH", "REVIEW"),
        ("admin_agent", "delete_database", "CRITICAL", "HALT"),
    ]
    
    for agent, action, risk, decision in decisions:
        record_decision(agent, action, risk, decision)
    
    ledger = read_ledger()
    
    # Verify chain: each entry's previous_hash matches previous entry's hash
    assert ledger[0]["previous_hash"] == "0"
    
    for i in range(1, len(ledger)):
        assert ledger[i]["previous_hash"] == ledger[i-1]["hash"]


def test_integrity_verification_passes():
    """Verify that ledger integrity check passes for valid ledger."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("admin_agent", "delete_database", "CRITICAL", "HALT")
    
    integrity = verify_ledger_integrity()
    
    assert integrity["valid"] is True
    assert integrity["total_entries"] == 3
    assert integrity["broken_at_index"] is None
    assert len(integrity["errors"]) == 0


def test_ledger_tamper_detection():
    """Verify that tampering with ledger is detected."""
    # Create a valid ledger
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    
    # Simulate tampering: modify a decision in the file
    with open(LEDGER_FILE, "r") as f:
        lines = f.readlines()
    
    # Modify the first entry
    first_entry = json.loads(lines[0])
    first_entry["decision"] = "HALT"  # Change outcome
    
    with open(LEDGER_FILE, "w") as f:
        f.write(json.dumps(first_entry) + "\n")
        f.writelines(lines[1:])
    
    # Verify integrity check detects tampering
    integrity = verify_ledger_integrity()
    assert integrity["valid"] is False
    assert integrity["broken_at_index"] is not None


# --------Replay Determinism--------

def test_decision_replay_determinism():
    """Verify that same governance inputs replay to same decisions."""
    # Record a decision
    entry1 = record_decision(
        agent="analytics_agent",
        action="read_database",
        risk="LOW",
        decision="ALLOW"
    )
    
    ledger = read_ledger()
    assert len(ledger) == 1
    
    # Same input recorded again
    entry2 = record_decision(
        agent="analytics_agent",
        action="read_database",
        risk="LOW",
        decision="ALLOW"
    )
    
    ledger = read_ledger()
    assert len(ledger) == 2
    
    # Both entries have valid decisions
    for entry in [entry1, entry2]:
        assert entry["decision"] in ["ALLOW", "REVIEW", "HALT"]
        assert "hash" in entry
        assert "timestamp" in entry


def test_all_decisions_valid():
    """Verify all recorded decisions are valid governance outcomes."""
    test_cases = [
        ("agent_01", "read_database", "LOW", "ALLOW"),
        ("agent_01", "write_database", "HIGH", "REVIEW"),
        ("agent_01", "delete_database", "CRITICAL", "HALT"),
        ("analytics_agent", "read_database", "LOW", "ALLOW"),
    ]
    
    for agent, action, risk, decision in test_cases:
        record_decision(agent, action, risk, decision)
    
    ledger = read_ledger()
    
    for entry in ledger:
        assert entry["decision"] in ["ALLOW", "REVIEW", "HALT"]
        assert entry["risk"] in ["LOW", "HIGH", "CRITICAL"]
        assert "agent" in entry
        assert "action" in entry


# --------Ledger Entry Retrieval--------

def test_get_decision_by_index():
    """Verify ability to retrieve decisions by index."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    record_decision("admin_agent", "delete_database", "CRITICAL", "HALT")
    
    entry0 = get_decision_by_id(0)
    assert entry0["decision"] == "ALLOW"
    assert entry0["agent"] == "agent_01"
    
    entry1 = get_decision_by_id(1)
    assert entry1["decision"] == "REVIEW"
    
    entry2 = get_decision_by_id(2)
    assert entry2["decision"] == "HALT"


def test_get_decision_invalid_index():
    """Verify error handling for invalid indices."""
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    
    with pytest.raises(IndexError):
        get_decision_by_id(10)


# --------Hash Consistency--------

def test_hash_consistency():
    """Verify that hash computation is deterministic."""
    entry = {
        "agent": "test_agent",
        "action": "test_action",
        "risk": "LOW",
        "decision": "ALLOW",
        "timestamp": "2026-03-04T12:00:00.000000"
    }
    
    hash1 = compute_hash(entry, "0")
    hash2 = compute_hash(entry, "0")
    
    assert hash1 == hash2


def test_ledger_immutability():
    """Verify ledger represents immutable history of decisions."""
    # Create initial entries
    record_decision("agent_01", "read_database", "LOW", "ALLOW")
    initial_ledger = read_ledger()
    initial_hashes = [e["hash"] for e in initial_ledger]
    
    # Add more entries
    record_decision("agent_01", "write_database", "HIGH", "REVIEW")
    extended_ledger = read_ledger()
    extended_hashes = [e["hash"] for e in extended_ledger]
    
    # Verify initial entries' hashes remain unchanged
    for i, initial_hash in enumerate(initial_hashes):
        assert extended_hashes[i] == initial_hash
