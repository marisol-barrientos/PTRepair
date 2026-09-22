"""
Lack-of-Activity test: insert missing activity BEFORE a PARALLEL block.

Intended behavior:
- After 'receive application' (SRC), the process must perform 'assign case' (DST).
- The PST starts a PARALLEL block immediately after SRC.
- The resolver should insert 'assign case' between SRC and the PARALLEL block.
"""

# Scenario configuration
SRC_LABEL = "Receive Application"
DST_LABEL = "Assign Case"

# -------------------------------
# 0) Initial state(s)
# -------------------------------
DEFAULT_INITIAL_STATE = "case_unassigned and certificate_initial and risk_initial"

DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "case_unassigned and certificate_initial and risk_initial",
]

# -------------------------------
# 1) Contradicting data states
# -------------------------------
DEFAULT_CONTRADICTING_STATES = {
    "case_assigned": "case_unassigned",
    "case_unassigned": "case_assigned",

    "risk_high": "risk_low",
    "risk_low": "risk_high",

    "rating_accepted": "rating_rejected",
    "rating_rejected": "rating_accepted",
}

# -------------------------------
# 2) Contradicting activities
# -------------------------------
DEFAULT_CONTRADICTING_ACTIVITIES = {}

# -------------------------------
# 3) Activities in the domain
# -------------------------------
DEFAULT_ACTIVITIES = [
    "receive application",
    "assign case",
    "check documents",
    "perform risk assessment",
    "approve request",
]

# -------------------------------
# 4) Preconditions
# -------------------------------
# Key point:
# - The parallel tasks require the case to be assigned.
#   So if the PST has PARALLEL immediately after SRC,
#   the planner *must* place 'assign case' before the PARALLEL block.
DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive application": "certificate_initial",

    "assign case": "case_unassigned",

    # Parallel work requires an assigned case
    "check documents": "case_assigned and risk_initial",
    "perform risk assessment": "case_assigned and risk_initial",

    # Approval after parallel (not required for this test goal)
    "approve request": "case_assigned",
}

# -------------------------------
# 5) Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive application": "certificate_initial",

    "assign case": "case_assigned",

    "check documents": "docs_checked",
    "perform risk assessment": "risk_assessed",

    "approve request": "rating_accepted",
}

# -------------------------------
# 6) Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "assign case": "case_unassigned",
}
