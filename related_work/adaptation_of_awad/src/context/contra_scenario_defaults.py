"""
Contradicting-Repair Scenario:
The system inserts a missing activity ("assign case") before an XOR block
to satisfy preconditions of both branches. However, this repair introduces
a contradiction with a downstream activity ("approve request"), which
requires the opposite data state.
"""

# -------------------------------
# Scenario configuration
# -------------------------------
SRC_LABEL = "Receive Application"
DST_LABEL = "Assign Case"

# -------------------------------
# Initial state
# -------------------------------
DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "case_unassigned and certificate_initial and risk_low",
    "case_unassigned and certificate_initial and risk_high",
]

DEFAULT_INITIAL_STATE = "case_unassigned and certificate_initial"

# -------------------------------
# Contradicting data states
# -------------------------------
DEFAULT_CONTRADICTING_STATES = {
    "case_assigned": "case_unassigned",
    "case_unassigned": "case_assigned",

    "risk_high": "risk_low",
    "risk_low": "risk_high",
}

# -------------------------------
# Contradicting activities
# -------------------------------
DEFAULT_CONTRADICTING_ACTIVITIES = {}

# -------------------------------
# Activities
# -------------------------------
DEFAULT_ACTIVITIES = [
    "receive application",
    "assign case",                 # inserted repair activity
    "check documents",
    "perform risk assessment",
    "approve request",
]

# -------------------------------
# Preconditions
# -------------------------------
DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive application": "certificate_initial",

    # Repair activity
    "assign case": "case_unassigned",

    # XOR branch requires assigned case
    "check documents": "case_assigned and risk_low",
    "perform risk assessment": "case_assigned and risk_high",

    # 🔴 CONTRADICTION HERE
    # Final activity requires the opposite state
    "approve request": "case_unassigned",
}

# -------------------------------
# Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive application": "certificate_initial",

    # Repair introduces conflicting state
    "assign case": "case_assigned",

    "check documents": "docs_checked",
    "perform risk assessment": "risk_assessed",

    "approve request": "rating_accepted",
}

# -------------------------------
# Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    # Assigning removes the required state for approval
    "assign case": "case_unassigned",
}