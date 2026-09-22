"""
Defaults for: XOR branch restructuring (duplicate-prevention case)

Process shape:
start review ->
XOR(
    reject application |
    manual evaluation |
    automatic evaluation
) ->
close case ->
(missing) archive decision
"""

SRC_LABEL = "start review"
DST_LABEL = "archive decision"


# -------------------------------
# 0) Initial states
# -------------------------------
DEFAULT_INITIAL_STATE = "case_open"

DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "case_open and evaluation_pending"
]


# -------------------------------
# 1) Contradicting data states
# -------------------------------
DEFAULT_CONTRADICTING_STATES = {

    "application_rejected": "application_accepted",
    "application_accepted": "application_rejected",

    "archive_ready": "archive_blocked",
    "archive_blocked": "archive_ready",

    "case_open": "case_closed",
    "case_closed": "case_open"
}


# -------------------------------
# 2) Contradicting activities
# -------------------------------
DEFAULT_CONTRADICTING_ACTIVITIES = {
    "archive decision": "reject application"
}


# -------------------------------
# 3) Activities in the domain
# -------------------------------
DEFAULT_ACTIVITIES = [
    "start review",
    "reject application",
    "manual evaluation",
    "automatic evaluation",
    "close case",
    "archive decision",
]


# -------------------------------
# 4) Preconditions
# -------------------------------
DEFAULT_ACTIVITY_PRECONDITIONS = {

    "start review": "case_open",

    "reject application": "evaluation_pending",
    "manual evaluation": "evaluation_pending",
    "automatic evaluation": "evaluation_pending",

    "close case": "evaluation_pending",

    # Archive only possible after evaluation
    "archive decision": "evaluation_complete and case_open"
}


# -------------------------------
# 5) Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {

    "start review": "evaluation_pending",

    "reject application": "application_rejected",

    "manual evaluation": "evaluation_complete",
    "automatic evaluation": "evaluation_complete",

    "close case": "case_closed",

    "archive decision": "archive_ready"
}


# -------------------------------
# 6) Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {

    "manual evaluation": "evaluation_pending",
    "automatic evaluation": "evaluation_pending",
    "archive decision": "case_open"
}