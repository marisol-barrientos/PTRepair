# ============================================================
# STEP 2:
# APPLY AND VALIDATE RESOLUTION STRATEGIES
# ============================================================
#
# This script applies the generated resolution strategies to
# the original process models and validates the resulting
# updated Process Structure Trees (PSTs).
#
# For each scenario and violated requirement, the script:
# - loads the original process model
# - loads the generated resolution strategies
# - applies each change operation sequentially
# - validates the updated process structure
# - stores the updated PSTs and execution logs
#
# The validation pipeline includes:
# - change operation validation
# - behavioral validation
# - PST validation
# - structural validation
#
# The script also generates:
# - a global CSV summary
# - validation statistics by scenario
#
# Output:
# - updated PST models (.xml)
# - validation and execution logs
# - validation summary CSV files
#
# ============================================================


# ============================================================
# STEP 2:
# APPLY AND VALIDATE RESOLUTION STRATEGIES
# ============================================================

import sys
import json
import time
import csv
from pathlib import Path
from collections import defaultdict

# ============================================================
# DYNAMIC PROJECT ROOT DETECTION
# ============================================================

CURRENT_DIR = Path.cwd().resolve()

BASE_PATH = CURRENT_DIR

while BASE_PATH.name != (
    "PTResolver"
):
    BASE_PATH = BASE_PATH.parent

print("Project root:")
print(BASE_PATH)

# ============================================================
# EXECUTION MODE
# ============================================================

RUN_ALL = True

SCENARIO_NAME = ""

REQUIREMENT_ID = ""

# ============================================================
# SCENARIO / REQUIREMENT CONFIGURATION
# ============================================================

SCENARIO_REQUIREMENTS = {

    "01_awad_delivery_of_goods":
      ["R1", "R2", "R3", "R4"],

    "02_de_masellis_loan_approval":
       ["R1", "R2", "R3"],

    "03_elgammal_loan_approval":
       ["R2", "R3"],

    "04_ghose_package_screening":
        ["R1"],

   "05_loebbecke_blood_collection":
        ["R6"],

    "06_BPMQ":
        ["R2", "R4", "R5", "R6"],

     "07_CRL":
        ["R1", "R3", "R4", "R6"],

     "08_DCR":
        ["R2"],

    "09_HaarmannetAL2021":
        ["R1"],

    "11_PCL":
        ["R1", "R3", "R4"],

    "12_PPSL":
        ["R2", "R3", "R4"],

    "13_Status":
        ["R1", "R2"],

    "14_SunetAl24":
        ["R2", "R3", "R4"],

    "15_WinteretAlER":
        ["R2", "R3"],

    "16_Zasadaetal23":
        ["R2", "R3", "R5"]
}


# ============================================================
# BUILD EXECUTION LIST
# ============================================================

EXECUTION_LIST = []

if RUN_ALL:

    for scenario, requirements in (
        SCENARIO_REQUIREMENTS.items()
    ):

        for req_id in requirements:

            EXECUTION_LIST.append(
                (scenario, req_id)
            )

else:

    EXECUTION_LIST.append(
        (
            SCENARIO_NAME,
            REQUIREMENT_ID
        )
    )

# ============================================================
# PYTHON PATHS
# ============================================================

SRC_DIR = (
    BASE_PATH
    / "src"
)

STEP2_DIR = (
    SRC_DIR
    / "step_2_apply_validate_resolution_strategies"
)

sys.path.append(str(SRC_DIR))
sys.path.append(str(STEP2_DIR))

# ============================================================
# IMPORTS
# ============================================================

from utils.process_io import load_process, save_process

from change_management.change_applier import (
    ChangeApplier
)

from validators.change_operation_validator import (
    ChangeOperationValidator
)

from validators.behavioral_validator import (
    BehavioralValidator
)

from validators.pst_validator import (
    PSTValidator
)

from validators.structural_validator import (
    StructuralValidator
)

from change_operations.operations import *

# ============================================================
# CHANGE OPERATION MAPPING
# ============================================================

operation_mapping = {
    "insert_after": insert_after,
    "insert_before": insert_before,
    "delete": delete,
    "rename": rename,
    "move_after": move_after,
    "move_before": move_before,
    "swap": swap,
    "merge": merge_by_label,
    "split": split,
    "copy_after": copy_after,
    "copy_before": copy_before,
    "modify_condition": modify_condition,
    "modify_resource": modify_resource,
    "modify_write": modify_write,
    "add_write": add_write,
    "remove_write": remove_write,
    "modify_read": modify_read,
    "parallelize": parallelize,
    "sequentialize_parallel": sequentialize_parallel,
    "add_xor_branch": add_xor_branch,
    "remove_branch": remove_branch,
    "remove_branch_by_condition":
        remove_branch_by_condition,
    "embed_activity_in_xor":
        embed_activity_in_xor,
    "embed_pre_loop": embed_pre_loop,
    "embed_post_loop": embed_post_loop,
    "remove_loop": remove_loop,
    "modify_loop_condition":
        modify_loop_condition,
    "modify_timeout": modify_timeout
}

