"""
Defaults for: Lack-of-Activity insertion AFTER a PARALLEL block.

Process shape:
receive application ->
PARALLEL( check documents || perform risk assessment ) ->
approve request ->
(missing) issue certificate
"""

# Scenario configuration
SRC_LABEL = "Receive Application"
DST_LABEL = "Issue Certificate"

# -------------------------------
# 0) Initial state(s)
# -------------------------------
# Keep it simple: both initial flags are present.
DEFAULT_INITIAL_STATE = "certificate_initial and risk_initial"

DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "certificate_initial and risk_initial",
]

# -------------------------------
# 1) Contradicting data states
# -------------------------------
DEFAULT_CONTRADICTING_STATES = {
    "risk_high": "risk_low",
    "risk_low": "risk_high",

    "extra_evaluation_yes": "extra_evaluation_no",
    "extra_evaluation_no": "extra_evaluation_yes",

    "rating_accepted": "rating_rejected",
    "rating_rejected": "rating_accepted",

    "certificate_valid": "certificate_invalid",
    "certificate_invalid": "certificate_valid",
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
    "check documents",
    "perform risk assessment",
    "approve request",
    "issue certificate",
]

# -------------------------------
# 4) Preconditions
# -------------------------------
# For PARALLEL, do NOT gate these by risk_low/high (unlike XOR),
# because both branches are executed.
DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive application": "certificate_initial",

    # Both can run in parallel; require only risk_initial.
    "check documents": "risk_initial",
    "perform risk assessment": "risk_initial",

    # Approval should not be blocked by risk classification.
    "approve request": "certificate_initial",

    # Issuance requires approval.
    "issue certificate": "rating_accepted and certificate_initial",
}

# -------------------------------
# 5) Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive application": "certificate_initial",

    # These produce some flags but do not affect approval directly.
    "check documents": "extra_evaluation_no",
    "perform risk assessment": "extra_evaluation_yes",

    "approve request": "rating_accepted",
    "issue certificate": "certificate_valid",
}

# -------------------------------
# 6) Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "issue certificate": "certificate_initial",
}
