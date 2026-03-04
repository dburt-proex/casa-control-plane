from CASA.evaluator import evaluate_action


def casa_guard(agent, action, tool_function):

    print("\n[CASA] Intercepting tool request")

    decision = evaluate_action(agent, action)

    if decision == "ALLOW":
        print("[CASA] Executing tool")
        return tool_function()

    elif decision == "REVIEW":
        print("[CASA] Manual review required")

    elif decision == "HALT":
        print("[CASA] Action blocked by CASA")