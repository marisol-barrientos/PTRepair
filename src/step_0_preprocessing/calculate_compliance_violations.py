# ============================================================
# PRELIMINARY STEP: CALCULATE INITIAL COMPLIANCE VIOLATIONS
# ============================================================
#
# This script evaluates the original process models against
# their associated compliance requirement sets using the
# ProcessTreeVerify verifier.
#
# For each scenario, the script:
# - injects the compliance requirements into the process model
# - executes the compliance verification
# - extracts the detected violations
# - stores the generated violation reports
#
# The script supports executing either:
# - one selected scenario
# - all available scenarios
#
# Output:
# - compliance violation reports (.json)
#
# ============================================================

import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# -----------------------------------
# Configuration
# -----------------------------------

RUN_ALL_SCENARIOS = True
SELECTED_SCENARIO = "01_awad_delivery_of_goods"

SCENARIOS = [
    "01_awad_delivery_of_goods",
    "02_de_masellis_loan_approval",
    "03_elgammal_loan_approval",
    "04_ghose_package_screening",
    "05_loebbecke_blood_collection",
    "06_BPMQ",
    "07_CRL",
    "08_DCR",
    "09_HaarmannetAL2021",
    "11_PCL",
    "12_PPSL",
    "13_Status",
    "14_SunetAl24",
    "15_WinteretAlER",
    "16_Zasadaetal23"
]

VERIFY_ALL = True

selected_requirement_ids = [
    "R1"
]

# -----------------------------------
# Dynamically locate project root
# -----------------------------------

BASE_DIR = Path.cwd().parents[1]

# -----------------------------------
# Paths
# -----------------------------------

PTV_SCRIPT = (
    BASE_DIR
    / "src"
    / "ProcessTreeVerify"
    / "python_code"
    / "test_script.py"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "compliance_violations_before_changes"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# -----------------------------------
# Namespaces
# -----------------------------------

NS_PROPERTIES = (
    "http://cpee.org/ns/properties/2.0"
)

NS_SUBSCRIPTIONS = (
    "http://riddl.org/ns/common-patterns/"
    "notifications-producer/2.0"
)

namespace = {
    "ns1": NS_PROPERTIES
}

# -----------------------------------
# Ensure <requirements> node
# -----------------------------------

def ensure_requirements_node(root):
    attributes_node = root.find(
        ".//ns1:attributes",
        namespace
    )

    if attributes_node is None:
        raise ValueError(
            "No <attributes> node found."
        )

    req_node = root.find(
        ".//ns1:requirements",
        namespace
    )

    if req_node is None:
        print(
            "\n[INFO] Creating "
            "<requirements> node."
        )

        req_node = ET.SubElement(
            attributes_node,
            f"{{{NS_PROPERTIES}}}requirements"
        )

    else:
        print(
            "\n[INFO] Existing "
            "<requirements> node found."
        )

    return req_node

# -----------------------------------
# Ensure <subscriptions> block
# -----------------------------------

def ensure_subscriptions(root):
    subscriptions = root.find(
        f"{{{NS_SUBSCRIPTIONS}}}subscriptions"
    )

    if subscriptions is not None:
        print(
            "\n[INFO] Subscriptions block already exists."
        )
        return

    print(
        "\n[INFO] Creating subscriptions block."
    )

    subscriptions = ET.SubElement(
        root,
        f"{{{NS_SUBSCRIPTIONS}}}subscriptions"
    )

    subscription = ET.SubElement(
        subscriptions,
        f"{{{NS_SUBSCRIPTIONS}}}subscription",
        {
            "id": "_compliance",
            "url": (
                "https://power.bpm.cit.tum.de/"
                "compliance/Subscriber"
            )
        }
    )

    topic = ET.SubElement(
        subscription,
        f"{{{NS_SUBSCRIPTIONS}}}topic",
        {
            "id": "description"
        }
    )

    event = ET.SubElement(
        topic,
        f"{{{NS_SUBSCRIPTIONS}}}event"
    )

    event.text = "change"

# -----------------------------------
# Run one scenario
# -----------------------------------

def run_scenario(scenario_name):
    print("\n===================================")
    print(f"RUNNING SCENARIO: {scenario_name}")
    print("===================================\n")

    xml_file = (
        BASE_DIR
        / "data"
        / "input"
        / "process_models"
        / "cpee_trees"
        / f"{scenario_name}.xml"
    )

    requirements_file = (
        BASE_DIR
        / "data"
        / "input"
        / "compliance_requirements"
        / "ast"
        / f"{scenario_name}.json"
    )

    with open(
        requirements_file,
        "r",
        encoding="utf-8"
    ) as f:
        all_requirements = json.load(f)

    if VERIFY_ALL:
        requirements = all_requirements

        print(
            "\nMode: VERIFY ALL REQUIREMENTS"
        )

    else:
        print(
            "\nMode: VERIFY SELECTED REQUIREMENTS"
        )

        missing_requirements = [
            rid
            for rid in selected_requirement_ids
            if rid not in all_requirements
        ]

        if missing_requirements:
            raise ValueError(
                f"Requirements not found: "
                f"{missing_requirements}"
            )

        requirements = {
            rid: all_requirements[rid]
            for rid in selected_requirement_ids
        }

    requirements_text = json.dumps(
        requirements,
        ensure_ascii=False
    )

    print("\nInjected requirements:")
    print(requirements_text)

    tree = ET.parse(xml_file)
    root = tree.getroot()

    req_node = ensure_requirements_node(root)
    ensure_subscriptions(root)

    req_node.text = requirements_text

    print(
        "\n[INFO] Requirements successfully injected."
    )

    with tempfile.NamedTemporaryFile(
        suffix=".xml",
        delete=False
    ) as tmp:
        temp_xml_path = Path(tmp.name)

    tree.write(
        temp_xml_path,
        encoding="utf-8",
        xml_declaration=True
    )

    print(
        f"\nTemporary XML created:\n"
        f"{temp_xml_path}"
    )

    result = subprocess.run(
        [
            "python3",
            str(PTV_SCRIPT),
            str(temp_xml_path)
        ],
        capture_output=True,
        text=True
    )

    print("\n=== STDOUT ===")
    print(result.stdout)

    print("\n=== STDERR ===")
    print(result.stderr)

    marker = "===== VIOLATION REPORT ====="

    if marker in result.stdout:
        violation_json = (
            result.stdout
            .split(marker)[-1]
            .strip()
        )

        violation_report = json.loads(
            violation_json
        )

        if VERIFY_ALL:
            selected_name = "ALL"

        else:
            selected_name = "_".join(
                selected_requirement_ids
            )

        output_file = (
            OUTPUT_DIR
            / (
                f"{scenario_name}_"
                f"{selected_name}_violations.json"
            )
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

    else:
        print("\nNo violation report found.")

    temp_xml_path.unlink(
        missing_ok=True
    )

    print("\nTemporary XML deleted.")

# -----------------------------------
# Main execution
# -----------------------------------

if RUN_ALL_SCENARIOS:
    for scenario in SCENARIOS:
        run_scenario(scenario)

else:
    run_scenario(SELECTED_SCENARIO)