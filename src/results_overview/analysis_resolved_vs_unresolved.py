# ============================================================
# ANALYSIS OF RESOLVED AND UNRESOLVED VIOLATIONS
# ============================================================
#
# This script analyzes whether the generated resolution
# strategies successfully resolved the targeted compliance
# violations in the updated Process Structure Trees (PSTs).
#
# The script identifies:
# - resolved violations
# - unresolved violations
# - requirements never resolved
#
# Output:
# - resolution analysis summaries (.xlsx)
#
# ============================================================

# !pip install openpyxl
import json
import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================


# Project root directory
BASEDIR = Path(__file__).resolve().parent.parent
VIOLATIONS_DIR = (
    BASE_DIR
    / "data/output/compliance_violations_after_changes"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data/output/resolution_strategy_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# RESULTS
# ============================================================

summary_rows = []

# ============================================================
# ITERATE SCENARIOS
# ============================================================

scenario_dirs = sorted(
    VIOLATIONS_DIR.iterdir()
)

for scenario_dir in scenario_dirs:

    if not scenario_dir.is_dir():
        continue

    scenario_name = scenario_dir.name

    print("\n===================================")
    print("SCENARIO:", scenario_name)
    print("===================================\n")

    violation_files = sorted(
        scenario_dir.glob("*.json")
    )

    for violation_file in violation_files:

        print("Processing:", violation_file.name)

        # ----------------------------------------------------
        # Extract requirement id from filename
        # ----------------------------------------------------

        # Example:
        # 01_awad_delivery_of_goods_R1_RS1_xxx_violations.json

        stem = violation_file.stem

        parts = stem.split("_")

        requirement_id = None

        for part in parts:

            if part.startswith("R"):

                if (
                    len(part) > 1
                    and part[1:].isdigit()
                ):

                    requirement_id = part
                    break

        if requirement_id is None:

            print(
                "Could not determine "
                "requirement id."
            )

            continue

        # ----------------------------------------------------
        # Load violations
        # ----------------------------------------------------

        with open(
            violation_file,
            "r",
            encoding="utf-8"
        ) as f:

            violations = json.load(f)

        # ----------------------------------------------------
        # Determine if target requirement
        # still violated
        # ----------------------------------------------------

        still_violated = False

        matching_violation = None

        for violation in violations:

            if (
                violation["requirement_id"]
                == requirement_id
            ):

                still_violated = True

                matching_violation = violation

                break

        # ----------------------------------------------------
        # Determine status
        # ----------------------------------------------------

        if still_violated:

            status = "NOT_FIXED"

            evidence = (
                matching_violation.get(
                    "evidence",
                    []
                )
            )

        else:

            status = "FIXED"

            evidence = []

        # ----------------------------------------------------
        # Add row
        # ----------------------------------------------------

        summary_rows.append({

            "scenario":
                scenario_name,

            "pst_file":
                violation_file.name,

            "requirement_id":
                requirement_id,

            "status":
                status,

            "remaining_evidence":
                " | ".join(evidence)
        })

# ============================================================
# CREATE DATAFRAME
# ============================================================

df = pd.DataFrame(summary_rows)

# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    by=[
        "scenario",
        "requirement_id",
        "pst_file"
    ]
)

# ============================================================
# REQUIREMENTS NEVER FIXED
# ============================================================

grouped = df.groupby(
    ["scenario", "requirement_id"]
)

never_fixed_rows = []

for (
    scenario,
    requirement_id
), group in grouped:

    statuses = set(
        group["status"].tolist()
    )

    # --------------------------------------------------------
    # requirement fixed at least once
    # --------------------------------------------------------

    if "FIXED" in statuses:

        overall_status = (
            "FIXED_AT_LEAST_ONCE"
        )

    # --------------------------------------------------------
    # never fixed
    # --------------------------------------------------------

    else:

        overall_status = "NEVER_FIXED"

    never_fixed_rows.append({

        "scenario":
            scenario,

        "requirement_id":
            requirement_id,

        "overall_status":
            overall_status,

        "total_strategies":
            len(group),

        "fixed_strategies":
            len(
                group[
                    group["status"]
                    == "FIXED"
                ]
            ),

        "not_fixed_strategies":
            len(
                group[
                    group["status"]
                    == "NOT_FIXED"
                ]
            )
    })

# ============================================================
# CREATE OVERVIEW DATAFRAME
# ============================================================

overview_df = pd.DataFrame(
    never_fixed_rows
)

overview_df = overview_df.sort_values(
    by=[
        "scenario",
        "requirement_id"
    ]
)



# ============================================================
# SAVE EXCEL
# ============================================================

excel_output = (
    OUTPUT_DIR
    / "resolution_strategy_summary.xlsx"
)

with pd.ExcelWriter(
    excel_output,
    engine="openpyxl"
) as writer:

    # --------------------------------------------------------
    # detailed results
    # --------------------------------------------------------

    df.to_excel(
        writer,
        sheet_name="all_results",
        index=False
    )

    # --------------------------------------------------------
    # overview
    # --------------------------------------------------------

    overview_df.to_excel(
        writer,
        sheet_name="requirements_overview",
        index=False
    )

    # --------------------------------------------------------
    # only never fixed
    # --------------------------------------------------------

    overview_df[
        overview_df["overall_status"]
        == "NEVER_FIXED"
    ].to_excel(
        writer,
        sheet_name="never_fixed",
        index=False
    )

# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n===================================")
print("SUMMARY")
print("===================================\n")

print(df)

print("\n===================================")
print("REQUIREMENTS OVERVIEW")
print("===================================\n")

print(overview_df)


print("\nExcel saved to:")
print(excel_output)