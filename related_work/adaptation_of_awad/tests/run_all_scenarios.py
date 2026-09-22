import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.py"
scenariostest = [
    "inverse_order",

]

scenarios = [
    "splitting_choice",
    "contra",
    "multiple",
    "duplicate_activities",
    #"payment",
    "lack_activity_append_suffix",
    "lack_activity_insert_before_suffix",
    "lack_activity_reuse_prefix",
    "lack_activity_reuse_prefix_parallel",
    "lack_activity_reuse_prefix_xor_insert_inside_branch",
    "lack_activity_after_parallel",
    "lack_activity_after_xor",
    "lack_activity_before_parallel",
    "lack_activity_before_xor",
    "lack_activity_single_contradiction",
    "lack_activity_mid_contradiction",
    "lack_activity_multi_contradiction"

]

for s in scenarios:
    #print("\n==============================")
    #print(f"Running scenario: {s}")
    #print("==============================\n")

    subprocess.run(["python", str(MAIN), s], cwd=ROOT)
