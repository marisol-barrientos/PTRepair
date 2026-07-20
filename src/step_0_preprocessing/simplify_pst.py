# ===============================================================================
# PRELIMINARY STEP: SIMPLIFY PTS FOR RESOLVING COMPLIANCE VIOLATIONS WITH AN LLM
# ===============================================================================
#
# This script converts original CPEE process models (.xml)
# into simplified Process Structure Trees (PSTs) represented
# as readable text. The generated simplified PSTs are later
# used as input for the automated generation of resolution
# strategies.
#
# The script supports executing either:
# - one selected scenario
# - all available scenarios
#
# Output:
# - simplified PST text files
#
# ==============================================================================

import sys
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import subprocess

# -----------------------------------
# Configuration
# -----------------------------------

RUN_ALL_SCENARIOS = False
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

# -----------------------------------
# Dynamically locate project root
# -----------------------------------

BASE_DIR = Path.cwd().parents[1]

# -----------------------------------
# Add paths
# -----------------------------------

SRC_DIR = BASE_DIR / "src"
sys.path.append(str(SRC_DIR))

STEP1_DIR = SRC_DIR / "step_1_generate_resolution_strategies"
sys.path.append(str(STEP1_DIR))

from utils.xml_loader import load_xml
from converter.cpee_to_simplified_pst import convert
from utils.exporter import pst_to_dict, pst_to_text

# -----------------------------------
# Directories
# -----------------------------------

PST_DIR = BASE_DIR / "data" / "input" / "process_models"

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "output"
    / "simplified_pst"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# -----------------------------------
# Run one scenario
# -----------------------------------

def run_scenario(scenario_name):
    print("\n===================================")
    print(f"RUNNING SCENARIO: {scenario_name}")
    print("===================================\n")

    xml_file = PST_DIR / f"{scenario_name}.xml"

    print(f"Using XML file: {xml_file}")

    root = load_xml(xml_file)
    pst = convert(root)

    pst_text = pst_to_text(pst)

    if not pst_text.rstrip().endswith("terminate"):
        pst_text = pst_text.rstrip() + "\nterminate"

    print("\n=== PST (Tree) ===")
    print(pst_text)

    print("\n=== PST (JSON) ===")
    print(
        json.dumps(
            pst_to_dict(pst),
            indent=2
        )
    )

    output_file = (
        OUTPUT_DIR
        / f"{scenario_name}_simplified_pst.txt"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(pst_text)

    print(
        f"\nSimplified PST saved to: "
        f"{output_file}"
    )

# -----------------------------------
# Main execution
# -----------------------------------

if RUN_ALL_SCENARIOS:
    for scenario in SCENARIOS:
        run_scenario(scenario)

else:
    run_scenario(SELECTED_SCENARIO)