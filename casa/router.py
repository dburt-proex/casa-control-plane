def route(decision, action):

    if decision == "ALLOW":
        print(f"Executing: {action}")

    elif decision == "REVIEW":
        print(f"Human review required for: {action}")

    elif decision == "HALT":
        print(f"Execution blocked: {action}")