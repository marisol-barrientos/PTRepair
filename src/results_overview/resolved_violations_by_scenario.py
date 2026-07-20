# ============================================================
# ANALYSIS:
# RESOLVED VIOLATIONS BY SCENARIO
# ============================================================
#
# This script analyzes the resolution strategy summary
# and determines how many violated requirements were
# resolved for each scenario.
#
# A requirement is considered RESOLVED if at least one
# resolution strategy fixed the violation.
#
# Output:
# - CSV summary grouped by scenario
#
# ============================================================

import pandas as pd
from pathlib import Path

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
# INPUT FILE
# ============================================================

INPUT_XLSX = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "resolution_strategy_summary.xlsx"
)

print("\nReading:")
print(INPUT_XLSX)

# ============================================================
# OUTPUT FILE
# ============================================================

OUTPUT_CSV = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
    / "resolved_violations_by_scenario.csv"
)

# ============================================================
# LOAD EXCEL
# ============================================================

df = pd.read_excel(INPUT_XLSX)

print("\nLoaded rows:", len(df))

# ============================================================
# NORMALIZE STATUS COLUMN
# ============================================================

df["status"] = (
    df["status"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# ============================================================
# DETERMINE REQUIREMENT RESOLUTION
# ============================================================

requirement_resolution = []

grouped_requirements = df.groupby(
    ["scenario", "requirement_id"]
)

for (
    (scenario, requirement_id),
    group
) in grouped_requirements:

    resolved = (
        group["status"]
        == "FIXED"
    ).any()

    requirement_resolution.append({

        "scenario":
            scenario,

        "requirement_id":
            requirement_id,

        "resolved":
            resolved
    })

requirements_df = pd.DataFrame(
    requirement_resolution
)

# ============================================================
# GROUP BY SCENARIO
# ============================================================

scenario_summary = []

grouped_scenarios = requirements_df.groupby(
    "scenario"
)

for scenario, group in grouped_scenarios:

    total_requirements = len(group)

    resolved_requirements = (
        group["resolved"]
        == True
    ).sum()

    unresolved_requirements = (
        group["resolved"]
        == False
    ).sum()

    resolution_rate = round(
        (
            resolved_requirements
            / total_requirements
        ) * 100,
        2
    )

    scenario_summary.append({

        "scenario":
            scenario,

        "total_violated_requirements":
            total_requirements,

        "resolved_requirements":
            resolved_requirements,

        "unresolved_requirements":
            unresolved_requirements,

        "resolution_rate_percent":
            resolution_rate
    })

# ============================================================
# CREATE SUMMARY DATAFRAME
# ============================================================

summary_df = pd.DataFrame(
    scenario_summary
)

summary_df = summary_df.sort_values(
    by="scenario"
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
print("RESOLVED VIOLATIONS BY SCENARIO")
print("================================================")

print(summary_df)

print("\nSaved CSV:")
print(OUTPUT_CSV)