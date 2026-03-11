from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json

from config import ENVIRONMENT, LOG_LEVEL, POLICY_FILE, LEDGER_PATH

from CASA.risk_engine import classify_risk
from CASA.gate_engine import gate_decision
from CASA.policy_loader import load_policy, check_policy
from CASA.ledger import log_event

from CASA.policy_simulator import simulate_policy
from CASA.audit_ledger import read_ledger
from CASA.decision_replay import DecisionReplayEngine
from CASA.telemetry.governance_dashboard import GovernanceDashboard
from CASA.telemetry.boundary_stress_meter import BoundaryStressMeter


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

    # classify risk based on action
    risk = classify_risk(request.action)

    # determine policy result for this agent/action
    policy_result = check_policy(request.agent, request.action, policy=policy)

    # compute governance decision
    decision = gate_decision(policy_result, risk)

    # log to ledger for audit/training
    log_event(
        request.agent,
        request.action,
        risk,
        decision
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
            "decisions_changed": 0,
            "routing_changes": [],
            "status": "NO_DATA"
        }

    # Simulate policy against historical decisions
    results = simulate_policy(ledger_entries, candidate_policy)
    
    # Calculate aggregate metrics
    decisions_changed = sum(1 for r in results if r["original"] != r["simulated"])
    
    return {
        "decisions_analyzed": len(results),
        "decisions_changed": decisions_changed,
        "change_percentage": round(100 * decisions_changed / len(results), 2) if results else 0.0,
        "routing_changes": results,
        "status": "SUCCESS" if results else "NO_DECISIONS"
    }


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
# Boundary Stress & Dashboard Endpoints
# ------------------------------------------------

@app.get("/boundary-stress")
def get_boundary_stress():
    """Get boundary stress metrics measuring system stress on policy limits.
    
    Returns stress score (0-1) and system state (STABLE/CAUTION/CRITICAL) indicating:
    - Near-threshold decisions (decisions operating near review boundary)
    - Tier2 boundary hits (escalations due to policy rules)
    - Drift acceleration (sudden changes in behavior pattern)
    - Confidence degradation (decisions below minimum confidence threshold)
    """
    try:
        meter = BoundaryStressMeter()
        return meter.compute_stress()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")


@app.get("/dashboard")
def get_dashboard_json():
    """Get comprehensive governance dashboard in JSON format.
    
    Includes all observability panels:
    - Governance Health (decision distribution, metrics)
    - Boundary Stress (stress score, system state, warnings)
    - Drift Monitoring (drift index, stability, anomalies)
    - Risk Profile (risk classification distribution)
    - System State (overall health, ledger integrity, policy version)
    """
    try:
        dashboard = GovernanceDashboard()
        return dashboard.get_json_dashboard()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")


@app.get("/dashboard/text")
def get_dashboard_text():
    """Get governance dashboard as formatted ASCII text (for CLI/logs).
    
    Shows all monitoring panels in human-readable text format:
    - Governance Health
    - Boundary Stress
    - Drift Monitoring
    - Risk Classification
    - System State
    - Warnings & Alerts
    """
    try:
        dashboard = GovernanceDashboard()
        return {
            "dashboard": dashboard.render_text_dashboard(),
            "system_safe": dashboard.is_system_safe(),
            "requires_attention": dashboard.requires_attention(),
            "recommendation": dashboard.get_recommendation(),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")


# ------------------------------------------------
# Health Check Endpoint
# ------------------------------------------------

@app.get("/health")
def health_check():

    return {
        "status": "CASA Governance API running",
        "environment": ENVIRONMENT,
        "log_level": LOG_LEVEL,
        "policy_file": POLICY_FILE,
        "ledger_path": LEDGER_PATH
    }