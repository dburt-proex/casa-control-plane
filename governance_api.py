from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

from CASA.risk_engine import classify_risk
from CASA.gate_engine import gate_decision
from CASA.policy_loader import load_policy, check_policy
from CASA.ledger import log_event

from CASA.policy_simulator import PolicySimulator
from CASA.audit_ledger import read_ledger
from CASA.decision_replay import DecisionReplayEngine


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

    # classify risk based on action and signals
    risk = classify_risk(request.action, signals_context=request.signals)

    # determine policy result for this agent/action
    policy_result = check_policy(request.agent, request.action, policy=policy)

    # compute governance decision
    decision = gate_decision(policy_result, risk)

    # log to ledger for audit/training - capture signals for replay
    log_event(
        request.agent,
        request.action,
        risk,
        decision,
        signals=request.signals,
        policy_version=policy.get("version", "unknown")
    )

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
# Decision Replay Endpoints
# ------------------------------------------------

@app.get("/decision-replay/{decision_id}")
def replay_single_decision(decision_id: str):
    """Replay a specific historical decision under current policy conditions.
    
    Enables regulatory audit trails: "how would this decision differ under current policy?"
    """
    try:
        engine = DecisionReplayEngine()
        result = engine.replay_decision(decision_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class DecisionReplayBatchRequest(BaseModel):
    agent_filter: str = None
    action_filter: str = None
    limit: int = 100


@app.post("/decision-replay/batch")
def replay_batch_decisions(request: DecisionReplayBatchRequest):
    """Replay multiple historical decisions with optional filters.
    
    Enables policy impact analysis: what percentage of decisions would change?
    """
    try:
        engine = DecisionReplayEngine()
        results = engine.replay_batch(
            agent_filter=request.agent_filter,
            action_filter=request.action_filter,
            limit=request.limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decision-replay/all")
def replay_all_decisions():
    """Replay all historical decisions under current policy.
    
    Produces comprehensive governance audit showing total impact of policy evolution.
    """
    try:
        engine = DecisionReplayEngine()
        results = engine.replay_all_decisions()
        return results
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")


# ------------------------------------------------
# Health Check Endpoint
# ------------------------------------------------

@app.get("/health")
def health_check():

    return {
        "status": "CASA Governance API running"
    }