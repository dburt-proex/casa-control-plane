import datetime
import json
import hashlib
from typing import List, Dict, Any


LEDGER_FILE = "ledger.log"


def compute_hash(entry: Dict[str, Any], previous_hash: str = "0") -> str:
    """Compute SHA-256 hash of an entry with previous hash included."""
    entry_with_previous = {
        "previous_hash": previous_hash,
        **entry
    }
    entry_str = json.dumps(entry_with_previous, sort_keys=True)
    return hashlib.sha256(entry_str.encode()).hexdigest()


def record_decision(agent: str, action: str, risk: str, decision: str) -> Dict[str, Any]:
    """Record a governance decision with hash chain integrity.
    
    Returns the recorded entry with computed hash.
    """
    # Read current ledger to get previous hash
    entries = read_ledger()
    previous_hash = entries[-1]["hash"] if entries else "0"
    
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "agent": agent,
        "action": action,
        "risk": risk,
        "decision": decision
    }
    
    # Compute hash of this entry
    entry_hash = compute_hash(entry, previous_hash)
    
    # Add hash to entry
    entry_with_hash = {
        **entry,
        "hash": entry_hash,
        "previous_hash": previous_hash
    }
    
    # Append to ledger
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps(entry_with_hash) + "\n")
    
    return entry_with_hash


def read_ledger() -> List[Dict[str, Any]]:
    """Read and parse entire ledger file."""
    entries = []
    try:
        with open(LEDGER_FILE, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return entries


def verify_ledger_integrity() -> Dict[str, Any]:
    """Verify hash chain integrity of entire ledger.
    
    Returns:
        {
            "valid": bool,
            "total_entries": int,
            "broken_at_index": int or None,
            "errors": List[str]
        }
    """
    entries = read_ledger()
    errors = []
    
    if not entries:
        return {
            "valid": True,
            "total_entries": 0,
            "broken_at_index": None,
            "errors": []
        }
    
    # Verify first entry starts with previous_hash = "0"
    if entries[0].get("previous_hash") != "0":
        errors.append("First entry does not have previous_hash='0'")
    
    # Verify hash chain
    for i, entry in enumerate(entries):
        stored_hash = entry.get("hash")
        previous_hash = entry.get("previous_hash", "0")
        
        # Recompute hash without the hash field
        entry_copy = {k: v for k, v in entry.items() if k != "hash"}
        computed_hash = compute_hash(entry_copy, previous_hash)
        
        if stored_hash != computed_hash:
            errors.append(f"Entry {i}: hash mismatch (stored={stored_hash}, computed={computed_hash})")
            return {
                "valid": False,
                "total_entries": len(entries),
                "broken_at_index": i,
                "errors": errors
            }
        
        # Verify previous hash links to previous entry
        if i > 0:
            previous_entry_hash = entries[i-1].get("hash")
            if previous_hash != previous_entry_hash:
                errors.append(f"Entry {i}: previous_hash mismatch")
                return {
                    "valid": False,
                    "total_entries": len(entries),
                    "broken_at_index": i,
                    "errors": errors
                }
    
    return {
        "valid": True,
        "total_entries": len(entries),
        "broken_at_index": None,
        "errors": errors
    }


def get_decision_by_id(index: int) -> Dict[str, Any]:
    """Retrieve a decision entry by its index in the ledger."""
    entries = read_ledger()
    if 0 <= index < len(entries):
        return entries[index]
    raise IndexError(f"No entry at index {index}")
