from simplified_pst.simplified_pst import PSTNode
from converter.data_extractor import extract_data_from_call
from utils.xml_utils import strip_ns
from utils.data_utils import parse_data_access


# ------------------------
# LEAF NODES
# ------------------------

def handle_call(node):
    tag = strip_ns(node.tag)

    # --- LABEL ---
    label = None

    if tag == "call":
        label_elem = node.find(".//{*}label")
        if label_elem is not None and label_elem.text:
            label = label_elem.text.strip()

    elif tag == "manipulate":
        label = node.attrib.get("label")

    if not label:
        label = node.attrib.get("id", "activity")

    # --- DATA ---
    data = extract_data_from_call(node)

    if tag == "manipulate":
        code_elem = node.find(".//{*}code")
        if code_elem is not None and code_elem.text:
            parsed = parse_data_access(code_elem.text)
            data["write"] = list(parsed.keys())

    # --- RESOURCE ---
    resource = extract_resource(node)

    # --- TIME / SPECIAL ENDPOINTS ---
    endpoint = node.attrib.get("endpoint")

    if endpoint == "timeout":
        timeout = node.find(".//{*}timeout")
        if timeout is not None and timeout.text:
            return PSTNode(
                label="timeout",
                node_type="activity",
                time=int(timeout.text),
                time_type="timeout"
            )

    elif endpoint == "wait_until":
        ts = node.find(".//{*}timestamp")
        value = ts.text.strip() if ts is not None and ts.text else None

        return PSTNode(
            label="wait_until",
            node_type="activity",
            time=value,
            time_type="wait_until"
        )

    elif endpoint == "sync":
        return PSTNode(
            label="sync",
            node_type="activity",
            data=data,
            time_type="sync"
        )

    elif endpoint == "due_date":
        ts = node.find(".//{*}timestamp")
        value = ts.text.strip() if ts is not None and ts.text else None

        return PSTNode(
            label="due_date",
            node_type="activity",
            time=value,
            data=data,
            time_type="due_date"
        )

    # --- DEFAULT ---
    return PSTNode(
        label=label,
        node_type="activity",
        data=data,
        resource=resource
    )


def handle_terminate(node):
    return PSTNode(label="terminate", node_type="activity")


# ------------------------
# BRANCH NODES
# ------------------------

def handle_parallel(node, convert):
    pst = PSTNode(
        label="parallel",
        node_type="branch",
        branch_type="parallel"
    )

    pst.parallel = {
        "wait": node.attrib.get("wait"),
        "cancel": node.attrib.get("cancel")
    }

    # --- convert branches ---
    for idx, child in enumerate(node):
        branch = convert(child)

        if branch and branch.node_type == "branch" and branch.branch_type == "sequence":
            branch.branch_id = f"par_{id(node)}_{idx}"
            pst.add_child(branch)
        elif branch:
            wrapper = PSTNode(
                label="sequence",
                node_type="branch",
                branch_type="sequence"
            )
            wrapper.branch_id = f"par_{id(node)}_{idx}"
            wrapper.add_child(branch)
            pst.add_child(wrapper)

    # 🔥 enrich time semantics
    enrich_time_semantics(pst)

    return pst


def handle_choose(node, convert):
    pst = PSTNode(
        label="exclusive",
        node_type="branch",
        branch_type="exclusive"
    )

    conditions = []
    branches = []

    for idx, child in enumerate(node):
        cond = child.attrib.get("condition")
        inner = convert(child)

        if inner and inner.node_type == "branch" and inner.branch_type == "sequence":
            wrapper = inner
        else:
            wrapper = PSTNode(
                label="sequence",
                node_type="branch",
                branch_type="sequence"
            )
            if inner:
                wrapper.add_child(inner)

        wrapper.branch_id = f"ex_{id(node)}_{idx}"

        branches.append((wrapper, cond))

        if cond:
            conditions.append(cond)

    for wrapper, cond in branches:
        if cond:
            wrapper.condition = cond
        else:
            if conditions:
                if len(conditions) == 1:
                    wrapper.condition = f"not ({conditions[0]})"
                else:
                    joined = " or ".join(f"({c})" for c in conditions)
                    wrapper.condition = f"not ({joined})"
            else:
                wrapper.condition = None

        pst.add_child(wrapper)

    return pst


def handle_loop(node, convert):
    mode = node.attrib.get("mode")
    condition = node.attrib.get("condition")

    pst = PSTNode(
        label="loop",
        node_type="branch",
        branch_type="loop"
    )

    pst.loop = {
        "mode": mode,
        "condition": condition
    }

    pst.condition = condition

    for child in node:
        converted = convert(child)
        if converted:
            pst.add_child(converted)

    return pst


# ------------------------
# RESOURCE EXTRACTION
# ------------------------

def extract_resource(node):
    resources = []

    resource_tag = node.find(".//{*}Resource")
    if resource_tag is not None and resource_tag.text:
        text = resource_tag.text.strip()
        resources = [r.strip() for r in text.split(",") if r.strip()]

    return resources


# ------------------------
# TIME SEMANTICS (🔥 NEW)
# ------------------------

def find_timeout(node):
    if node.node_type == "activity" and node.time_type == "timeout":
        return node

    for child in node.children:
        result = find_timeout(child)
        if result:
            return result

    return None


def collect_activity_labels(node):
    labels = []

    if node.node_type == "activity" and node.label not in {"timeout", "wait_until"}:
        labels.append(node.label)

    for child in node.children:
        labels.extend(collect_activity_labels(child))

    return labels


def find_next_activity_after_timeout(node):
    found = False

    def dfs(n):
        nonlocal found

        if n.node_type == "activity" and n.time_type == "timeout":
            found = True
            return None

        if found and n.node_type == "activity" and n.time_type != "timeout":
            return n

        for c in n.children:
            result = dfs(c)
            if result:
                return result

        return None

    return dfs(node)


def enrich_time_semantics(parallel_node):
    if not parallel_node.parallel:
        return

    cancel_mode = parallel_node.parallel.get("cancel")

    if cancel_mode not in {"first", "last"}:
        return

    for branch in parallel_node.children:
        timeout = find_timeout(branch)

        if not timeout:
            continue

        # --- affects ---
        for other in parallel_node.children:
            if other != branch:
                timeout.time_links["affects"].extend(
                    collect_activity_labels(other)
                )

        # --- triggers ---
        next_act = find_next_activity_after_timeout(branch)

        if next_act:
            timeout.time_links["triggers"] = next_act.label