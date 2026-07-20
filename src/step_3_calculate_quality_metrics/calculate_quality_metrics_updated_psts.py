# ============================================================
# STEP 3: VERIFY COMPLIANCE OF UPDATED PSTS
# ============================================================
#
# This script evaluates the updated Process Structure Trees
# (PSTs) generated after applying resolution strategies.
#
# The verification now includes:
# - originally violated requirements
# - resolution context requirements
#
# This allows checking:
# - whether the targeted violations were fixed
# - whether previously compliant requirements
#   remain compliant after adaptation
#
# Output:
# - compliance violation reports for updated PSTs (.json)
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

SELECTED_SCENARIO = (
    "01_awad_delivery_of_goods"
)

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

UPDATED_PST_DIR = (
    BASE_DIR
    / "data"
    / "ablation_study_step_1"
    / "final_prompt_4th_iteration"
    / "updated_pst"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "ablation_study_step_1"
    / "final_prompt_4th_iteration"
    / "compliance_violations_after_changes"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# -----------------------------------
# Requirement folders
# -----------------------------------

VIOLATION_REQUIREMENTS_DIR = (
    BASE_DIR
    / "data"
    / "input"
    / "compliance_requirements"
    / "ast"
)

RESOLUTION_CONTEXT_DIR = (
    BASE_DIR
    / "data"
    / "input"
    / "resolution_context"
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
# Load resolution context
# -----------------------------------

def load_resolution_context(
    scenario_name
):

    resolution_context_file = (
        RESOLUTION_CONTEXT_DIR
        / (
            f"{scenario_name}"
            f"_req_resolution_context.json"
        )
    )

    if not resolution_context_file.exists():

        print(
            "\n[INFO] No resolution context "
            "requirements found."
        )

        return {}

    with open(
        resolution_context_file,
        "r",
        encoding="utf-8"
    ) as f:

        resolution_context = json.load(f)

    print(
        f"\n[INFO] Loaded "
        f"{len(resolution_context)} "
        f"resolution context requirements."
    )

    return resolution_context

# -----------------------------------
# Run one PST
# -----------------------------------

def run_pst(
    scenario_name,
    pst_file
):

    print("\n===================================")
    print(f"SCENARIO: {scenario_name}")
    print(f"PST: {pst_file.name}")
    print("===================================\n")

    # -----------------------------------
    # Load violation requirements
    # -----------------------------------

    requirements_file = (
        VIOLATION_REQUIREMENTS_DIR
        / f"{scenario_name}.json"
    )

    with open(
        requirements_file,
        "r",
        encoding="utf-8"
    ) as f:

        all_requirements = json.load(f)

    print(
        f"\n[INFO] Loaded "
        f"{len(all_requirements)} "
        f"violation requirements."
    )

    # -----------------------------------
    # Select requirements
    # -----------------------------------

    if VERIFY_ALL:

        requirements = all_requirements

        print(
            "\nMode: VERIFY ALL VIOLATION REQUIREMENTS"
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

    # -----------------------------------
    # Load resolution context
    # -----------------------------------

    resolution_context = (
        load_resolution_context(
            scenario_name
        )
    )

    # -----------------------------------
    # Merge requirements
    # -----------------------------------

    merged_requirements = {
        **requirements,
        **resolution_context
    }

    requirements_text = json.dumps(
        merged_requirements,
        ensure_ascii=False
    )

    print("\nInjected requirements:")
    print(requirements_text)

    print(
        f"\n[INFO] Total injected requirements:"
        f" {len(merged_requirements)}"
    )

    # -----------------------------------
    # Parse PST
    # -----------------------------------

    tree = ET.parse(pst_file)

    root = tree.getroot()

    req_node = ensure_requirements_node(root)

    ensure_subscriptions(root)

    req_node.text = requirements_text

    print(
        "\n[INFO] Requirements successfully injected."
    )

    # -----------------------------------
    # Create temp XML
    # -----------------------------------

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

    # -----------------------------------
    # Run verifier
    # -----------------------------------

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

    # -----------------------------------
    # Extract violation report
    # -----------------------------------

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

        # -----------------------------------
        # Add metadata
        # -----------------------------------

        violation_report_with_metadata = {

            "scenario_name":
                scenario_name,

            "pst_file":
                pst_file.name,

            "verified_violation_requirements":
                list(requirements.keys()),

            "verified_resolution_context_requirements":
                list(
                    resolution_context.keys()
                ),

            "all_verified_requirements":
                list(
                    merged_requirements.keys()
                ),

            "violation_report":
                violation_report
        }

        # -----------------------------------
        # Scenario output directory
        # -----------------------------------

        scenario_output_dir = (
            OUTPUT_DIR
            / scenario_name
        )

        scenario_output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # -----------------------------------
        # Output filename
        # -----------------------------------

        output_file = (
            scenario_output_dir
            / (
                f"{pst_file.stem}"
                f"_violations.json"
            )
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                violation_report_with_metadata,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"\nViolation report saved to:\n"
            f"{output_file}"
        )

    else:

        print(
            "\nNo violation report found."
        )

    # -----------------------------------
    # Delete temp XML
    # -----------------------------------

    temp_xml_path.unlink(
        missing_ok=True
    )

    print(
        "\nTemporary XML deleted."
    )

# -----------------------------------
# Main execution
# -----------------------------------

scenario_dirs = sorted(
    UPDATED_PST_DIR.iterdir()
)

for scenario_dir in scenario_dirs:

    if not scenario_dir.is_dir():
        continue

    scenario_name = scenario_dir.name

    if (
        not RUN_ALL_SCENARIOS
        and scenario_name != SELECTED_SCENARIO
    ):
        continue

    pst_dir = (
        scenario_dir
        / "pst"
    )

    if not pst_dir.exists():

        print(
            f"\nNo pst folder found for:"
            f" {scenario_name}"
        )

        continue

    pst_files = sorted(
        pst_dir.glob("*.xml")
    )

    print("\n===================================")
    print(f"FOUND {len(pst_files)} PST FILES")
    print(f"FOR SCENARIO {scenario_name}")
    print("===================================\n")

    for pst_file in pst_files:

        run_pst(
            scenario_name,
            pst_file
        )
