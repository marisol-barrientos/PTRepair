def pst_to_dict(node):
    return {
        "label": node.label,
        "type": node.node_type,
        "branch_type": node.branch_type,
        "condition": node.condition,
        "resource": node.resource,
        "data": {
            "read": node.data.get("read", []),
            "write": node.data.get("write", [])
        } if node.data else {},
        "time": node.time,
        "loop": getattr(node, "loop", None),
        "parallel": getattr(node, "parallel", None),
        "children": [pst_to_dict(c) for c in node.children]
    }
def pst_to_text(node, indent=0):
    space = "  " * indent

    # --- label ---
    if node.node_type == "branch":
        label = node.branch_type
    else:
        label = node.label

    parts = [label]

    # --- condition ---
    if node.condition:
        parts.append(f"(cond: {node.condition})")

    # --- resource ---
    if node.resource:
        parts.append(f"(res: {', '.join(node.resource)})")

    # --- data ---
    if node.data:
        read = node.data.get("read", [])
        write = node.data.get("write", [])

        if read:
            parts.append(f"(read: {', '.join(read)})")
        if write:
            parts.append(f"(write: {', '.join(write)})")

    # --- parallel metadata ---
    if node.branch_type == "parallel" and node.parallel:
        wait = node.parallel.get("wait")
        cancel = node.parallel.get("cancel")

        if wait or cancel:
            parts.append(f"(wait={wait}, cancel={cancel})")

    # --- loop metadata ---
    if node.branch_type == "loop" and hasattr(node, "loop"):
        mode = node.loop.get("mode")
        cond = node.loop.get("condition")

        loop_parts = []
        if mode:
            loop_parts.append(f"mode={mode}")
        if cond:
            loop_parts.append(f"cond={cond}")

        if loop_parts:
            parts.append(f"({', '.join(loop_parts)})")

    # --- time ---
    if node.time is not None:
        parts.append(f"({node.time})")

    line = space + " ".join(parts) + "\n"

    # --- children (🔥 flatten trivial sequences) ---
    for child in node.children:

        # 🔥 flatten sequence with single child
        if (
            child.node_type == "branch"
            and child.branch_type == "sequence"
            and len(child.children) == 1
            and not child.condition
        ):
            line += pst_to_text(child.children[0], indent + 1)
        else:
            line += pst_to_text(child, indent + 1)

    return line