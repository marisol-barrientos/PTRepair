# src/context/defaults.py

"""
Healthcare treatment process with missing diagnostic steps.

Key idea:
- A treatment decision is taken without ensuring diagnosis.
- Multiple alternative ways exist to reach diagnosis.
- The planner will suggest one, but others are equally valid.
"""

# Scenario configuration
SRC_LABEL = "Register Patient"
DST_LABEL = "Start Treatment"

# -------------------------------
# 0) Default initial state(s)
# -------------------------------
DEFAULT_INITIAL_STATE_ALTERNATIVES = [
    "patient_registered and patient_unexamined",
]

DEFAULT_INITIAL_STATE = "patient_registered"


# -------------------------------
# 1) Contradicting data states
# -------------------------------
DEFAULT_CONTRADICTING_STATES = {
    "diagnosis_ready": "diagnosis_missing",
    "diagnosis_missing": "diagnosis_ready",

    "lab_test_done": "lab_test_not_done",
    "lab_test_not_done": "lab_test_done",

    "clinical_exam_done": "clinical_exam_not_done",
    "clinical_exam_not_done": "clinical_exam_done",

    "treatment_started": "treatment_not_started",
    "treatment_not_started": "treatment_started",
}

# -------------------------------
# 2) Contradicting activities
# -------------------------------
DEFAULT_CONTRADICTING_ACTIVITIES = {
    # Example:
    # "start treatment": "discharge patient",
}

# -------------------------------
# 3) Activities in the domain
# -------------------------------
DEFAULT_ACTIVITIES = [
    "register patient",
    "perform lab test",
    "analyze lab test",
    "perform clinical examination",
    "start treatment",
]

# -------------------------------
# 4) Preconditions
# -------------------------------
DEFAULT_ACTIVITY_PRECONDITIONS = {
    "register patient": "patient_unexamined",

    # Lab-based diagnosis path
    "perform lab test": "patient_registered",
    "analyze lab test": "lab_test_done",

    # Alternative diagnosis path
    "perform clinical examination": "patient_registered",

    # Treatment requires diagnosis
    "start treatment": "diagnosis_ready",
}

# -------------------------------
# 5) Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "register patient": "patient_registered",

    # Lab path
    "perform lab test": "lab_test_done",
    "analyze lab test": "diagnosis_ready",

    # Clinical shortcut path
    "perform clinical examination": "diagnosis_ready",

    "start treatment": "treatment_started",
}

# -------------------------------
# 6) Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    # No destructive effects needed here
}