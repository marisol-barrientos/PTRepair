import argparse
import os
import json
import re
import logging
import assurancelogger
import xml.etree.ElementTree as ET

from LogHandler import LogHandler
from util import (
    transform_log,
    exists_by_label,
    get_ancestors,
    compare_ele,
    add_start_end,
    combine_sub_trees
)
from tester import run_tests
from reqparser import parse_requirements
from verificationAST import verify


# -----------------------------
# Helper functions
# -----------------------------

def extract_verdict(message):
    """Extract violation + assurance"""

    violation = "False" in message

    match = re.search(r'(\d+)$', message)

    assurance = int(match.group(1)) if match else None

    return violation, assurance


def build_violation_report(xes_log):
    """Transform XES log → structured report"""

    grouped = {}

    report = []

    # -----------------------------
    # Group events by requirement ID
    # -----------------------------
    for e in xes_log:

        ev = e["event"]

        rid = ev["concept:instance"]

        if rid not in grouped:
            grouped[rid] = []

        grouped[rid].append(ev)

    # -----------------------------
    # Process grouped events
    # -----------------------------
    for rid, events in grouped.items():

        current = {
            "requirement_id": rid,
            "requirement": None,
            "assurance": None,
            "evidence": [],
            "_violation": False
        }

        for ev in events:

            msg = ev["data"]

            # -----------------------------
            # START event
            # -----------------------------
            if ev["lifecycle:transition"] == "start":

                requirement = re.sub(
                    r"^Verifying Requirement [^:]+:\s*",
                    "",
                    msg
                )

                current["requirement"] = requirement

            # -----------------------------
            # COMPLETE event
            # -----------------------------
            elif ev["lifecycle:transition"] == "complete":

                violation, assurance = extract_verdict(msg)

                current["_violation"] = violation

                current["assurance"] = assurance

            # -----------------------------
            # EVIDENCE event
            # -----------------------------
            elif ev["concept:name"] != "<module>":

                current["evidence"].append(msg)

        # -----------------------------
        # Keep only violated requirements
        # -----------------------------
        if current["_violation"]:

            del current["_violation"]

            report.append(current)

    return report


# -----------------------------
# Logging setup
# -----------------------------

logger = logging.getLogger("Top Level")

log = []

handler = LogHandler(log)

logging.basicConfig(
    level=logging.INFO,
    format=(
        '%(asctime)s.%(msecs)03d - '
        '%(name)s - '
        '%(funcName)s - '
        '%(message)s'
    ),
    handlers=[handler]
)


# -----------------------------
# Argument parsing
# -----------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    'process',
    help="Path to process tree XML file"
)

args = parser.parse_args()


# -----------------------------
# File loading
# -----------------------------

xml = ET.parse(args.process)


# -----------------------------
# Data preparation
# -----------------------------

namespace1 = {
    "ns0": "http://cpee.org/ns/description/1.0"
}

namespace2 = {
    "ns1": "http://cpee.org/ns/properties/2.0"
}

req = xml.find(
    './/ns1:requirements',
    namespace2
)

xml = xml.find(
    './/ns0:description',
    namespace1
)

requirements = parse_requirements(req.text)

xml = add_start_end(xml)

xml = combine_sub_trees(xml)


# -----------------------------
# Verification
# -----------------------------

pre_parsing_assurance = logger.get_assurance_level()

logger.info(
    f"The global assurance level is "
    f"{pre_parsing_assurance}"
)

logger.reset_assurance_level()

verified_requirements = []

# ---------------------------------
# Preserve original requirement IDs
# ---------------------------------

for req_id, req_text in requirements.items():

    logger.info(
        f"Verifying Requirement {req_id}: "
        f"{req_text}"
    )

    result, assurance = verify(
        req_text,
        tree=xml
    )

    message = (
        f"Requirement {req_id} is "
        f"{bool(result)} with assurance level "
        f"{assurance}"
    )

    logger.info(message)

    verified_requirements.append(
        {
            "requirement_id": req_id,
            "result": bool(result),
            "assurance": assurance,
            "message": message
        }
    )

    logger.reset_assurance_level()


logger.info(
    f"Currently required activities for the process are: "
    f"{logger.get_activities()}"
)

logger.info(
    f"Currently missing activities for the process are: "
    f"{logger.get_missing_activities()}"
)


# -----------------------------
# Transform logs
# -----------------------------

xes_log = transform_log(log)


# -----------------------------
# Build violation report
# -----------------------------

violation_report = build_violation_report(
    xes_log
)


# -----------------------------
# Save violation report
# -----------------------------

# PTResolver repository root
REPO_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

output_dir = os.path.join(
    REPO_ROOT,
    "data",
    "output",
    "compliance_violations_before_changes"
)

os.makedirs(
    output_dir,
    exist_ok=True
)

process_name = os.path.splitext(
    os.path.basename(args.process)
)[0]

output_file = os.path.join(
    output_dir,
    f"{process_name}_violations.json"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        violation_report,
        f,
        indent=4,
        ensure_ascii=False
    )

print(
    f"\nViolation report saved to:\n"
    f"{output_file}"
)


# -----------------------------
# Print outputs
# -----------------------------

print("\n===== FULL XES LOG =====")

print(
    json.dumps(
        xes_log,
        indent=4,
        ensure_ascii=False
    )
)

print("\n===== VIOLATION REPORT =====")

print(
    json.dumps(
        violation_report,
        indent=4,
        ensure_ascii=False
    )
)