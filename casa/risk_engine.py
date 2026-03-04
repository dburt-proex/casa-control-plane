from config import RISK_MATRIX


def classify_risk(action):
    return RISK_MATRIX.get(action, "MEDIUM")