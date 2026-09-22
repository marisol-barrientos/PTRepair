"""
Splitting-Choice (skip-choice) where B is mandatory.
Skip is represented ONLY by a branch condition (no explicit skip activity).
"""

SRC_LABEL = "Receive Application"
DST_LABEL = "Issue Certificate"

DEFAULT_INITIAL_STATE = "certificate_initial and do_issue"
DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "certificate_initial and do_issue",
    "certificate_initial and skip_issue",
]

DEFAULT_CONTRADICTING_STATES = {
    "do_issue": "skip_issue",
    "skip_issue": "do_issue",
    "certificate_valid": "certificate_invalid",
    "certificate_invalid": "certificate_valid",
}

DEFAULT_CONTRADICTING_ACTIVITIES = {}

DEFAULT_ACTIVITIES = [
    "receive application",
    "issue certificate",
]

DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive application": "certificate_initial",
    # B only possible in the do_issue world
    "issue certificate": "certificate_initial and do_issue",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive application": "certificate_initial",
    "issue certificate": "certificate_valid",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "issue certificate": "certificate_initial",
}
