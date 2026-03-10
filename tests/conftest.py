"""
Shared test fixtures for CASA test suite.

Ensures ledger.log is cleaned before and after every test to prevent
cross-file contamination.
"""

import os
import pytest

LEDGER_FILE = "ledger.log"


@pytest.fixture(autouse=True)
def clean_ledger():
    """Remove ledger.log before and after each test."""
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
    yield
    if os.path.exists(LEDGER_FILE):
        os.remove(LEDGER_FILE)
