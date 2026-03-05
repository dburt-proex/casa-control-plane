# CASA REGULATORY DEMO SCENARIO

## Executive Summary

This scenario demonstrates CASA as an enterprise governance platform for regulated AI systems. It shows:

1. **Real-time governance monitoring** - Live decision distribution and risk metrics
2. **Decision audit trails** - Complete reproducible history with replay capability
3. **Policy evolution without risk** - Safe testing via dry-run simulator
4. **Anomaly detection** - Identifying divergent agent behavior
5. **Stress measurement** - Early warning of boundary violations

---

## Setup: FinTech Autonomous Trading Platform

**Environment**: A financial institution running multiple autonomous trading agents

**Regulated by**: SEC, CFTC

**Compliance requirement**: "All trades executed by autonomous agents must be governed, audited, and explainable"

### Agents in the System

```
trading_agent_usa_equities      - NYSE stock trading (domestic)
trading_agent_global_fixed_income - Bond trading (international)
risk_management_system          - Real-time position management
compliance_monitor              - Trade compliance verification
settlement_processor            - Trade settlement automation
```

---

## Scenario Flow

### PHASE 1: Normal Operations (10:00 AM - 3:00 PM Market Hours)

**Regulatory Context**: "Execute normal trading with standard governance"

Starting state shows:
- **Decision Distribution**: ALLOW 85%, REVIEW 13%, HALT 2%
- **Risk Profile**: LOW 60%, MEDIUM 30%, HIGH 10%
- **Drift Index**: 0.15 (stable)
- **Boundary Stress**: STABLE (0.21)

#### Actions to Demonstrate:

```bash
# 1. Show real-time dashboard
curl http://localhost:8000/dashboard

# 2. Show text dashboard for CLI operations
curl http://localhost:8000/dashboard/text

# 3. Evaluate an example trade
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "trading_agent_usa_equities",
    "action": "place_equity_trade",
    "signals": {
      "order_size_usd": 500000,
      "sector": "technology",
      "market_condition": "normal"
    }
  }'

# Returns: {"decision": "ALLOW", "risk": "LOW"}
```

**Key Message**: "Everything operating normally. Governance is transparent and non-intrusive for routine operations."

---

### PHASE 2: Market Stress Test (3:00 PM - 4:15 PM)

**Scenario**: Volatility spike in fixed income markets

Policy pressure increases:
- More REVIEW decisions (24%)
- HALT decisions increase (6%)
- Drift trending upward (0.28)
- Stress score: 0.38 (CAUTION)

#### Actions to Demonstrate:

```bash
# 1. Show updated metrics
curl http://localhost:8000/dashboard

# 2. Check boundary stress specifically
curl http://localhost:8000/boundary-stress

# Shows: near_threshold_decisions_pct: 18.2%
#        tier2_boundary_hits: 17
#        drift_acceleration: +0.13
#        system_state: CAUTION
```

**Key Message**: "System stress is visible real-time. Operators get early warning before boundaries are crossed."

### Warnings Generated:

```
⚠ WARNINGS:
  • High near-threshold rate: 18.2% of decisions operating near policy boundary
  • Elevated tier2 boundary hits: 17 decisions escalated due to policy rules
  • Drift acceleration detected: +0.1300 indicates system instability
```

---

### PHASE 3: Policy Evolution Test (4:15 PM - 4:30 PM)

**Scenario**: Risk committee proposes tighter controls for volatile markets

**Question**: "Without implementing new policy, how would historical decisions change?"

#### Actions to Demonstrate:

```bash
# Create test policy file: new_policy_v1.1.json
# (Stricter: review_threshold drops from 70 to 65)

curl -X POST http://localhost:8000/policy/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "policy_candidate_path": "new_policy_v1.1.json"
  }'

# Returns complete impact analysis:
# {
#   "decisions_analyzed": 247,
#   "decisions_that_change": 23,
#   "percent_changed": 9.3%,
#   "routing_changes": {
#     "allow_to_review": 18,
#     "review_to_halt": 5,
#     ...
#   },
#   "confidence": 87.5,
#   "recommendation": "WARNING"
# }
```

**Key Message**: "Test policy changes against 100% of historical decisions before deployment - ZERO risk of unintended consequences."

---

### PHASE 4: Decision Audit & Replay (4:30 PM - 5:00 PM)

**Scenario**: Regulatory inspection asks "Show me how trading would have changed under v1.1"

#### Actions to Demonstrate:

```bash
# Full decision replay showing difference between policies
curl http://localhost:8000/decision-replay/all

# Returns complete audit trail:
# {
#   "total_replayed": 247,
#   "decisions_that_change": 23,
#   "policy_comparison": {
#     "original_policy_versions": ["v1.0"],
#     "replay_policy_version": "v1.0"
#   },
#   "routing_changes": {...},
#   "recommendations": "REVIEW_RECOMMENDED",
#   "decisions": [
#     {
#       "decision_id": "uuid",
#       "agent": "trading_agent_usa_equities",
#       "original": {...},
#       "replayed": {...},
#       "changed": true,
#       "risk_delta": 5.2,
#       "reason": "ALLOW → REVIEW: risk=72.5 (≥ review_threshold=70)"
#     },
#     ...
#   ]
# }
```

**Key Message**: "Complete audit trail with decision diffs - provable compliance with regulatory requirements."

---