# ============================================================
# VALIDATORS + APPLIER
# ============================================================

applier = ChangeApplier()

pattern_validator = ChangeOperationValidator()

behavioral_validator = BehavioralValidator()

pst_validator = PSTValidator()

structural_validator = StructuralValidator()

# ============================================================
# GLOBAL VALIDATION SUMMARY
# ============================================================

validation_summary = []

scenario_statistics = defaultdict(
    lambda: {
        "total_strategies": 0,
        "applied": 0,
        "warnings": 0,
        "errors": 0
    }
)

# ============================================================
# EXECUTION
# ============================================================

for (
    SCENARIO_NAME,
    REQUIREMENT_ID
) in EXECUTION_LIST:

    print("\n================================================")
    print("SCENARIO:", SCENARIO_NAME)
    print("REQUIREMENT:", REQUIREMENT_ID)
    print("================================================")

    ORIGINAL_MODEL_PATH = (
        BASE_PATH
        / "data/input/process_models/cpee_trees"
        / f"{SCENARIO_NAME}.xml"
    )

    RESOLUTION_STRATEGIES_FILE = (
        BASE_PATH
        / "data/ablation_study_step_1/final_prompt_4th_iteration/generated_resolution_strategies"
        / SCENARIO_NAME
        / "resolution_strategies_clean"
        / f"{SCENARIO_NAME}_RS_{REQUIREMENT_ID}.json"
    )

    if not RESOLUTION_STRATEGIES_FILE.exists():

        print(
            "Resolution strategy file missing:"
        )

        print(RESOLUTION_STRATEGIES_FILE)

        continue

    SCENARIO_OUTPUT_DIR = (
        BASE_PATH
        / "data/ablation_study_step_1/final_prompt_4th_iteration/updated_pst"
        / SCENARIO_NAME
    )

    PST_OUTPUT_DIR = (
        SCENARIO_OUTPUT_DIR
        / "pst"
    )

    LOG_OUTPUT_DIR = (
        SCENARIO_OUTPUT_DIR
        / "logs"
    )

    PST_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    LOG_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        RESOLUTION_STRATEGIES_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        resolution_data = json.load(f)

    resolution_strategies = (
        resolution_data[
            "resolution_strategies"
        ]
    )

    for strategy in resolution_strategies:

        strategy_id = strategy[
            "resolution_strategy_id"
        ]

        print("\n------------------------------------------------")
        print("Applying strategy:", strategy_id)
        print("------------------------------------------------")

        tree, root = load_process(
            str(ORIGINAL_MODEL_PATH)
        )

        current_root = root

        strategy_logs = []

        applied_operations = []

        strategy_start_time = time.time()

        strategy_applied = "YES"

        validation_status = "SUCCESS"

        warnings_detected = "NO"

        change_operation_validation = (
            "SUCCESS"
        )

        behavioral_validation = (
            "NOT_EXECUTED"
        )

        pst_validation = (
            "NOT_EXECUTED"
        )

        structural_validation = (
            "NOT_EXECUTED"
        )

        failure_message = ""

        for operation_data in strategy[
            "change_operations"
        ]:

            operation_name = operation_data[
                "operation"
            ]

            parameters = operation_data[
                "parameters"
            ]

            print(
                "\nOperation:",
                operation_name
            )

            print(
                "Parameters:",
                parameters
            )

            if (
                operation_name
                not in operation_mapping
            ):

                raise ValueError(
                    f"Unsupported operation: "
                    f"{operation_name}"
                )

            operation_function = (
                operation_mapping[
                    operation_name
                ]
            )

            pattern_validator.validate(
                operation_function
            )

            strategy_logs.append(
                f"ChangeOperationValidator: "
                f"SUCCESS ({operation_name})"
            )

            args = []

            # =================================================
            # ARGUMENT MAPPING
            # =================================================

            if operation_name in [
                "insert_after",
                "insert_before"
            ]:

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_activity_label"
                    ]
                ]

            elif operation_name == "delete":

                args = [
                    parameters[
                        "target_activity_label"
                    ]
                ]

            elif operation_name == "rename":

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_activity_label"
                    ]
                ]

            elif operation_name in [
                "move_after",
                "move_before"
            ]:

                args = [
                    parameters[
                        "source_activity_label"
                    ],
                    parameters[
                        "target_activity_label"
                    ]
                ]

            elif operation_name == "swap":

                args = [
                    parameters[
                        "first_activity_label"
                    ],
                    parameters[
                        "second_activity_label"
                    ]
                ]

            elif operation_name == "merge":

                args = [
                    parameters[
                        "first_activity_label"
                    ],
                    parameters[
                        "second_activity_label"
                    ]
                ]

            elif operation_name == "split":

                args = [
                    parameters[
                        "target_activity_label"
                    ]
                ]

            elif operation_name in [
                "copy_after",
                "copy_before"
            ]:

                args = [
                    parameters[
                        "source_activity_label"
                    ],
                    parameters[
                        "target_activity_label"
                    ]
                ]

            elif operation_name in [
                "parallelize",
                "sequentialize_parallel"
            ]:

                args = [
                    parameters[
                        "first_activity_label"
                    ],
                    parameters[
                        "second_activity_label"
                    ]
                ]

            elif operation_name == "remove_branch":

                args = [
                    parameters[
                        "target_activity_label"
                    ]
                ]

            elif operation_name == (
                "remove_branch_by_condition"
            ):

                args = [
                    parameters[
                        "target_condition"
                    ]
                ]

            elif operation_name == (
                "modify_condition"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_condition"
                    ]
                ]

            elif operation_name == (
                "modify_resource"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_resource"
                    ]
                ]

            elif operation_name == (
                "modify_write"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_statement"
                    ]
                ]

            elif operation_name == "add_write":

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "added_statement"
                    ]
                ]

            elif operation_name == (
                "remove_write"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "removed_variable_name"
                    ]
                ]

            elif operation_name == (
                "modify_read"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "old_variable_name"
                    ],
                    parameters[
                        "new_variable_name"
                    ]
                ]

            elif operation_name == "remove_loop":

                args = [
                    parameters[
                        "target_activity_label"
                    ]
                ]

            elif operation_name == (
                "modify_loop_condition"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_condition"
                    ]
                ]

            elif operation_name == (
                "modify_timeout"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "new_timeout"
                    ]
                ]

            elif operation_name == (
                "add_xor_branch"
            ):

                args = [
                    parameters[
                        "existing_branch_condition"
                    ],
                    parameters[
                        "new_branch_condition"
                    ],
                    parameters[
                        "new_activity_label"
                    ]
                ]

            elif operation_name == (
                "embed_activity_in_xor"
            ):

                args = [
                    parameters[
                        "target_activity_label"
                    ],
                    parameters[
                        "condition"
                    ],
                    parameters[
                        "mode"
                    ]
                ]

            elif operation_name in [
                "embed_pre_loop",
                "embed_post_loop"
            ]:

                args = [
                    parameters[
                        "start_activity_label"
                    ],
                    parameters[
                        "end_activity_label"
                    ],
                    parameters[
                        "condition"
                    ]
                ]

            else:

                raise ValueError(
                    f"Argument mapping missing "
                    f"for operation: "
                    f"{operation_name}"
                )

            # =================================================
            # APPLY CHANGE
            # =================================================

            try:

                current_root, log = (
                    applier.apply(
                        current_root,
                        operation_function,
                        *args
                    )
                )

                applied_operations.append(
                    f"{operation_name}"
                )

                strategy_logs.append(log)

            except Exception as e:

                print("FAILED TO APPLY CHANGE")

                print(str(e))

                strategy_applied = "NO"

                validation_status = "ERROR"

                failure_message = str(e)

                strategy_logs.append(
                    f"APPLICATION FAILED: {str(e)}"
                )

                break

            # =================================================
            # VALIDATION PHASE
            # =================================================

            try:

                behavioral_validator.validate(
                    current_root
                )

                behavioral_validation = (
                    "SUCCESS"
                )

                strategy_logs.append(
                    "BehavioralValidator: SUCCESS"
                )

            except Exception as e:

                behavioral_validation = (
                    "WARNING"
                )

                validation_status = (
                    "WARNING"
                )

                warnings_detected = "YES"

                strategy_logs.append(
                    f"BehavioralValidator WARNING: "
                    f"{str(e)}"
                )

            try:

                pst_validator.validate(
                    current_root
                )

                pst_validation = (
                    "SUCCESS"
                )

                strategy_logs.append(
                    "PSTValidator: SUCCESS"
                )

            except Exception as e:

                pst_validation = (
                    "WARNING"
                )

                validation_status = (
                    "WARNING"
                )

                warnings_detected = "YES"

                strategy_logs.append(
                    f"PSTValidator WARNING: "
                    f"{str(e)}"
                )

            try:

                structural_warnings = (
                    structural_validator.validate(
                        current_root
                    )
                )

                structural_validation = (
                    "SUCCESS"
                )

                strategy_logs.append(
                    "StructuralValidator: SUCCESS"
                )

                if structural_warnings:

                    warnings_detected = (
                        "YES"
                    )

                    validation_status = (
                        "WARNING"
                    )

                    for warning in (
                        structural_warnings
                    ):

                        strategy_logs.append(
                            f"Structural WARNING: "
                            f"{warning}"
                        )

            except Exception as e:

                structural_validation = (
                    "WARNING"
                )

                validation_status = (
                    "WARNING"
                )

                warnings_detected = "YES"

                strategy_logs.append(
                    f"StructuralValidator WARNING: "
                    f"{str(e)}"
                )

            print("SUCCESS")

        # =====================================================
        # EXECUTION TIME
        # =====================================================

        strategy_end_time = time.time()

        execution_time_ms = round(
            (
                strategy_end_time
                - strategy_start_time
            ) * 1000,
            2
        )

        strategy_logs.append(
            f"Execution time "
            f"(milliseconds): "
            f"{execution_time_ms}"
        )

        # =====================================================
        # SAVE VALIDATION SUMMARY
        # =====================================================

        validation_summary.append({

            "scenario":
                SCENARIO_NAME,

            "requirement_id":
                REQUIREMENT_ID,

            "strategy_id":
                strategy_id,

            "strategy_applied":
                strategy_applied,

            "validation_status":
                validation_status,

            "warnings_detected":
                warnings_detected,

            "change_operation_validator":
                change_operation_validation,

            "behavioral_validator":
                behavioral_validation,

            "pst_validator":
                pst_validation,

            "structural_validator":
                structural_validation,

            "applied_operations":
                " | ".join(
                    applied_operations
                ),

            "execution_time_ms":
                execution_time_ms,

            "failure_message":
                failure_message
        })

        # =====================================================
        # SCENARIO STATISTICS
        # =====================================================

        scenario_statistics[
            SCENARIO_NAME
        ]["total_strategies"] += 1

        if strategy_applied == "YES":

            scenario_statistics[
                SCENARIO_NAME
            ]["applied"] += 1

        if validation_status == "WARNING":

            scenario_statistics[
                SCENARIO_NAME
            ]["warnings"] += 1

        if validation_status == "ERROR":

            scenario_statistics[
                SCENARIO_NAME
            ]["errors"] += 1

        # =====================================================
        # SAVE UPDATED MODEL
        # =====================================================

        tree._setroot(current_root)

        output_model_path = (
            PST_OUTPUT_DIR
            / (
                f"{SCENARIO_NAME}_"
                f"{REQUIREMENT_ID}_"
                f"{strategy_id}.xml"
            )
        )

        save_process(
            tree,
            str(output_model_path)
        )

        print("\nSaved updated model:")

        print(output_model_path)

        # =====================================================
        # SAVE LOG
        # =====================================================

        log_path = (
            LOG_OUTPUT_DIR
            / (
                f"{SCENARIO_NAME}_"
                f"{REQUIREMENT_ID}_"
                f"{strategy_id}_log.txt"
            )
        )

        with open(
            log_path,
            "w",
            encoding="utf-8"
        ) as f:

            for log_entry in strategy_logs:

                f.write(str(log_entry))
                f.write("\n")

        print("Saved log:")

        print(log_path)

