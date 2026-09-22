"""
Lack-of-Activity test: insert missing activity BEFORE an XOR block.
"""

# Scenario configuration
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
    "assign case",
    "check documents",
    "perform risk assessment",
    "approve request",
]

# -------------------------------
# Preconditions
# -------------------------------
DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive application": "certificate_initial",

    "assign case": "case_unassigned",

    "check documents": "case_assigned and risk_low",
    "perform risk assessment": "case_assigned and risk_high",

    "approve request": "case_assigned",
}

# -------------------------------
# Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive application": "certificate_initial",
    "assign case": "case_assigned",

    "check documents": "docs_checked",
    "perform risk assessment": "risk_assessed",

    "approve request": "rating_accepted",
}

# -------------------------------
# Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "assign case": "case_unassigned",
}
