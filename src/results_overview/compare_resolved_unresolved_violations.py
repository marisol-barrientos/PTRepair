# ============================================================
# ANALYSIS OF RESOLVED / UNRESOLVED VIOLATIONS
# + RESOLUTION CONTEXT PRESERVATION
# + VIOLATION EVIDENCE
# ============================================================
#
# This script analyzes:
#
# 1. Whether originally violated requirements
#    are now compliant
#
# 2. Whether previously compliant requirements
#    (resolution context requirements)
#    remain compliant after applying the
#    resolution strategies
#
# 3. Why resolution context requirements
#    became violated
#
# Output:
# - detailed analysis
# - overview statistics
# - preservation analysis
# - Excel summary
#
# ============================================================

import json
import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parents[2]

VIOLATIONS_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "compliance_violations_after_changes"
)

RESOLUTION_CONTEXT_DIR = (
    BASE_DIR
    / "data"
    / "input"
    / "resolution_context"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "resolution_strategy_analysis"
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

    # --------------------------------------------------------
    # Load resolution context requirements
    # --------------------------------------------------------

    resolution_context_file = (
        RESOLUTION_CONTEXT_DIR
        / (
            f"{scenario_name}"
            f"_req_resolution_context.json"
        )
    )

    resolution_context_requirements = set()

    if resolution_context_file.exists():

        with open(
            resolution_context_file,
            "r",
            encoding="utf-8"
        ) as f:

            resolution_context = json.load(f)

        resolution_context_requirements = set(
            resolution_context.keys()
        )

        print(
            f"Loaded "
            f"{len(resolution_context_requirements)} "
            f"resolution context requirements."
        )

    else:

        print(
            "No resolution context "
            "requirements found."
        )

    # --------------------------------------------------------
    # Violation files
    # --------------------------------------------------------

    violation_files = sorted(
        scenario_dir.glob("*.json")
    )

    for violation_file in violation_files:

        print("Processing:", violation_file.name)

        # ----------------------------------------------------
        # Extract original violated requirement
        # ----------------------------------------------------

        stem = violation_file.stem

        parts = stem.split("_")

        original_requirement_id = None

        for part in parts:

            if (
                part.startswith("R")
                and len(part) > 1
                and part[1:].isdigit()
            ):

                original_requirement_id = part

                break

        if original_requirement_id is None:

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

            file_content = json.load(f)

        # ----------------------------------------------------
        # Handle new structure
        # ----------------------------------------------------

        if isinstance(file_content, dict):

            violations = file_content.get(
                "violation_report",
                []
            )

        else:

            violations = file_content

        # ----------------------------------------------------
        # Collect violated requirements
        # ----------------------------------------------------

        violated_requirements_after = set()

        for violation in violations:

            if (
                isinstance(violation, dict)
                and "requirement_id" in violation
            ):

                violated_requirements_after.add(
                    violation["requirement_id"]
                )

        # ----------------------------------------------------
        # 1. CHECK IF ORIGINAL VIOLATION FIXED
        # ----------------------------------------------------

        original_fixed = (
            original_requirement_id
            not in violated_requirements_after
        )

        # ----------------------------------------------------
        # 2. CHECK RESOLUTION CONTEXT VIOLATIONS
        # ----------------------------------------------------

        violated_resolution_context = []

        resolution_context_evidence = []

        for violation in violations:

            if not isinstance(violation, dict):
                continue

            violated_req = violation.get(
                "requirement_id"
            )

            if (
                violated_req
                in resolution_context_requirements
            ):

                violated_resolution_context.append(
                    violated_req
                )

                evidence = violation.get(
                    "evidence",
                    []
                )

                if isinstance(evidence, list):

                    evidence_text = " | ".join(
                        str(e)
                        for e in evidence
                    )

                else:

                    evidence_text = str(evidence)

                resolution_context_evidence.append(
                    f"{violated_req}: {evidence_text}"
                )

        violated_resolution_context = sorted(
            set(violated_resolution_context)
        )

        resolution_context_preserved = (
            len(
                violated_resolution_context
            ) == 0
        )

        # ----------------------------------------------------
        # Build status labels
        # ----------------------------------------------------

        if original_fixed:

            original_status = "FIXED"

        else:

            original_status = "NOT_FIXED"

        if resolution_context_preserved:

            context_status = "PRESERVED"

        else:

            context_status = "BROKEN"

        # ----------------------------------------------------
        # Evidence for original violation
        # ----------------------------------------------------

        original_violation_evidence = []

        for violation in violations:

            if not isinstance(violation, dict):
                continue

            if (
                violation.get("requirement_id")
                == original_requirement_id
            ):

                evidence = violation.get(
                    "evidence",
                    []
                )

                if isinstance(evidence, list):

                    original_violation_evidence.extend(
                        evidence
                    )

                else:

                    original_violation_evidence.append(
                        str(evidence)
                    )

        # ----------------------------------------------------
        # Add row
        # ----------------------------------------------------

        summary_rows.append({

            "scenario":
                scenario_name,

            "pst_file":
                violation_file.name,

            "original_requirement":
                original_requirement_id,

            "original_violation_status":
                original_status,

            "original_violation_evidence":
                " || ".join(
                    original_violation_evidence
                ),

            "resolution_context_status":
                context_status,

            "violated_resolution_context_requirements":
                ", ".join(
                    violated_resolution_context
                ),

            "resolution_context_violation_evidence":
                " || ".join(
                    resolution_context_evidence
                ),

            "num_broken_resolution_context_requirements":
                len(
                    violated_resolution_context
                ),

            "all_remaining_violations":
                ", ".join(
                    sorted(
                        violated_requirements_after
                    )
                )
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
        "original_requirement",
        "pst_file"
    ]
)

# ============================================================
# OVERVIEW
# ============================================================

grouped = df.groupby(
    ["scenario", "original_requirement"]
)

overview_rows = []

for (
    scenario,
    requirement
), group in grouped:

    # --------------------------------------------------------
    # Original violation fixed?
    # --------------------------------------------------------

    fixed_count = len(
        group[
            group[
                "original_violation_status"
            ] == "FIXED"
        ]
    )

    not_fixed_count = len(
        group[
            group[
                "original_violation_status"
            ] == "NOT_FIXED"
        ]
    )

    # --------------------------------------------------------
    # Resolution context preserved?
    # --------------------------------------------------------

    preserved_count = len(
        group[
            group[
                "resolution_context_status"
            ] == "PRESERVED"
        ]
    )

    broken_count = len(
        group[
            group[
                "resolution_context_status"
            ] == "BROKEN"
        ]
    )

    # --------------------------------------------------------
    # Overall statuses
    # --------------------------------------------------------

    if fixed_count > 0:

        overall_fix_status = (
            "FIXED_AT_LEAST_ONCE"
        )

    else:

        overall_fix_status = (
            "NEVER_FIXED"
        )

    if broken_count == 0:

        overall_context_status = (
            "ALWAYS_PRESERVED"
        )

    else:

        overall_context_status = (
            "BROKEN_AT_LEAST_ONCE"
        )

    # --------------------------------------------------------
    # Add row
    # --------------------------------------------------------

    overview_rows.append({

        "scenario":
            scenario,

        "requirement":
            requirement,

        "overall_fix_status":
            overall_fix_status,

        "overall_resolution_context_status":
            overall_context_status,

        "total_strategies":
            len(group),

        "fixed_strategies":
            fixed_count,

        "not_fixed_strategies":
            not_fixed_count,

        "preserved_context_strategies":
            preserved_count,

        "broken_context_strategies":
            broken_count
    })

# ============================================================
# OVERVIEW DATAFRAME
# ============================================================

overview_df = pd.DataFrame(
    overview_rows
)

overview_df = overview_df.sort_values(
    by=[
        "scenario",
        "requirement"
    ]
)

# ============================================================
# SAVE EXCEL
# ============================================================

excel_output = (
    OUTPUT_DIR
    / (
        "resolution_strategy_analysis"
        "_with_context.xlsx"
    )
)

with pd.ExcelWriter(
    excel_output,
    engine="openpyxl"
) as writer:

    # --------------------------------------------------------
    # Detailed results
    # --------------------------------------------------------

    df.to_excel(
        writer,
        sheet_name="all_results",
        index=False
    )

    # --------------------------------------------------------
    # Overview
    # --------------------------------------------------------

    overview_df.to_excel(
        writer,
        sheet_name="overview",
        index=False
    )

    # --------------------------------------------------------
    # Only unresolved
    # --------------------------------------------------------

    df[
        df[
            "original_violation_status"
        ] == "NOT_FIXED"
    ].to_excel(
        writer,
        sheet_name="not_fixed",
        index=False
    )

    # --------------------------------------------------------
    # Broken resolution context
    # --------------------------------------------------------

    df[
        df[
            "resolution_context_status"
        ] == "BROKEN"
    ].to_excel(
        writer,
        sheet_name="broken_context",
        index=False
    )

# ============================================================
# SUMMARY
# ============================================================

print("\n===================================")
print("SUMMARY")
print("===================================\n")

print(df)

print("\n===================================")
print("OVERVIEW")
print("===================================\n")

print(overview_df)

print("\nExcel saved to:")
print(excel_output)