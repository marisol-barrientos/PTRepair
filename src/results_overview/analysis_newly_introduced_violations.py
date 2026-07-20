# ============================================================
# ANALYSIS:
# DO NEWLY BROKEN RESOLUTION CONTEXT REQUIREMENTS
# CORRESPOND TO PREVIOUS OVERLAPS?
# ============================================================
#
# This script checks whether newly violated
# resolution context requirements are associated
# with structural overlaps between:
#
# - originally violated requirements
# - previously compliant requirements
#
# Overlap dimensions:
# - activities
# - resources
# - data
# - temporal constraints
#
# Output:
# - detailed overlap-impact analysis
# - Excel summary
#
# ============================================================

import json
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
# ------------------------------------------------------------
# INPUTS
# ------------------------------------------------------------

COMPLIANCE_REQUIREMENTS_DIR = (
    BASE_DIR
    / "data/input/compliance_requirements"
)

RESOLUTION_CONTEXT_DIR = (
    BASE_DIR
    / "data/input/resolution_context"
)

VIOLATIONS_AFTER_CHANGES_DIR = (
    BASE_DIR
    / "data/output/compliance_violations_after_changes"
)

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR = (
    BASE_DIR
    / "data/output/overlap_resolution_context_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# REGEX
# ============================================================

PATTERN_REGEX = re.compile(
    r'(\w+)\((.*?)\)'
)

# ============================================================
# HELPERS
# ============================================================

def split_arguments(arg_string):

    args = re.findall(
        r"'([^']*)'|([^,]+)",
        arg_string
    )

    cleaned = []

    for a, b in args:

        val = a if a else b

        cleaned.append(
            val.strip()
        )

    return cleaned

# ============================================================
# EXTRACT STRUCTURAL ELEMENTS
# ============================================================

def extract_elements(requirement_text):

    result = {
        "activities": set(),
        "resources": set(),
        "data": set(),
        "temporal": set(),
    }

    matches = PATTERN_REGEX.findall(
        requirement_text
    )

    for pattern_name, arg_string in matches:

        args = split_arguments(
            arg_string
        )

        # ----------------------------------------------------
        # Activity-only
        # ----------------------------------------------------

        if pattern_name in {
            "exists",
            "absence",
            "loop"
        }:

            if len(args) >= 1:

                result["activities"].add(
                    args[0]
                )

        # ----------------------------------------------------
        # Temporal
        # ----------------------------------------------------

        elif pattern_name in {
            "directly_follows",
            "leads_to",
            "precedence",
            "leads_to_absence",
            "precedence_absence",
            "parallel",
            "condition_directly_follows",
            "condition_eventually_follows"
        }:

            if len(args) >= 2:

                result["activities"].update(
                    [args[0], args[1]]
                )

                result["temporal"].add(
                    pattern_name
                )

        # ----------------------------------------------------
        # Resource
        # ----------------------------------------------------

        elif pattern_name == "executed_by":

            if len(args) >= 2:

                result["activities"].add(
                    args[0]
                )

                result["resources"].add(
                    args[1]
                )

        # ----------------------------------------------------
        # Timed
        # ----------------------------------------------------

        elif pattern_name == (
            "timed_alternative"
        ):

            if len(args) >= 3:

                result["activities"].update(
                    [args[0], args[1]]
                )

                result["temporal"].add(
                    "timed_alternative"
                )

        # ----------------------------------------------------
        # Data
        # ----------------------------------------------------

        elif pattern_name in {
            "activity_sends",
            "activity_receives",
            "data_leads_to_absence"
        }:

            if len(args) >= 2:

                result["activities"].add(
                    args[0]
                )

                result["data"].add(
                    args[1]
                )

    return result

# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)

# ============================================================
# RESULTS
# ============================================================

rows = []

# ============================================================
# ITERATE SCENARIOS
# ============================================================

scenario_dirs = sorted(
    VIOLATIONS_AFTER_CHANGES_DIR.iterdir()
)

for scenario_dir in scenario_dirs:

    if not scenario_dir.is_dir():
        continue

    scenario_name = scenario_dir.name

    print("\n===================================")
    print("SCENARIO:", scenario_name)
    print("===================================\n")

    # --------------------------------------------------------
    # Load original violated requirements
    # --------------------------------------------------------

    violated_req_file = (
        COMPLIANCE_REQUIREMENTS_DIR
        / f"{scenario_name}.json"
    )

    if not violated_req_file.exists():

        print(
            "Missing compliance requirements."
        )

        continue

    violated_requirements = load_json(
        violated_req_file
    )

    # --------------------------------------------------------
    # Load resolution context
    # --------------------------------------------------------

    resolution_context_file = (
        RESOLUTION_CONTEXT_DIR
        / (
            f"{scenario_name}"
            f"_req_resolution_context.json"
        )
    )

    if not resolution_context_file.exists():

        print(
            "No resolution context."
        )

        continue

    resolution_context = load_json(
        resolution_context_file
    )

    # --------------------------------------------------------
    # PST violation reports
    # --------------------------------------------------------

    violation_reports = sorted(
        scenario_dir.glob("*.json")
    )

    for report_file in violation_reports:

        print(
            "Processing:",
            report_file.name
        )

        # ----------------------------------------------------
        # Extract original violated requirement
        # ----------------------------------------------------

        stem = report_file.stem

        parts = stem.split("_")

        original_requirement = None

        for part in parts:

            if (
                part.startswith("R")
                and len(part) > 1
                and part[1:].isdigit()
            ):

                original_requirement = part

                break

        if original_requirement is None:
            continue

        # ----------------------------------------------------
        # Load violation report
        # ----------------------------------------------------

        report_content = load_json(
            report_file
        )

        if isinstance(report_content, dict):

            violations_after = (
                report_content.get(
                    "violation_report",
                    []
                )
            )

        else:

            violations_after = report_content

        # ----------------------------------------------------
        # Collect newly violated resolution context reqs
        # ----------------------------------------------------

        broken_context_requirements = []

        for violation in violations_after:

            if not isinstance(
                violation,
                dict
            ):
                continue

            req_id = violation.get(
                "requirement_id"
            )

            if (
                req_id
                in resolution_context
            ):

                broken_context_requirements.append(
                    req_id
                )

        broken_context_requirements = sorted(
            set(
                broken_context_requirements
            )
        )

        # ----------------------------------------------------
        # Extract original violated structure
        # ----------------------------------------------------

        if (
            original_requirement
            not in violated_requirements
        ):

            continue

        original_elements = (
            extract_elements(
                violated_requirements[
                    original_requirement
                ]
            )
        )

        # ----------------------------------------------------
        # Compare with broken context reqs
        # ----------------------------------------------------

        for broken_req in (
            broken_context_requirements
        ):

            broken_elements = (
                extract_elements(
                    resolution_context[
                        broken_req
                    ]
                )
            )

            # ------------------------------------------------
            # Overlaps
            # ------------------------------------------------

            activity_overlap = sorted(
                original_elements[
                    "activities"
                ]
                &
                broken_elements[
                    "activities"
                ]
            )

            resource_overlap = sorted(
                original_elements[
                    "resources"
                ]
                &
                broken_elements[
                    "resources"
                ]
            )

            data_overlap = sorted(
                original_elements[
                    "data"
                ]
                &
                broken_elements[
                    "data"
                ]
            )

            temporal_overlap = sorted(
                original_elements[
                    "temporal"
                ]
                &
                broken_elements[
                    "temporal"
                ]
            )

            # ------------------------------------------------
            # Any overlap?
            # ------------------------------------------------

            any_overlap = any([
                activity_overlap,
                resource_overlap,
                data_overlap,
                temporal_overlap
            ])

            # ------------------------------------------------
            # Add row
            # ------------------------------------------------

            rows.append({

                "scenario":
                    scenario_name,

                "pst_file":
                    report_file.name,

                "original_violated_requirement":
                    original_requirement,

                "newly_broken_requirement":
                    broken_req,

                "has_overlap":
                    any_overlap,

                "activity_overlap":
                    ", ".join(
                        activity_overlap
                    ),

                "resource_overlap":
                    ", ".join(
                        resource_overlap
                    ),

                "data_overlap":
                    ", ".join(
                        data_overlap
                    ),

                "temporal_overlap":
                    ", ".join(
                        temporal_overlap
                    ),

                "num_activity_overlap":
                    len(
                        activity_overlap
                    ),

                "num_resource_overlap":
                    len(
                        resource_overlap
                    ),

                "num_data_overlap":
                    len(
                        data_overlap
                    ),

                "num_temporal_overlap":
                    len(
                        temporal_overlap
                    )
            })

# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(rows)

# ============================================================
# OVERVIEW STATISTICS
# ============================================================

if len(df) > 0:

    total_cases = len(df)

    overlap_cases = len(
        df[
            df["has_overlap"] == True
        ]
    )

    no_overlap_cases = (
        total_cases - overlap_cases
    )

    overview_df = pd.DataFrame([{

        "total_broken_context_cases":
            total_cases,

        "cases_with_overlap":
            overlap_cases,

        "cases_without_overlap":
            no_overlap_cases,

        "percentage_with_overlap":
            round(
                (
                    overlap_cases
                    / total_cases
                ) * 100,
                2
            )
    }])

else:

    overview_df = pd.DataFrame()

# ============================================================
# SAVE EXCEL
# ============================================================

excel_output = (
    OUTPUT_DIR
    / (
        "overlap_vs_broken_context"
        ".xlsx"
    )
)

with pd.ExcelWriter(
    excel_output,
    engine="openpyxl"
) as writer:

    df.to_excel(
        writer,
        sheet_name="detailed_results",
        index=False
    )

    overview_df.to_excel(
        writer,
        sheet_name="overview",
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