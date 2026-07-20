# ============================================================
# ANALYSIS:
# CHANGE COSTS BY SCENARIO
# ============================================================
#
# This script calculates redesign/change costs
# per scenario based on the generated resolution
# strategies.
#
# The cost model reflects the structural and
# behavioral impact of each change operation.
#
# Costs are normalized by the number of
# resolved violations.
#
# Output:
# - CSV with normalized redesign costs
#   per scenario
#
# ============================================================

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

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
# INPUT DIRECTORIES
# ============================================================

STRATEGY_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "generated_resolution_strategies"
)

RESOLVED_VIOLATIONS_CSV = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "resolved_violations_by_scenario.csv"
)

print("\nReading resolution strategies from:")
print(STRATEGY_DIR)

print("\nReading resolved violations from:")
print(RESOLVED_VIOLATIONS_CSV)

# ============================================================
# OUTPUT FILE
# ============================================================

OUTPUT_CSV = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "change_costs_by_scenario.csv"
)

# ============================================================
# CHANGE COST MODEL
# ============================================================

CHANGE_COSTS = {

    # --------------------------------------------------------
    # LOW IMPACT
    # --------------------------------------------------------

    "rename": 1,
    "modify_resource": 1,
    "modify_write": 1,
    "add_write": 1,
    "remove_write": 1,
    "modify_read": 1,
    "modify_condition": 1,
    "modify_loop_condition": 1,
    "modify_timeout": 1,

    # --------------------------------------------------------
    # MODERATE IMPACT
    # --------------------------------------------------------

    "insert_after": 2,
    "insert_before": 2,
    "delete": 2,
    "move_after": 2,
    "move_before": 2,
    "copy_after": 2,
    "copy_before": 2,
    "swap": 2,
    "merge": 2,
    "split": 2,

    # --------------------------------------------------------
    # HIGH IMPACT
    # --------------------------------------------------------

    "parallelize": 3,
    "sequentialize_parallel": 3,
    "add_xor_branch": 3,
    "remove_branch": 3,
    "remove_branch_by_condition": 3,
    "embed_activity_in_xor": 3,
    "remove_loop": 3,

    # --------------------------------------------------------
    # VERY HIGH IMPACT
    # --------------------------------------------------------

    "embed_pre_loop": 4,
    "embed_post_loop": 4
}

# ============================================================
# LOAD RESOLVED VIOLATIONS
# ============================================================

resolved_df = pd.read_csv(
    RESOLVED_VIOLATIONS_CSV
)

resolved_lookup = {}

for _, row in resolved_df.iterrows():

    scenario = row["scenario"]

    resolved_lookup[scenario] = int(
        row["resolved_requirements"]
    )

# ============================================================
# INITIALIZATION
# ============================================================

scenario_statistics = defaultdict(
    lambda: {

        "total_cost": 0,

        "total_operations": 0,

        "total_strategies": 0,

        "strategy_costs": []
    }
)

# ============================================================
# ITERATE OVER SCENARIOS
# ============================================================

scenario_dirs = [

    d for d in STRATEGY_DIR.iterdir()

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

        # ----------------------------------------------------
        # PROCESS EACH STRATEGY
        # ----------------------------------------------------

        for strategy in resolution_strategies:

            strategy_cost = 0

            change_operations = strategy.get(
                "change_operations",
                []
            )

            for operation in change_operations:

                operation_name = operation.get(
                    "operation"
                )

                if not operation_name:

                    continue

                operation_cost = CHANGE_COSTS.get(
                    operation_name,
                    1
                )

                strategy_cost += operation_cost

                scenario_statistics[
                    scenario_name
                ]["total_cost"] += operation_cost

                scenario_statistics[
                    scenario_name
                ]["total_operations"] += 1

            scenario_statistics[
                scenario_name
            ]["total_strategies"] += 1

            scenario_statistics[
                scenario_name
            ]["strategy_costs"].append(
                strategy_cost
            )

# ============================================================
# CREATE SUMMARY TABLE
# ============================================================

summary_rows = []

for (
    scenario,
    stats
) in scenario_statistics.items():

    total_cost = stats["total_cost"]

    total_operations = stats[
        "total_operations"
    ]

    total_strategies = stats[
        "total_strategies"
    ]

    strategy_costs = stats[
        "strategy_costs"
    ]

    resolved_violations = resolved_lookup.get(
        scenario,
        0
    )

    avg_cost_per_strategy = round(
        (
            total_cost
            / total_strategies
        ),
        2
    ) if total_strategies > 0 else 0

    avg_cost_per_operation = round(
        (
            total_cost
            / total_operations
        ),
        2
    ) if total_operations > 0 else 0

    cost_per_resolved_violation = round(
        (
            total_cost
            / resolved_violations
        ),
        2
    ) if resolved_violations > 0 else 0

    max_strategy_cost = max(
        strategy_costs
    ) if strategy_costs else 0

    min_strategy_cost = min(
        strategy_costs
    ) if strategy_costs else 0

    summary_rows.append({

        "scenario":
            scenario,

        "resolved_violations":
            resolved_violations,

        "total_change_cost":
            total_cost,

        "cost_per_resolved_violation":
            cost_per_resolved_violation,

        "total_resolution_strategies":
            total_strategies,

        "total_operations":
            total_operations,

        "avg_cost_per_strategy":
            avg_cost_per_strategy,

        "avg_cost_per_operation":
            avg_cost_per_operation,

        "max_strategy_cost":
            max_strategy_cost,

        "min_strategy_cost":
            min_strategy_cost
    })

# ============================================================
# CREATE DATAFRAME
# ============================================================

summary_df = pd.DataFrame(
    summary_rows
)

summary_df = summary_df.sort_values(
    by="cost_per_resolved_violation",
    ascending=False
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
print("CHANGE COSTS BY SCENARIO")
print("================================================")

print(summary_df)

print("\nSaved CSV:")
print(OUTPUT_CSV)