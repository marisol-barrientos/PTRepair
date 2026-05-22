from converter.mapping import LEAF_TAGS
from converter import transformer
from simplified_pst.simplified_pst import PSTNode


def strip_ns(tag):
    return tag.split("}")[-1]


def convert(node):
    tag = strip_ns(node.tag)

    # --- LEAF ---
    if tag in LEAF_TAGS:
        return transformer.handle_call(node)

    # --- BRANCHES ---
    elif tag == "parallel":
        return transformer.handle_parallel(node, convert)

    elif tag == "choose":
        return transformer.handle_choose(node, convert)

    elif tag == "loop":
        return transformer.handle_loop(node, convert)

    elif tag == "terminate":
        return transformer.handle_terminate(node)

    # --- STRUCTURAL WRAPPERS (IGNORE BUT KEEP CHILDREN) ---
    elif tag in {"parallel_branch", "alternative", "otherwise", "description"}:
        children = [convert(c) for c in node]
        children = [c for c in children if c]

        if not children:
            return None

        if len(children) == 1:
            return children[0]

        # multiple children → sequence
        seq = PSTNode(label="sequence", node_type="branch", branch_type="sequence")
        for c in children:
            seq.add_child(c)

        return seq

    # --- DEFAULT ---
    else:
        children = [convert(c) for c in node]
        children = [c for c in children if c]

        if not children:
            return None

        if len(children) == 1:
            return children[0]

        seq = PSTNode(label="sequence", node_type="branch", branch_type="sequence")
        for c in children:
            seq.add_child(c)

        return seq