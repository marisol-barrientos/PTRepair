"""
Scenario-driven debug entry point.

Run:
    python main.py certificate
    python main.py payment
"""

from __future__ import annotations

import importlib
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from src.context.business_context import BusinessContext
from src.model.pst import ProcessStructureTree
from src.planning.planner import Planner, FastDownwardConfig
from src.resolution.compliance_resolver import ComplianceResolver, ViolationType
from src.model.node import Node, NodeType


PROJECT_ROOT = Path(__file__).resolve().parent
SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "certificate"

TREE_XML = PROJECT_ROOT / "data" / "examples" / f"{SCENARIO}_scenario_tree.xml"
DEFAULTS_MODULE = f"src.context.{SCENARIO}_scenario_defaults"

PYTHON_EXE = "python3"
FD_ALIAS = "lama-first"
DEBUG = True


def log(msg: str = "") -> None:
    print(msg, flush=True)


def load_defaults_module():
    log(f"\nLoading defaults: {DEFAULTS_MODULE}")
    return importlib.import_module(DEFAULTS_MODULE)


def pick_first_occurrence(tree: ProcessStructureTree, label: str) -> Optional[Node]:
    """
    Case/whitespace-insensitive lookup of the first activity occurrence.
    """
    target = " ".join(label.strip().lower().split())

    # safest: traverse all activities via the tree root
    def walk(n: Node) -> List[Node]:
        out: List[Node] = []
        if n.node_type == NodeType.Activity:
            out.append(n)
        for ch in getattr(n, "children", []) or []:
            out.extend(walk(ch))
        return out

    for act in walk(tree.root):
        lab = " ".join(act.label.strip().lower().split())
        if lab == target:
            return act
    return None


def main() -> None:
    t0 = time.time()

    log("===================================")
    log(f"Running scenario: {SCENARIO}")
    log("===================================")

    # -------------------------
    # Load defaults
    # -------------------------
    defaults = load_defaults_module()

    SRC_LABEL = defaults.SRC_LABEL.strip()
    DST_LABEL = defaults.DST_LABEL.strip()

    log(f"SRC = {SRC_LABEL}")
    log(f"DST = {DST_LABEL}")

    # -------------------------
    # Business Context
    # -------------------------
    log("\n[1/5] Loading BusinessContext...")
    bc = BusinessContext()
    bc.load_from_defaults_module(defaults)
    log(f"Init bases: {bc.get_initial_state_alternatives()}")

    # -------------------------
    # Load PST
    # -------------------------
    log("\n[2/5] Loading PST...")
    pst = ProcessStructureTree()
    pst.load_tree_from_file(str(TREE_XML))

    if DEBUG:
        log(pst.print_tree())

    # -------------------------
    # Planner
    # -------------------------
    log("\n[3/5] Planner setup...")
    fd_script = PROJECT_ROOT / "planners" / "fast-downward" / "fast-downward.py"
    work_dir = PROJECT_ROOT / "fd_work"

    cfg = FastDownwardConfig(
        fd_path=str(fd_script),
        python_exe=PYTHON_EXE,
        alias=FD_ALIAS,
        work_dir=str(work_dir),
        plan_file="sas_plan",
    )

    planner = Planner(bc, cfg)

    # -------------------------
    # Resolver
    # -------------------------
    log("\n[4/5] Resolver...")
    resolver = ComplianceResolver(pst, bc, planner=planner)

    # -------------------------
    # SRC / DST
    # -------------------------
    log("\n[5/5] Finding nodes...")
    src = pick_first_occurrence(pst, SRC_LABEL)
    dst = pick_first_occurrence(pst, DST_LABEL)

    if src is None:
        raise ValueError(f"SRC not found: {SRC_LABEL}")

    if dst is None:
        log("DST not in PST — creating virtual node")
        dst = Node(node_type=NodeType.Activity)
        dst.set_label(DST_LABEL)

    vt = resolver.get_violation_type_of_leads_to(src, dst)
    log(f"\nViolation type: {vt}")

    # Dispatch to the correct resolver based on violation type
    new_tree = None

    if vt == ViolationType.splittingChoice:
        new_tree = resolver.resolve_splitting_choice_violation(src, dst)
        # optional: cleanup redundant blocks (collapse single-branch choice, flatten sequences)
        resolver.cleanup_redundant_blocks()

    elif vt == ViolationType.LackofActivity:
        new_tree = resolver.resolve_lack_of_activity_violation(src, dst)

    elif vt == ViolationType.DifferentBranches:
        new_tree = resolver.resolve_different_branches_violation(src, dst)

    elif vt == ViolationType.InverseOrder:
        new_tree = resolver.resolve_inverse_order_violation(src, dst)

    else:
        # no violation, keep original
        new_tree = resolver.get_tree()

    if new_tree is None:
        log("No resolution found.")
        return

    log("\n--- Result PST ---")
    log(new_tree.print_tree())

    log(f"\nDone in {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
