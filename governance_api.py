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


class ReviewDecisionRequest(BaseModel):
    action: str
    reviewer: str = "operator"
    notes: str = ""


# ------------------------------------------------
# Core Governance Evaluation Endpoint
# ------------------------------------------------

@app.post("/evaluate")
def evaluate_governance(request: GovernanceRequest):

    policy = load_policy()
    risk = classify_risk(request.action, signals_context=request.signals)
    policy_result = check_policy(request.agent, request.action, policy=policy)
    decision = gate_decision(policy_result, risk)

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
        return {
            "decisions_analyzed": 0,
            "decisions_that_change": 0,
            "routing_changes": 0,
            "conflicts": [],
            "risk_indicators": [],
            "confidence": 0.0,
            "recommendation": "NO_DATA"
        }

    simulator = PolicySimulator(candidate_policy, ledger_entries)
    results = simulator.simulate()

    return results


# ------------------------------------------------
# Review Gate Endpoints
# ------------------------------------------------

@app.get("/decisions/flagged")
def list_flagged_decisions():
    try:
        ledger_entries = read_ledger()
    except FileNotFoundError:
        return []

    reviewed_ids = {
        entry.get("signals", {}).get("reviewed_decision_id")
        for entry in ledger_entries
        if entry.get("action") == "review_decision"
    }

    flagged = []
    for entry in ledger_entries:
        if entry.get("decision") == "REVIEW":
            decision_id = entry.get("decision_id")
            if decision_id and decision_id not in reviewed_ids:
                flagged.append({
                    "id": decision_id,
                    "decision_id": decision_id,
                    "timestamp": entry.get("time"),
                    "agent": entry.get("agent"),
                    "action": entry.get("action"),
                    "status": "REVIEW",
                    "risk": entry.get("risk"),
                    "policy_version": entry.get("policy_version"),
                    "signals": entry.get("signals", {}),
                    "reason": "Decision requires human review"
                })

    return flagged


@app.post("/decisions/{decision_id}/review")
def review_decision(decision_id: str, request: ReviewDecisionRequest):
    review_action = request.action.upper()
    if review_action not in {"APPROVE", "HALT"}:
        raise HTTPException(status_code=400, detail="Invalid action")

    try:
        ledger_entries = read_ledger()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")

    original = next((e for e in ledger_entries if e.get("decision_id") == decision_id), None)
    if not original:
        raise HTTPException(status_code=404, detail="Decision not found")

    if original.get("decision") != "REVIEW":
        raise HTTPException(status_code=409, detail="Only REVIEW decisions can be reviewed")

    already_reviewed = any(
        e.get("action") == "review_decision" and
        e.get("signals", {}).get("reviewed_decision_id") == decision_id
        for e in ledger_entries
    )
    if already_reviewed:
        raise HTTPException(status_code=409, detail="Already reviewed")

    final_decision = "ALLOW" if review_action == "APPROVE" else "HALT"

    policy = load_policy()
    log_event(
        request.reviewer,
        "review_decision",
        original.get("risk"),
        final_decision,
        signals={
            "reviewed_decision_id": decision_id,
            "review_action": review_action,
            "review_notes": request.notes,
        },
        policy_version=policy.get("version", "unknown")
    )

    return {
        "success": True,
        "decision_id": decision_id,
        "final_decision": final_decision
    }


# ------------------------------------------------
# Decision Replay Endpoints
# ------------------------------------------------

@app.get("/decision-replay/{decision_id}")
def replay_single_decision(decision_id: str):
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
    try:
        meter = BoundaryStressMeter()
        return meter.compute_stress()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")


@app.get("/dashboard")
def get_dashboard_json():
    try:
        dashboard = GovernanceDashboard()
        return dashboard.get_json_dashboard()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")


@app.get("/dashboard/text")
def get_dashboard_text():
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
    return {"status": "CASA Governance API running"}
