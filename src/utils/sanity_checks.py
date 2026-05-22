from lxml import etree as ET


# ============================================================
# HELPERS
# ============================================================

def contains_behavior(node):
    """
    Returns True if the node contains executable behavior.

    Supported executable elements:
    - call
    - terminate
    - choose
    - parallel
    - loop
    """

    executable_tags = (
        "call",
        "terminate",
        "choose",
        "parallel",
        "loop"
    )

    return any(
        elem.tag.endswith(executable_tags)
        for elem in node.iter()
    )


def build_parent_map(root):
    return {c: p for p in root.iter() for c in p}


# ============================================================
# REMOVE EMPTY PARALLEL BRANCHES
# ============================================================

def remove_empty_parallel_branches(root):

    parent_map = build_parent_map(root)

    for branch in list(root.iter()):

        if not branch.tag.endswith("parallel_branch"):
            continue

        if not contains_behavior(branch):

            parent = parent_map.get(branch)

            if parent is not None:
                parent.remove(branch)


# ============================================================
# REMOVE EMPTY XOR ALTERNATIVES
# ============================================================

def remove_empty_alternatives(root):

    parent_map = build_parent_map(root)

    for alt in list(root.iter()):

        if not alt.tag.endswith("alternative"):
            continue

        if not contains_behavior(alt):

            parent = parent_map.get(alt)

            if parent is not None:
                parent.remove(alt)


# ============================================================
# REMOVE EMPTY PARALLEL
# ============================================================

def remove_empty_parallel(root):

    parent_map = build_parent_map(root)

    for parallel in list(root.iter()):

        if not parallel.tag.endswith("parallel"):
            continue

        branches = [
            c for c in parallel
            if c.tag.endswith("parallel_branch")
        ]

        if len(branches) == 0:

            parent = parent_map.get(parallel)

            if parent is not None:
                parent.remove(parallel)


# ============================================================
# FLATTEN SINGLE-BRANCH PARALLEL
# ============================================================

def flatten_single_branch_parallel(root):

    parent_map = build_parent_map(root)

    for parallel in list(root.iter()):

        if not parallel.tag.endswith("parallel"):
            continue

        branches = [
            b for b in parallel
            if b.tag.endswith("parallel_branch")
        ]

        if len(branches) == 1:

            branch = branches[0]

            parent = parent_map.get(parallel)

            if parent is None:
                continue

            index = list(parent).index(parallel)

            # move all children of branch upward
            for child in list(branch):

                branch.remove(child)

                parent.insert(index, child)

                index += 1

            parent.remove(parallel)


# ============================================================
# SIMPLIFY XOR
# ============================================================

def simplify_choose(root):

    parent_map = build_parent_map(root)

    for choose in list(root.iter()):

        if not choose.tag.endswith("choose"):
            continue

        branches = [
            c for c in choose
            if c.tag.endswith(("alternative", "otherwise"))
        ]

        # only one branch remains
        if len(branches) == 1:

            surviving_branch = branches[0]

            parent = parent_map.get(choose)

            if parent is None:
                continue

            index = list(parent).index(choose)

            movable_children = [
                c for c in surviving_branch
                if not c.tag.endswith("_probability")
            ]

            for child in movable_children:

                surviving_branch.remove(child)

                parent.insert(index, child)

                index += 1

            parent.remove(choose)


# ============================================================
# FULL SANITIZER
# ============================================================

def sanitize_process(root):

    # --------------------------------------------
    # remove dead branches
    # --------------------------------------------

    remove_empty_parallel_branches(root)

    remove_empty_alternatives(root)

    # --------------------------------------------
    # remove dead containers
    # --------------------------------------------

    remove_empty_parallel(root)

    # --------------------------------------------
    # simplify structures
    # --------------------------------------------

    flatten_single_branch_parallel(root)

    simplify_choose(root)