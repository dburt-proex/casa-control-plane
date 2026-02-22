import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


LEDGER_PATH = Path("ledger.json")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _compute_hash(block: dict) -> str:
    block_copy = block.copy()
    block_copy.pop("hash", None)
    encoded = json.dumps(block_copy, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read_ledger():
    if not LEDGER_PATH.exists():
        return []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_ledger(ledger: list):
    with LEDGER_PATH.open("w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)


def _initialize_if_empty():
    ledger = _read_ledger()
    if not ledger:
        genesis = {
            "index": 0,
            "timestamp": _utc_now(),
            "intent": "GENESIS",
            "signals": {},
            "metadata": {},
            "previous_hash": "0",
            "hash": ""
        }
        genesis["hash"] = _compute_hash(genesis)
        _write_ledger([genesis])


def record_decision(intent: dict, signals: dict, metadata: dict):
    _initialize_if_empty()

    ledger = _read_ledger()
    previous_block = ledger[-1]

    # Backward compatibility for legacy ledger entries
    previous_index = previous_block.get("index", len(ledger) - 1)

    new_block = {
        "index": previous_index + 1,
        "timestamp": _utc_now(),
        "intent": intent,
        "signals": signals,
        "metadata": metadata,
        "previous_hash": previous_block["hash"],
        "hash": ""
    }

    new_block["hash"] = _compute_hash(new_block)
    ledger.append(new_block)
    _write_ledger(ledger)