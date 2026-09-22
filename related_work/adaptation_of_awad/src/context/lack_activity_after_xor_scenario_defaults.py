# src/context/defaults.py

"""
Default domain configuration.

These defaults are designed to be consistent with a PST where:
- Risk is already classified (risk_low OR risk_high) before the XOR-choice is resolved.
- The XOR-choice uses conditions "risk_low" vs "risk_high".
- Approve Request happens after either branch.
"""

# Scenario configuration
SRC_LABEL = "Receive Application"
DST_LABEL = "Issue Certificate"

# -------------------------------
# 0) Default initial state(s)
# -------------------------------
# If your init-state generator supports multiple alternative initial states,
# use these instead of a single ["risk_initial", "certificate_initial"].
#
# Rationale:
#   Your XCHOICE conditions are "risk_low" and "risk_high".
#   So at the choice point, one of them must already hold.
DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "risk_low and certificate_initial",
    "risk_high and certificate_initial",
]

# If you still need a single init string, keep it simple:
# (Only used if your code ignores DEFAULT_INITIAL_STATE_ALTERNATIVES.)
DEFAULT_INITIAL_STATE = "certificate_initial"


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

    "evaluation_passed": "evaluation_failed",
    "evaluation_failed": "evaluation_passed",

    "certificate_valid": "certificate_invalid",
    "certificate_invalid": "certificate_valid",

    "payment_method_bank": "payment_method_credit",
    "payment_method_credit": "payment_method_bank",
}

# -------------------------------
# 2) Contradicting activities
# -------------------------------
DEFAULT_CONTRADICTING_ACTIVITIES = {
    # Example:
    # "issue certificate": "reject request",
}

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
# 4) Preconditions (less restrictive + aligned to your XOR conditions)
# -------------------------------
# Key changes vs your old defaults:
# - "approve request" no longer requires risk_low (so the planner doesn't
#   have to force risk assessment just to approve).
# - "check documents" is guarded by risk_low, and "perform risk assessment"
#   is guarded by risk_high, matching your XML XCHOICE.
#
# NOTE:
# These guards only work as intended if your initial state (or earlier actions)
# establish risk_low OR risk_high before the XCHOICE is evaluated.
DEFAULT_ACTIVITY_PRECONDITIONS = {
    # Receiving an application is possible as long as we're in the initial certificate state.
    "receive application": "certificate_initial",

    # Branch actions follow the XCHOICE guards.
    "check documents": "risk_low",
    "perform risk assessment": "risk_high",

    # Approval happens after either branch; keep it non-blocking by default.
    "approve request": "certificate_initial",

    # Certificate issuance still requires that approval happened.
    "issue certificate": "rating_accepted and certificate_initial",
}

# -------------------------------
# 5) Positive effects
# -------------------------------
# Key change:
# - "perform risk assessment" no longer flips risk_high->risk_low by default.
#   In your XML, it is executed *because* risk_high holds.
#   So by default we treat it as setting an "extra evaluation" flag,
#   not magically changing the risk class.
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive application": "certificate_initial",

    "check documents": "extra_evaluation_no",
    "perform risk assessment": "extra_evaluation_yes",

    "approve request": "rating_accepted",
    "issue certificate": "certificate_valid",
}

# -------------------------------
# 6) Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    # Issuing the certificate consumes the initial certificate state.
    "issue certificate": "certificate_initial",
}
