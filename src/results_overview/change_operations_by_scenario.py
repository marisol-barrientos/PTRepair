# ============================================================
# ANALYSIS:
# CHANGE OPERATIONS BY SCENARIO
# ============================================================
#
# This script analyzes the generated resolution strategies
# and counts how many times each change operation was used
# per scenario.
#
# Example:
# - copy_after -> 4
# - insert_before -> 2
#
# Output:
# - CSV summary of change operation frequencies
#   grouped by scenario
#
# ============================================================

import json
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# DYNAMIC PROJECT ROOT DETECTION
# ============================================================

CURRENT_DIR = Path.cwd().resolve()

BASE_DIR = CURRENT_DIR

while BASE_DIR.name != (
    "PTResolver"
):
    BASE_DIR = BASE_DIR.parent

print("Project root:")
print(BASE_DIR)

# ============================================================
# INPUT DIRECTORY
# ============================================================

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "generated_resolution_strategies"
)

print("\nReading resolution strategies from:")
print(INPUT_DIR)

# ============================================================
# OUTPUT FILE
# ============================================================

OUTPUT_CSV = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "change_operations_by_scenario.csv"
)

# ============================================================
# INITIALIZATION
# ============================================================

scenario_operation_counter = defaultdict(
    Counter
)

# ============================================================
# ITERATE OVER SCENARIOS
# ============================================================

scenario_dirs = [

    d for d in INPUT_DIR.iterdir()

    if d.is_dir()
]

for scenario_dir in scenario_dirs:

    scenario_name = scenario_dir.name

    resolution_dir = (
        scenario_dir
        / "resolution_strategies_clean"
    )

    if not resolution_dir.exists():

        continue

    print("\nProcessing scenario:")
    print(scenario_name)

    json_files = list(
        resolution_dir.glob("*.json")
    )

    for json_file in json_files:

        try:

            with open(
                json_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception as e:

            print(
                f"Failed reading "
                f"{json_file.name}: {e}"
            )

            continue

        resolution_strategies = data.get(
            "resolution_strategies",
            []
        )

        for strategy in resolution_strategies:

            change_operations = strategy.get(
                "change_operations",
                []
            )

            for operation in change_operations:

                operation_name = operation.get(
                    "operation"
                )

                if operation_name:

                    scenario_operation_counter[
                        scenario_name
                    ][operation_name] += 1

# ============================================================
# CREATE SUMMARY ROWS
# ============================================================

summary_rows = []

for (
    scenario,
    counter
) in scenario_operation_counter.items():

    total_operations = sum(
        counter.values()
    )

    for (
        operation,
        count
    ) in counter.items():

        percentage = round(
            (
                count
                / total_operations
            ) * 100,
            2
        )

        summary_rows.append({

            "scenario":
                scenario,

            "operation":
                operation,

            "count":
                count,

            "percentage":
                percentage
        })

# ============================================================
# CREATE DATAFRAME
# ============================================================

summary_df = pd.DataFrame(
    summary_rows
)

summary_df = summary_df.sort_values(
    by=[
        "scenario",
        "count"
    ],
    ascending=[
        True,
        False
    ]
)

# ============================================================
# SAVE CSV
# ============================================================

summary_df.to_csv(
    OUTPUT_CSV,
    index=False
)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n================================================")
print("CHANGE OPERATIONS BY SCENARIO")
print("================================================")

print(summary_df)

print("\nSaved CSV:")
print(OUTPUT_CSV)