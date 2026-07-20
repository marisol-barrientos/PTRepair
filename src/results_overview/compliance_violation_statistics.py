# ============================================================
# ANALYSIS STEP:
# CALCULATE GLOBAL COMPLIANCE VIOLATION STATISTICS
# ============================================================
#
# This script analyzes multiple compliance violation reports
# generated from process verification runs and computes
# aggregated statistics about violated compliance patterns.
#
# For each violation report, the script:
# - extracts violated compliance requirements
# - identifies the compliance patterns involved
# - computes global and per-file statistics
# - aggregates requirement-level information
#
# The script produces:
# - global violation statistics
# - per-scenario/file pattern distributions
# - requirement-level summaries
# - average/minimum/maximum violations
#
# Output:
# - aggregated violation statistics (.json)
#
# ============================================================

import json
import re
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
# CONFIGURATION
# ============================================================

# Folder containing multiple violation JSON files

INPUT_FOLDER = (
    BASE_DIR
    / "data"
    / "output"
    / "compliance_violations_before_changes"
)

# Output summary file

OUTPUT_JSON = (
    BASE_DIR
    / "data"
    / "output"
    / "global_violation_statistics.json"
)

# Allowed compliance patterns

ALLOWED_PATTERNS = [
    "exists",
    "absence",
    "loop",
    "directly_follows",
    "leads_to",
    "precedence",
    "leads_to_absence",
    "precedence_absence",
    "parallel",
    "executed_by",
    "timed_alternative",
    "activity_sends",
    "activity_receives",
    "condition_directly_follows",
    "condition_eventually_follows",
    "data_leads_to_absence"
]

# ============================================================
# INITIALIZATION
# ============================================================

pattern_regex = re.compile(
    r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
)

global_pattern_counter = Counter()

file_statistics = {}

requirement_statistics = defaultdict(list)

total_files = 0
total_violations = 0

# ============================================================
# ITERATE OVER ALL JSON FILES
# ============================================================

json_files = list(
    Path(INPUT_FOLDER).glob("*.json")
)

for json_file in json_files:

    total_files += 1

    print(f"Processing: {json_file.name}")

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as f:

            violations = json.load(f)

    except Exception as e:

        print(
            f"ERROR reading "
            f"{json_file.name}: {e}"
        )

        continue

    # --------------------------------------------------------
    # Skip invalid structures
    # --------------------------------------------------------

    if not isinstance(violations, list):

        print(
            f"Skipping {json_file.name}: "
            f"expected a list"
        )

        continue

    file_pattern_counter = Counter()

    file_violation_count = len(violations)

    total_violations += file_violation_count

    # --------------------------------------------------------
    # PROCESS EACH VIOLATION
    # --------------------------------------------------------

    for violation in violations:

        requirement_id = violation.get(
            "requirement_id",
            "UNKNOWN"
        )

        requirement = violation.get(
            "requirement",
            ""
        )

        found_patterns = pattern_regex.findall(
            requirement
        )

        valid_patterns = [
            p for p in found_patterns
            if p in ALLOWED_PATTERNS
        ]

        # ----------------------------------------------------
        # Global statistics
        # ----------------------------------------------------

        for pattern in valid_patterns:

            global_pattern_counter[
                pattern
            ] += 1

            file_pattern_counter[
                pattern
            ] += 1

        # ----------------------------------------------------
        # Store requirement-level info
        # ----------------------------------------------------

        requirement_statistics[
            json_file.name
        ].append({

            "requirement_id":
                requirement_id,

            "patterns":
                valid_patterns
        })

    # --------------------------------------------------------
    # STORE FILE-LEVEL STATS
    # --------------------------------------------------------

    file_statistics[json_file.name] = {

        "violations":
            file_violation_count,

        "pattern_distribution":
            dict(file_pattern_counter)
    }

# ============================================================
# ADDITIONAL VIOLATION STATISTICS
# ============================================================

violations_per_file = [
    stats["violations"]
    for stats in file_statistics.values()
]

if violations_per_file:

    average_violations = (
        sum(violations_per_file)
        / len(violations_per_file)
    )

    minimum_violations = min(
        violations_per_file
    )

    maximum_violations = max(
        violations_per_file
    )

else:

    average_violations = 0
    minimum_violations = 0
    maximum_violations = 0

# ============================================================
# PRINT GLOBAL RESULTS
# ============================================================

print("\n" + "=" * 70)

print(
    "GLOBAL COMPLIANCE VIOLATION STATISTICS"
)

print("=" * 70)

print(
    f"\nTotal JSON files processed: "
    f"{total_files}"
)

print(
    f"Total violations found:     "
    f"{total_violations}"
)

print(
    f"Average violations per scenario: "
    f"{average_violations:.2f}"
)

print(
    f"Minimum violations in a scenario: "
    f"{minimum_violations}"
)

print(
    f"Maximum violations in a scenario: "
    f"{maximum_violations}"
)

print("\nGLOBAL PATTERN DISTRIBUTION")

print("-" * 70)

for pattern in sorted(ALLOWED_PATTERNS):

    count = global_pattern_counter.get(
        pattern,
        0
    )

    percentage = (
        (count / total_violations) * 100
        if total_violations > 0 else 0
    )

    print(
        f"{pattern:<35} "
        f"{count:>6} "
        f"({percentage:.2f}%)"
    )

# ============================================================
# PRINT FILE-LEVEL SUMMARY
# ============================================================

print("\nFILE-LEVEL STATISTICS")

print("-" * 70)

for file_name, stats in file_statistics.items():

    print(f"\n{file_name}")

    print(
        f"  Violations: "
        f"{stats['violations']}"
    )

    if stats["pattern_distribution"]:

        for pattern, count in sorted(
            stats[
                "pattern_distribution"
            ].items()
        ):

            print(
                f"    {pattern:<30} "
                f"{count}"
            )

    else:

        print(
            "    No recognized patterns found"
        )

# ============================================================
# SAVE RESULTS
# ============================================================

summary = {

    "total_files":
        total_files,

    "total_violations":
        total_violations,

    "average_violations_per_scenario":
        average_violations,

    "minimum_violations_per_scenario":
        minimum_violations,

    "maximum_violations_per_scenario":
        maximum_violations,

    "global_pattern_distribution":
        dict(global_pattern_counter),

    "file_statistics":
        file_statistics,

    "requirement_statistics":
        dict(requirement_statistics)
}

with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=4
    )

print("\n" + "=" * 70)

print(
    f"Statistics saved to:\n"
    f"{OUTPUT_JSON}"
)

print("=" * 70)