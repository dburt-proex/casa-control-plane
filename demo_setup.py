#!/usr/bin/env python3
"""
CASA Demo Environment Setup

Initializes the CASA governance platform with realistic decision scenarios
for enterprise and regulatory demonstrations.

Usage:
    python demo_setup.py [scenario]

Scenarios:
    - stable: Normal governance operations
    - degrading: System showing signs of stress
    - breach_attempt: Anomalous agent behavior
    - recovery: System stabilizing after stress
"""

import sys
import argparse
from pathlib import Path
from CASA.ledger import log_event


def scenario_stable_operations():
    """Simulate stable governance operations - baseline scenario."""
    print("Setting up STABLE OPERATIONS scenario...")
    
    agents = ["analytics_001", "reporting_002", "ingestion_003", "cache_004"]
    actions = [
        ("read_database", "LOW", "ALLOW"),
        ("query_warehouse", "LOW", "ALLOW"),
        ("read_config", "LOW", "ALLOW"),
        ("read_logs", "LOW", "ALLOW"),
        ("write_cache", "MEDIUM", "ALLOW"),
        ("update_metrics", "MEDIUM", "ALLOW"),
        ("write_database", "HIGH", "REVIEW"),
        ("modify_policy", "CRITICAL", "HALT"),
    ]
    
    # Generate 150 stable decisions
    for i in range(150):
        agent = agents[i % len(agents)]
        action, risk, decision = actions[(i // 3) % len(actions)]
        
        log_event(
            agent=agent,
            action=action,
            risk=risk,
            decision=decision,
            signals={
                "external": False,
                "sensitive": risk in ["HIGH", "CRITICAL"],
                "policy_override": False,
            },
            policy_version="v1.0"
        )
    
    print("[OK] Generated 150 stable governance decisions")
    print("  - Mostly ALLOW (72%) for safe operations")
    print("  - Some REVIEW (24%) for data modifications")
    print("  - Rare HALT (4%) for critical actions")
    print("  - Drift: LOW")
    print("  - Boundary Stress: STABLE")


def scenario_degrading_system():
    """Simulate system under stress - increasing review/halt rates."""
    print("\nSetting up DEGRADING SYSTEM scenario...")
    
    agents = ["batch_process_001", "ml_training_002", "etl_pipeline_003"]
    
    # Phase 1: Normal operations (50 decisions)
    for i in range(50):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="read_training_data",
            risk="LOW",
            decision="ALLOW",
            signals={"external": False},
            policy_version="v1.0"
        )
    
    # Phase 2: Increasing resource requests (40 decisions)
    for i in range(40):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="write_intermediate_results",
            risk="MEDIUM",
            decision="REVIEW",  # Policy escalation
            signals={"external": False, "resource_intensive": True},
            policy_version="v1.0"
        )
    
    # Phase 3: Critical access patterns (30 decisions)
    for i in range(30):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="access_sensitive_features",
            risk="HIGH",
            decision="REVIEW",
            signals={"external": False, "sensitive": True},
            policy_version="v1.0"
        )
    
    # Phase 4: Approaching limits (20 decisions)
    for i in range(20):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="delete_intermediate_files",
            risk="HIGH",
            decision="HALT",
            signals={"sensitive": True, "system_critical": True},
            policy_version="v1.0"
        )
    
    print("[OK] Generated 140 degrading system decisions (4 phases)")
    print("  - Phase 1 (50): Stable operations")
    print("  - Phase 2 (40): Resource requests escalating")
    print("  - Phase 3 (30): Sensitive feature access")
    print("  - Phase 4 (20): Critical decisions with HALT")
    print("  - Drift: INCREASING")
    print("  - Boundary Stress: CAUTION→CRITICAL")


def scenario_breach_attempt():
    """Simulate anomalous agent behavior - breach attempt scenario."""
    print("\nSetting up BREACH ATTEMPT scenario...")
    
    normal_agents = ["audit_service", "reporting_service"]
    anomalous_agent = "compromised_agent"
    
    # Baseline: normal agents behaving correctly (80 decisions)
    for i in range(80):
        agent = normal_agents[i % len(normal_agents)]
        log_event(
            agent=agent,
            action="read_logs",
            risk="LOW",
            decision="ALLOW",
            signals={"external": False},
            policy_version="v1.0"
        )
    
    # Normal escalations from normal agents
    for i in range(20):
        agent = normal_agents[i % len(normal_agents)]
        log_event(
            agent=agent,
            action="generate_compliance_report",
            risk="MEDIUM",
            decision="REVIEW",
            signals={"external": False},
            policy_version="v1.0"
        )
    
    # ANOMALOUS: Compromised agent attempting escalation (30 decisions)
    for i in range(30):
        log_event(
            agent=anomalous_agent,
            action="request_elevated_access",
            risk="CRITICAL",
            decision="HALT",  # All blocked
            signals={
                "external": True,  # Unusual: external attempt
                "sensitive": True,
                "policy_override_requested": True,
            },
            policy_version="v1.0"
        )
    
    # After detection: normal agents increase monitoring (20 decisions)
    for i in range(20):
        agent = normal_agents[i % len(normal_agents)]
        log_event(
            agent=agent,
            action="audit_suspicious_activity",
            risk="MEDIUM",
            decision="HALT",  # Precautionary
            signals={"external": False, "incident_response": True},
            policy_version="v1.0"
        )
    
    print("[OK] Generated 150 breach attempt scenario decisions")
    print("  - 80 normal operations from legitimate agents")
    print("  - 20 normal escalations")
    print("  - 30 CRITICAL attempts from anomalous agent (ALL HALTED)")
    print("  - 20 incident response decisions")
    print("  - Anomaly Score: HIGH")
    print("  - System State: INCIDENT DETECTED")