# ============================================================
# SAVE GLOBAL CSV SUMMARY
# ============================================================

summary_csv_path = (
    BASE_PATH
    / "data/output/updated_pst"
    / "validation_summary.csv"
)

with open(
    summary_csv_path,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:

    writer = csv.DictWriter(
        csvfile,
        fieldnames=[

            "scenario",
            "requirement_id",
            "strategy_id",

            "strategy_applied",
            "validation_status",
            "warnings_detected",

            "change_operation_validator",
            "behavioral_validator",
            "pst_validator",
            "structural_validator",

            "applied_operations",

            "execution_time_ms",

            "failure_message"
        ]
    )

    writer.writeheader()

    for row in validation_summary:

        writer.writerow(row)

print("\nSaved global validation summary:")

print(summary_csv_path)

# ============================================================
# SAVE SCENARIO STATISTICS CSV
# ============================================================

scenario_stats_csv = (
    BASE_PATH
    / "data/output/updated_pst"
    / "scenario_statistics.csv"
)

with open(
    scenario_stats_csv,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:

    writer = csv.DictWriter(
        csvfile,
        fieldnames=[

            "scenario",

            "total_strategies",

            "applied",

            "warnings",

            "errors",

            "application_rate"
        ]
    )

    writer.writeheader()

    for (
        scenario,
        stats
    ) in scenario_statistics.items():

        application_rate = round(
            (
                stats["applied"]
                / stats["total_strategies"]
            ) * 100,
            2
        )

        writer.writerow({

            "scenario":
                scenario,

            "total_strategies":
                stats["total_strategies"],

            "applied":
                stats["applied"],

            "warnings":
                stats["warnings"],

            "errors":
                stats["errors"],

            "application_rate":
                application_rate
        })

print("\nSaved scenario statistics:")

print(scenario_stats_csv)

print("\n================================================")
print("ALL STRATEGIES COMPLETED")
print("================================================")