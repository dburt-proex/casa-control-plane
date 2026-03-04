def gate_decision(policy_result, risk):

    # Hard policy block
    if policy_result == "FORBIDDEN":
        return "HALT"

    # Critical actions always blocked
    if risk == "CRITICAL":
        return "HALT"

    # High risk requires review
    if risk == "HIGH":
        return "REVIEW"

    # Policy review rule
    if policy_result == "REVIEW":
        return "REVIEW"

    return "ALLOW"