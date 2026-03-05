from config import RISK_MATRIX


def classify_risk(action, signals_context=None):
    """Classify risk based on action and optional signal context.
    
    Args:
        action: Type of action being evaluated
        signals_context: Optional dict of signals for context-aware risk adjustment
    
    Returns:
        Risk level string: LOW, MEDIUM, HIGH, or CRITICAL
    """
    base_risk = RISK_MATRIX.get(action, "MEDIUM")
    
    # If no signal context, return base risk as-is
    if not signals_context:
        return base_risk
    
    # Convert to levels for adjustment
    risk_to_level = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    level_to_risk = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
    
    current_level = risk_to_level.get(base_risk, 2)
    
    # Adjust level based on signals
    if signals_context.get("sensitive"):
        current_level = min(current_level + 1, 4)
    
    if signals_context.get("external"):
        current_level = min(current_level + 1, 4)
    
    if signals_context.get("system_critical"):
        current_level = 4  # Force CRITICAL for system-critical changes
    
    return level_to_risk.get(current_level, base_risk)