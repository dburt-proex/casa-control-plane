from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

from CASA.risk_engine import classify_risk
from CASA.gate_engine import gate_decision
from CASA.policy_loader import load_policy, check_policy
from CASA.ledger import log_event

from CASA.policy_simulator import PolicySimulator
from CASA.audit_ledger import read_ledger


app = FastAPI(
    title="CASA Governance API",
    description="Deterministic Governance Control Plane for Agentic Systems",
    version="1.0"
)


# ------------------------------------------------
# Request Models
# ------------------------------------------------

class GovernanceRequest(BaseModel):
    agent: str
    action: str
    signals: dict


class PolicyDryRunRequest(BaseModel):
    policy_candidate_path: str


# ------------------------------------------------
# Core Governance Evaluation Endpoint
# ------------------------------------------------

@app.post("/evaluate")
def evaluate_governance(request: GovernanceRequest):

    # load current policy and evaluate request
    policy = load_policy()

    # classify risk based on action (signals currently unused)
    risk = classify_risk(request.action)

    # determine policy result for this agent/action
    policy_result = check_policy(request.agent, request.action, policy=policy)

    # compute governance decision
    decision = gate_decision(policy_result, risk)

    # log to ledger for audit/training
    log_event(request.agent, request.action, risk, decision)

    return {
        "agent": request.agent,
        "action": request.action,
        "risk": risk,
        "decision": decision
    }


# ------------------------------------------------
# Policy Dry-Run Simulation Endpoint
# ------------------------------------------------

@app.post("/policy/dryrun")
def policy_dryrun(request: PolicyDryRunRequest):

    try:
        with open(request.policy_candidate_path) as f:
            candidate_policy = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Policy file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in policy file")

    try:
        ledger_entries = read_ledger()
    except FileNotFoundError:
        # No ledger yet, return empty results
        return {
            "decisions_analyzed": 0,
            "decisions_that_change": 0,
            "routing_changes": 0,
            "conflicts": [],
            "risk_indicators": [],
            "confidence": 0.0,
            "recommendation": "NO_DATA"
        }

    # Use PolicySimulator to analyze impact of candidate policy
    simulator = PolicySimulator(candidate_policy, ledger_entries)
    results = simulator.simulate()

    return results


# ------------------------------------------------
# Health Check Endpoint
# ------------------------------------------------

@app.get("/health")
def health_check():

    return {
        "status": "CASA Governance API running"
    }