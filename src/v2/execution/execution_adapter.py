import uuid
from datetime import datetime

def build_execution_plan(funding_plan, governance=None):
    """
    Transforme le funding_plan en execution_plan safe.
    Aucun ordre réel n'est généré ici.
    """

    plan_id = f"exec_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"

    actions = funding_plan.get("pool_actions", {}) if funding_plan else {}

    execution_actions = []
    blocked = False
    reasons = []

    # Gouvernance (soft)
    if governance:
        if governance.get("mode") == "SAFE":
            blocked = True
            reasons.append("governance SAFE mode")

        if governance.get("action_policy") == "simulated_only":
            reasons.append("simulated only mode")

    for pool, acts in actions.items():
        for a in acts:
            execution_actions.append({
                "pool": pool,
                "brick": a.get("brick"),
                "action": a.get("action"),
                "delta": a.get("approved_delta"),
                "status": "READY" if not blocked else "BLOCKED"
            })

    return {
        "status": "ok",
        "plan_id": plan_id,
        "blocked": blocked,
        "block_reasons": reasons,
        "execution_mode": "SIMULATED",
        "actions": execution_actions,
        "timestamp": datetime.utcnow().isoformat()
    }
