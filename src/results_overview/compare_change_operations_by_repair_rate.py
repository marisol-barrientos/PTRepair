# ============================================================
# ANALYSIS:
# CHANGE OPERATIONS THAT FIXED VIOLATIONS
# VS
# CHANGE OPERATIONS THAT DID NOT
# ============================================================
#
# This script combines:
#
# 1. Generated resolution strategies
# 2. Resolution strategy execution results
#
# and classifies:
#
# - Which change operations contributed to FIXED violations
# - Which change operations belonged to NOT_FIXED violations
#
# Output:
# - CSV with global operation statistics
#
# ============================================================

import json
import pandas as pd
from pathlib import Path
from collections import Counter

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
# INPUTS
# ============================================================

STRATEGY_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "generated_resolution_strategies"
)

SUMMARY_XLSX = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "resolution_strategy_summary.xlsx"
)

print("\nReading strategy results:")
print(SUMMARY_XLSX)

print("\nReading strategies from:")
print(STRATEGY_DIR)

# ============================================================
# OUTPUT FILE
# ============================================================

OUTPUT_CSV = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "change_operations_fix_effectiveness.csv"
)

# ============================================================
# LOAD SUMMARY EXCEL
# ============================================================

summary_df = pd.read_excel(
    SUMMARY_XLSX
)

summary_df["status"] = (
    summary_df["status"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# ============================================================
# COUNTERS
# ============================================================

fixed_counter = Counter()

not_fixed_counter = Counter()

total_counter = Counter()

# ============================================================
# ITERATE OVER RESULT ROWS
# ============================================================

for _, row in summary_df.iterrows():

    scenario = row["scenario"]

    pst_file = row["pst_file"]

    status = row["status"]

    # --------------------------------------------------------
    # EXTRACT STRATEGY ID
    # --------------------------------------------------------

    # Example:
    # 01_awad_delivery_of_goods_R1_RS1_copy_notification...
    #
    # -> RS1_copy_notification...

    split_name = pst_file.split("_")

    rs_index = None

    for i, token in enumerate(split_name):

        if token.startswith("RS"):

            rs_index = i
            break

    if rs_index is None:

        continue

    strategy_id = "_".join(
        split_name[rs_index:]
    )

    strategy_id = strategy_id.replace(
        "_violations.json",
        ""
    )

    # --------------------------------------------------------
    # FIND STRATEGY JSON FILES
    # --------------------------------------------------------

    strategy_folder = (
        STRATEGY_DIR
        / scenario
        / "resolution_strategies_clean"
    )

    if not strategy_folder.exists():

        continue

    json_files = list(
        strategy_folder.glob("*.json")
    )

    matched_strategy = None

    # --------------------------------------------------------
    # SEARCH STRATEGY
    # --------------------------------------------------------

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

        strategies = data.get(
            "resolution_strategies",
            []
        )

        for strategy in strategies:

            if (
                strategy.get(
                    "resolution_strategy_id"
                )
                == strategy_id
            ):

                matched_strategy = strategy
                break

        if matched_strategy:

            break

    # --------------------------------------------------------
    # NO MATCH FOUND
    # --------------------------------------------------------

    if matched_strategy is None:

        print(
            f"Strategy not found: "
            f"{strategy_id}"
        )

        continue

    # --------------------------------------------------------
    # COUNT OPERATIONS
    # --------------------------------------------------------

    change_operations = matched_strategy.get(
        "change_operations",
        []
    )

    for operation in change_operations:

        operation_name = operation.get(
            "operation"
        )

        if not operation_name:

            continue

        total_counter[
            operation_name
        ] += 1

        if status == "FIXED":

            fixed_counter[
                operation_name
            ] += 1

        else:

            not_fixed_counter[
                operation_name
            ] += 1

# ============================================================
# CREATE SUMMARY TABLE
# ============================================================

summary_rows = []

all_operations = sorted(
    total_counter.keys()
)

for operation in all_operations:

    total = total_counter[operation]

    fixed = fixed_counter[operation]

    not_fixed = not_fixed_counter[operation]

    fix_rate = round(
        (
            fixed / total
        ) * 100,
        2
    ) if total > 0 else 0

    summary_rows.append({

        "operation":
            operation,

        "total_usage":
            total,

        "fixed_usage":
            fixed,

        "not_fixed_usage":
            not_fixed,

        "fix_rate_percent":
            fix_rate
    })

# ============================================================
# CREATE DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    summary_rows
)

result_df = result_df.sort_values(
    by="fix_rate_percent",
    ascending=False
)

# ============================================================
# SAVE CSV
# ============================================================

result_df.to_csv(
    OUTPUT_CSV,
    index=False
)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n================================================")
print("CHANGE OPERATIONS FIX EFFECTIVENESS")
print("================================================")

print(result_df)

print("\nSaved CSV:")
print(OUTPUT_CSV)