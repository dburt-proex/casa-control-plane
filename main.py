
from CASA.evaluator import evaluate_action

if __name__ == "__main__":
    agent = "support_agent"
    action = "write_database"

    decision = evaluate_action(agent, action)

    print("CASA decision:", decision)
    