def scenario_recovery():
    """Simulate system recovery from stress."""
    print("\nSetting up SYSTEM RECOVERY scenario...")
    
    agents = ["system_001", "system_002", "system_003"]
    
    # Phase 1: Peak stress (30 decisions)
    for i in range(30):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="under_load_operation",
            risk="HIGH",
            decision="HALT",
            signals={"external": False, "high_load": True},
            policy_version="v1.0"
        )
    
    # Phase 2: Stabilization kicks in (40 decisions)
    for i in range(40):
        agent = agents[i % len(agents)]
        decision = "REVIEW" if i % 2 == 0 else "ALLOW"
        log_event(
            agent=agent,
            action="recovering_operation",
            risk="MEDIUM",
            decision=decision,
            signals={"external": False, "recovery_mode": True},
            policy_version="v1.0"
        )
    
    # Phase 3: Return to normal (50 decisions)
    for i in range(50):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="normal_operation",
            risk="LOW",
            decision="ALLOW",
            signals={"external": False},
            policy_version="v1.0"
        )
    
    # Phase 4: Continued stabilization (30 decisions)
    for i in range(30):
        agent = agents[i % len(agents)]
        log_event(
            agent=agent,
            action="verified_operation",
            risk="LOW",
            decision="ALLOW",
            signals={"external": False},
            policy_version="v1.0"
        )
    
    print("[OK] Generated 150 system recovery decisions (4 phases)")
    print("  - Phase 1 (30): Peak stress - all HALT")
    print("  - Phase 2 (40): Stabilization - recovering to steady state")
    print("  - Phase 3 (50): Return to normal operations")
    print("  - Phase 4 (30): Sustained normal behavior")
    print("  - Drift: DECREASING")
    print("  - Boundary Stress: CRITICAL→STABLE")


def show_demo_info(scenario_name):
    """Show information about the selected scenario."""
    from CASA.telemetry.governance_dashboard import GovernanceDashboard
    
    print("\n" + "=" * 70)
    print("CASA DEMO SCENARIO LOADED".center(70))
    print("=" * 70)
    
    dashboard = GovernanceDashboard()
    print(dashboard.render_text_dashboard())
    
    print("\n[INFO] SCENARIO INFO:")
    print(f"  Scenario: {scenario_name}")
    print(f"  Total Decisions: {dashboard.metrics.total_decisions}")
    print(f"  ALLOW Rate: {dashboard.metrics.gate_distribution()['ALLOW']:.1f}%")
    print(f"  REVIEW Rate: {dashboard.metrics.gate_distribution()['REVIEW']:.1f}%")
    print(f"  HALT Rate: {dashboard.metrics.gate_distribution()['HALT']:.1f}%")
    
    stress = dashboard.stress_meter.compute_stress()
    print(f"  Stress Score: {stress['stress_score']:.3f}")
    print(f"  System State: {stress['system_state']}")
    
    print("\n[API] ENDPOINTS TO TEST:")
    print("  GET  /health - API health check")
    print("  POST /evaluate - Evaluate a governance request")
    print("  GET  /dashboard - Full governance dashboard (JSON)")
    print("  GET  /dashboard/text - Dashboard text (ASCII)")
    print("  GET  /boundary-stress - Boundary stress metrics")
    print("  GET  /decision-replay/all - Replay all decisions")
    print("  POST /policy/dryrun - Dry-run policy changes")
    
    print("\n[RUN] START API SERVER:")
    print("  python -m uvicorn governance_api:app --reload")
    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CASA Demo Environment Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios:
  stable            - Normal governance operations (BASELINE)
  degrading         - System under increasing stress
  breach_attempt    - Anomalous agent trying to escalate privileges
  recovery          - System recovering from stress
  all               - Run all scenarios in sequence
        """
    )
    
    parser.add_argument(
        "scenario",
        nargs="?",
        default="stable",
        choices=["stable", "degrading", "breach_attempt", "recovery", "all"],
        help="Demo scenario to load (default: stable)"
    )
    
    args = parser.parse_args()
    
    # Clean existing ledger if present
    ledger_path = Path("ledger.log")
    if ledger_path.exists():
        print("Clearing existing ledger...")
        ledger_path.unlink()
    
    if args.scenario == "all":
        scenario_stable_operations()
        scenario_degrading_system()
        scenario_breach_attempt()
        scenario_recovery()
        show_demo_info("ALL SCENARIOS")
    else:
        if args.scenario == "stable":
            scenario_stable_operations()
        elif args.scenario == "degrading":
            scenario_degrading_system()
        elif args.scenario == "breach_attempt":
            scenario_breach_attempt()
        elif args.scenario == "recovery":
            scenario_recovery()
        
        show_demo_info(args.scenario.upper())


if __name__ == "__main__":
    main()