### PHASE 5: Anomaly Detection & Root Cause (5:00 PM - 5:30 PM)

**Critical Event**: One agent shows anomalous behavior pattern

#### Actions to Demonstrate:

```bash
# Anomaly detected in agent behavior
curl http://localhost:8000/dashboard

# Risk panel shows:
# {
#   "anomalies": {
#     "high_risk_agents": ["trading_agent_global_fixed_income"],
#     "agent_anomaly_score": {
#       "trading_agent_global_fixed_income": 78.5
#     }
#   }
# }

# Drill into specific agent replay
curl http://localhost:8000/decision-replay/batch \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "agent_filter": "trading_agent_global_fixed_income",
    "limit": 50
  }'

# Shows: 40% of recent decisions diverged from normal pattern
# Risk increased from LOW/MEDIUM to HIGH/CRITICAL
# Confidence score dropped from 0.85 to 0.62
```

**Investigation Output**:

```
DECISION REPLAY - ANOMALY INVESTIGATION

Agent: trading_agent_global_fixed_income
Total Decisions: 32
Decisions Changed: 19 (59.4%)

Recent Pattern Shift:
  Previous behavior: LOW/MEDIUM risk, 95% ALLOW rate
  Current behavior:  HIGH risk, 40% REVIEW rate
  
Risk Acceleration: +25.3 over last 10 decisions
Confidence Degradation: 23%

Warnings:
  ⚠ Anomalous risk escalation detected
  ⚠ Confidence score degradation
  ⚠ Recommend manual review of agent configuration
```

**Key Message**: "Drift detection identifies problems before they become regulatory violations."

---

## Enterprise & Regulatory Value

### For Operations Teams
✅ **Real-time governance visibility** - Know system state at any moment  
✅ **Early warning signals** - Boundary stress alerts before violations  
✅ **Decision audit trail** - 100% traceable governance history  

### For Risk & Compliance
✅ **Safe policy evolution** - Test changes on 100% historical data  
✅ **Anomaly detection** - Identify divergent agent behavior  
✅ **Regulatory reporting** - Complete decision replay for audits  

### For Regulators
✅ **Provable governance** - Immutable cryptographic ledger  
✅ **Decision explainability** - Each decision backed by signals and policy  
✅ **Audit trail replay** - Show decisions under any policy version  

---

## Technical Architecture Proven

```
┌─────────────────────────────────────────────────────────┐
│  AI Agent     │ Execute trades autonomously             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CASA Control Plane                                     │
│  - Risk Classification (signals → risk score)           │
│  - Gate Engine (policy → decision)                      │
│  - Router (ALLOW/REVIEW/HALT → execution)              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Immutable Ledger (append-only, SHA-256 hash chain)     │
│  - Every decision recorded with signals                 │
│  - Policy version tracked                              │
│  - Cryptographic integrity verified                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Governance Analytics Layer                             │
│  - Drift Monitoring                                     │
│  - Boundary Stress Meter                                │
│  - Decision Replay Engine                               │
│  - Policy Simulator                                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Enterprise Dashboard (REST API + Text)                 │
│  - Real-time governance metrics                         │
│  - System state and alerts                              │
│  - Compliance reporting                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Running the Demo

### Option 1: Stable Operations (Baseline)
```bash
python demo_setup.py stable
python -m uvicorn governance_api:app --reload
# Navigate endpoints above
```

### Option 2: Comprehensive Demo (All Scenarios)
```bash
python demo_setup.py all
python -m uvicorn governance_api:app --reload
```

### Option 3: Specific Scenario
```bash
python demo_setup.py degrading    # System under stress
python demo_setup.py breach_attempt  # Anomaly detection
python demo_setup.py recovery     # System stabilization
```

---

## Key Differentiation vs. Existing Solutions

| Aspect | Existing Tools | CASA |
|--------|---|---|
| **Governance Type** | Prompt/Output Filtering | Execution Governance |
| **Auditability** | Lossy Logs | Cryptographic Ledger |
| **Policy Testing** | Risky (manual spot checks) | 100% Historical Replay |
| **Drift Detection** | Manual Inspection | Automated Metrics |
| **System Stress** | Reactive (after breach) | Proactive (boundary measurement) |
| **Decision Explainability** | String Logs | Structured Replay with Signals |

---

## Getting to Production

**What CASA Provides**:
- ✅ Governance control plane
- ✅ Immutable audit ledger  
- ✅ Drift detection & anomaly flagging
- ✅ Policy simulation & replay
- ✅ Boundary stress measurement
- ✅ Enterprise dashboard
- ✅ REST API for integration

**What You Provide**:
- Authentication/authorization
- Agent integration (route decisions via CASA)
- Signal extraction (domain-specific metrics)
- Policy configuration (governance rules)
- Incident response workflows

**Integration Effort**: ~2-4 weeks for production FinTech deployment

---

## Next Steps

1. **Evaluate Scenario**: Run demo_setup.py and explore endpoints
2. **Integrate with Your Agents**: Route decisions through /evaluate
3. **Configure Policies**: Define risk thresholds for your domain
4. **Test Dry-Run Simulator**: Validate policy changes before deployment
5. **Monitor Dashboard**: Set up operational monitoring
6. **Ready for Compliance**: Regulatory audit trail complete

---

**CASA: Governance Infrastructure for Autonomous AI Systems**
