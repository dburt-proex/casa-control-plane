from casa.models import Signals
from casa.gate_engine import evaluate_gate


def test_halt_on_tier3():
    signals = Signals(0.1, 0.1, 0.1, 0.1, 0.1)
    intent = {"tier": 3}

    result = evaluate_gate(intent, signals)

    assert result.outcome == "HALT"