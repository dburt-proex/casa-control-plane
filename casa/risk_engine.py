from config import RISK_MATRIX


RISK_TO_SCORE = {
    "LOW": 25,
    "MEDIUM": 50,
    "HIGH": 75,
    "CRITICAL": 95,
}


def classify_risk(action, signals_context=None):
    """Classify risk based on action text and optional signal context."""
    action_text = str(action or "").lower()

    if any(term in action_text for term in [
        "delete customer records",
        "delete records",
        "delete_database",
        "expose private data",
        "private data",
        "credential",
        "secret",
    ]):
        base_risk = "CRITICAL"
    elif any(term in action_text for term in [
        "send customer-facing email",
        "customer-facing email",
        "send_email",
        "external email",
        "generated content",
        "write_database",
    ]):
        base_risk = "HIGH"
    elif any(term in action_text for term in [
        "summarize a public support ticket",
        "public support ticket",
        "read_database",
    ]):
        base_risk = "LOW"
    else:
        base_risk = RISK_MATRIX.get(action, "MEDIUM")

    if not signals_context:
        return base_risk

    risk_to_level = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    level_to_risk = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
    current_level = risk_to_level.get(base_risk, 2)

    if signals_context.get("sensitive"):
        current_level = min(current_level + 1, 4)
    if signals_context.get("external"):
        current_level = min(current_level + 1, 4)
    if signals_context.get("system_critical"):
        current_level = 4

    return level_to_risk.get(current_level, base_risk)


def risk_score(risk):
    """Convert CASA risk label to numeric score."""
    return RISK_TO_SCORE.get(str(risk).upper(), 50)
