from utils.change_operations_utils import get_label, find_unique_by_label
import xml.etree.ElementTree as ET
from lxml import etree as ET
import copy
import uuid


NS = {
    "p": "http://cpee.org/ns/properties/2.0",
    "d": "http://cpee.org/ns/description/1.0"
}



def insert_after(
    root,
    target_activity_label,
    new_activity_label
):
    """
    Insert a new activity after an existing activity.
    """

    target = find_unique_by_label(
        root,
        target_activity_label
    )

    # ---------------------------------------------------
    # create new activity node
    # ---------------------------------------------------

    new_id = f"n_{uuid.uuid4().hex[:6]}"

    new_node = clone_call_template(
        root,
        new_id,
        new_activity_label
    )

    # ---------------------------------------------------
    # insert node
    # ---------------------------------------------------

    parent_map = {c: p for p in root.iter() for c in p}

    parent = parent_map[target]

    index = list(parent).index(target)

    parent.insert(index + 1, new_node)

    return {
        "type": "insert_after",
        "target_activity": target_activity_label,
        "new_activity": new_activity_label
    }

def insert_before(
    root,
    target_activity_label,
    new_activity_label
):
    """
    Insert a new activity before an existing activity.
    """

    target = find_unique_by_label(
        root,
        target_activity_label
    )

    # ---------------------------------------------------
    # create new activity node
    # ---------------------------------------------------

    new_id = f"n_{uuid.uuid4().hex[:6]}"

    new_node = clone_call_template(
        root,
        new_id,
        new_activity_label
    )

    # ---------------------------------------------------
    # insert node
    # ---------------------------------------------------

    parent_map = {c: p for p in root.iter() for c in p}

    parent = parent_map[target]

    index = list(parent).index(target)

    parent.insert(index, new_node)

    return {
        "type": "insert_before",
        "target_activity": target_activity_label,
        "new_activity": new_activity_label
    }

def delete(root, target_activity_label):

    target = find_unique_by_label(root, target_activity_label)

    parent_map = {c: p for p in root.iter() for c in p}
    parent = parent_map[target]

    parent.remove(target)

    return {
        "type": "delete",
        "target_activity_label": target_activity_label
    }


def rename(root, target_activity_label, new_activity_label):
    node = find_unique_by_label(root, target_activity_label)

    # Case 1: simple attribute-based label
    if "label" in node.attrib:
        node.attrib["label"] = new_activity_label
    else:
        # Case 2: CPEE structure (parameters/label)
        label_elem = node.find(".//{*}parameters/{*}label")
        if label_elem is not None:
            label_elem.text = new_activity_label
        else:
            raise ValueError(f"Node with label '{target_activity_label}' has no editable label")

    return {
        "type": "rename",
        "target_activity_label": target_activity_label,
        "new_activity_label": new_activity_label
    }

def move_after(root, source_activity_label, target_activity_label):
    source = find_unique_by_label(root, source_activity_label)
    target = find_unique_by_label(root, target_activity_label)

    parent_map = {c: p for p in root.iter() for c in p}

    source_parent = parent_map[source]
    target_parent = parent_map[target]

    # Remove source from its current position
    source_parent.remove(source)

    # Recompute parent map (structure changed)
    parent_map = {c: p for p in root.iter() for c in p}
    target_parent = parent_map[target]

    index = list(target_parent).index(target)
    target_parent.insert(index + 1, source)

    return {
        "type": "move_after",
        "source_activity_label": source_activity_label,
        "target_activity_label": target_activity_label
    }

def move_before(root, source_activity_label, target_activity_label):
    source = find_unique_by_label(root, source_activity_label)
    target = find_unique_by_label(root, target_activity_label)

    parent_map = {c: p for p in root.iter() for c in p}

    source_parent = parent_map[source]
    target_parent = parent_map[target]

    # Remove source first
    source_parent.remove(source)

    # Recompute parent map
    parent_map = {c: p for p in root.iter() for c in p}
    target_parent = parent_map[target]

    index = list(target_parent).index(target)
    target_parent.insert(index, source)

    return {
        "type": "move_before",
        "source_activity_label": source_activity_label,
        "target_activity_label": target_activity_label
    }

def swap(root, first_activity_label, second_activity_label):
    node_a = find_unique_by_label(root, first_activity_label)
    node_b = find_unique_by_label(root, second_activity_label)

    if node_a == node_b:
        return {
            "type": "swap",
            "nodes": (first_activity_label, second_activity_label),
            "note": "same node, no-op"
        }

    parent_map = {c: p for p in root.iter() for c in p}

    parent_a = parent_map[node_a]
    parent_b = parent_map[node_b]

    index_a = list(parent_a).index(node_a)
    index_b = list(parent_b).index(node_b)

    # Case 1: same parent → simple swap
    if parent_a == parent_b:
        parent = parent_a
        children = list(parent)

        children[index_a], children[index_b] = children[index_b], children[index_a]

        # rewrite children
        parent[:] = children

    else:
        # Case 2: different parents → remove and reinsert
        parent_a.remove(node_a)
        parent_b.remove(node_b)

        parent_a.insert(index_a, node_b)
        parent_b.insert(index_b, node_a)

    return {
        "type": "swap",
        "first_activity_label": first_activity_label,
        "second_activity_label": second_activity_label
    }


def normalize_node(node):
    node_copy = copy.deepcopy(node)

    # --- Remove volatile attributes ---
    for elem in node_copy.iter():
        # remove IDs
        if "id" in elem.attrib:
            del elem.attrib["id"]

    # --- Remove label (since merge changes it) ---
    for label in node_copy.findall(".//{*}label"):
        label.text = ""

    # --- Optional: remove annotations (often irrelevant for equality) ---
    for ann in node_copy.findall(".//{*}annotations"):
        parent = _get_parent(node_copy, ann)
        if parent is not None:
            parent.remove(ann)

    # --- Normalize whitespace ---
    for elem in node_copy.iter():
        if elem.text:
            elem.text = elem.text.strip()
        if elem.tail:
            elem.tail = elem.tail.strip()

    # --- Canonical string ---
    return ET.tostring(node_copy, encoding="utf-8")

def set_label(node, new_label):
    # Case 1: attribute label
    if "label" in node.attrib:
        node.attrib["label"] = new_label
        return

    # Case 2: CPEE structure
    label_elem = node.find(".//{*}parameters/{*}label")
    if label_elem is not None:
        label_elem.text = new_label
        return

    raise ValueError("Node has no label field")


def merge_by_label(root, first_activity_label, second_activity_label, keep="first"):
    node_a = find_unique_by_label(root, first_activity_label)
    node_b = find_unique_by_label(root, second_activity_label)

    # --- Optional: compatibility check (you already have this) ---
    if normalize_node(node_a) != normalize_node(node_b):
        raise ValueError(
            f"Cannot merge '{first_activity_label}' and '{second_activity_label}': structures differ"
        )

    parent_map = {c: p for p in root.iter() for c in p}

    parent_a = parent_map[node_a]
    parent_b = parent_map[node_b]

    # --- Decide which one to keep ---
    if keep == "first":
        keep_node = node_a
        remove_node = node_b
        remove_parent = parent_b
        base_label = first_activity_label
        other_label = second_activity_label
    elif keep == "second":
        keep_node = node_b
        remove_node = node_a
        remove_parent = parent_a
        base_label = second_activity_label
        other_label = first_activity_label
    else:
        raise ValueError("keep must be 'first' or 'second'")

    # --- Combine labels ---
    new_label = f"{base_label} and {other_label}"
    set_label(keep_node, new_label)

    # --- Remove the other node ---
    remove_parent.remove(remove_node)

    return {
        "type": "merge",
        "first_activity_label": first_activity_label,
        "second_activity_label": second_activity_label,
        "merged_activity_label": new_label,
        "keep_position": keep
    }

def _get_parent(root, child):
    for parent in root.iter():
        for c in parent:
            if c is child:
                return parent
    return None


def split(root, target_activity_label):
    target = find_unique_by_label(root, target_activity_label)

    # --- get label element ---
    label_elem = target.find(".//{*}label")
    if label_elem is None or "and" not in label_elem.text:
        raise ValueError(f"Label '{target_activity_label}' cannot be split")

    full_label = label_elem.text
    part1, part2 = [p.strip() for p in full_label.split("and", 1)]

    # --- create two copies ---
    node1 = copy.deepcopy(target)
    node2 = copy.deepcopy(target)

    # --- assign new labels ---
    node1.find(".//{*}label").text = part1
    node2.find(".//{*}label").text = part2

    # --- assign new IDs ---
    import uuid
    node1.attrib["id"] = f"n_{uuid.uuid4().hex[:6]}"
    node2.attrib["id"] = f"n_{uuid.uuid4().hex[:6]}"

    # --- replace original node ---
    parent_map = {c: p for p in root.iter() for c in p}
    parent = parent_map[target]

    index = list(parent).index(target)

    parent.remove(target)
    parent.insert(index, node1)
    parent.insert(index + 1, node2)

    return {
        "type": "split",
        "target_activity_label": full_label,
        "new_activity_labels": [part1, part2]
    }

def modify_condition(root, target_activity_label, new_condition):
    target = find_unique_by_label(root, target_activity_label)

    parent_map = {c: p for p in root.iter() for c in p}

    # --- climb up until we find an alternative ---
    current = target
    alternative = None

    while current in parent_map:
        current = parent_map[current]
        if current.tag.endswith("alternative"):
            alternative = current
            break

    if alternative is None:
        raise ValueError(f"No enclosing <alternative> found for '{target_activity_label}'")

    old_condition = alternative.attrib.get("condition")

    # --- update condition ---
    alternative.set("condition", new_condition)

    return {
        "type": "modify_condition",
        "target_activity_label": target_activity_label,
        "old_condition": old_condition,
        "new_condition": new_condition
    }

def copy_after(root, source_activity_label, target_activity_label):
    source = find_unique_by_label(root, source_activity_label)
    target = find_unique_by_label(root, target_activity_label)

    # --- deep copy ---
    new_node = copy.deepcopy(source)

    # --- assign new ID ---
    new_node.attrib["id"] = f"n_{uuid.uuid4().hex[:6]}"

    parent_map = {c: p for p in root.iter() for c in p}
    parent = parent_map[target]

    index = list(parent).index(target)
    parent.insert(index + 1, new_node)

    return {
        "type": "copy_after",
        "source_activity_label": source_activity_label,
        "target_activity_label": target_activity_label,
        "copied_activity_label": get_label(new_node)
    }

def copy_before(root, source_activity_label, target_activity_label):
    source = find_unique_by_label(root, source_activity_label)
    target = find_unique_by_label(root, target_activity_label)

    # --- deep copy ---
    new_node = copy.deepcopy(source)

    # --- assign new ID ---
    new_node.attrib["id"] = f"n_{uuid.uuid4().hex[:6]}"

    parent_map = {c: p for p in root.iter() for c in p}
    parent = parent_map[target]

    index = list(parent).index(target)
    parent.insert(index, new_node)

    return {
        "type": "copy_before",
        "source_activity_label": source_activity_label,
        "target_activity_label": target_activity_label,
        "new_node": get_label(new_node)
    }

def modify_resource(
    root,
    target_activity_label,
    new_resource
):

    node = find_unique_by_label(
        root,
        target_activity_label
    )

    # ---------------------------------------------------
    # find or create annotations
    # ---------------------------------------------------

    annotations = node.find(
        "./{*}annotations"
    )

    if annotations is None:

        annotations = ET.SubElement(
            node,
            "annotations"
        )

    # ---------------------------------------------------
    # find or create _generic
    # ---------------------------------------------------

    generic = annotations.find(
        "./{*}_generic"
    )

    if generic is None:

        generic = ET.SubElement(
            annotations,
            "_generic"
        )

    # ---------------------------------------------------
    # find or create Resource
    # ---------------------------------------------------

    resource_elem = generic.find(
        "./{*}Resource"
    )

    if resource_elem is None:

        resource_elem = ET.SubElement(
            generic,
            "Resource"
        )

        old_resource = None

    else:

        old_resource = resource_elem.text

    # ---------------------------------------------------
    # update resource
    # ---------------------------------------------------

    resource_elem.text = new_resource

    return {
        "type": "modify_resource",
        "target_activity_label":
            target_activity_label,
        "old_resource":
            old_resource,
        "new_resource":
            new_resource
    }

def modify_write(root, target_activity_label, new_statement):
    node = find_unique_by_label(root, target_activity_label)

    finalize = node.find(".//{*}code/{*}finalize")
    if finalize is None:
        raise ValueError(f"No <finalize> block in '{target_activity_label}'")

    old = finalize.text
    finalize.text = new_statement

    return {
        "type": "modify_write",
        "target_activity_label": target_activity_label,
        "old_statement": old,
        "new_statement": new_statement
    }

def add_write(
    root,
    target_activity_label,
    new_statement
):

    node = find_unique_by_label(
        root,
        target_activity_label
    )

    # ---------------------------------------------------------
    # ensure <code>
    # ---------------------------------------------------------

    code = node.find("./{*}code")

    if code is None:

        code = ET.SubElement(
            node,
            "code"
        )

    # ---------------------------------------------------------
    # ensure <finalize>
    # ---------------------------------------------------------

    finalize = code.find("./{*}finalize")

    if finalize is None:

        finalize = ET.SubElement(
            code,
            "finalize"
        )

        finalize.text = ""

    # ---------------------------------------------------------
    # append statement
    # ---------------------------------------------------------

    old = finalize.text or ""

    finalize.text = (
        old
        + "\n"
        + new_statement
    ).strip()

    return {
        "type": "add_write",
        "target_activity_label":
            target_activity_label,
        "added_statement":
            new_statement
    }

def remove_write(root, target_activity_label, variable_name):
    node = find_unique_by_label(root, target_activity_label)

    finalize = node.find(".//{*}code/{*}finalize")
    if finalize is None or not finalize.text:
        return

    lines = finalize.text.split("\n")
    lines = [l for l in lines if variable_name not in l]

    finalize.text = "\n".join(lines)

    return {
        "type": "remove_write",
        "target_activity_label": target_activity_label,
        "removed_variable_name": variable_name
    }

def modify_read(root, target_activity_label, old_variable_name, new_variable_name):
    node = find_unique_by_label(root, target_activity_label)

    code_block = node.find(".//{*}code")
    if code_block is None:
        return

    for elem in code_block.iter():
        if elem.text:
            elem.text = elem.text.replace(old_variable_name, new_variable_name)

    return {
        "type": "modify_read",
        "target_activity_label": target_activity_label,
        "old_variable_name": old_variable_name,
        "new_variable_name": new_variable_name
    }


def get_process_description(root):
    """
    Returns the INNER process description node:
    <description xmlns="http://cpee.org/ns/description/1.0">
    """

    desc = root.xpath(
        "./p:description/d:description",
        namespaces=NS
    )

    if not desc:
        raise ValueError("Process description not found")

    return desc[0]


def parallelize(root, first_activity_label, second_activity_label):

    process_root = get_process_description(root)

    node_a = find_unique_by_label(process_root, first_activity_label)
    node_b = find_unique_by_label(process_root, second_activity_label)

    parent = node_a.getparent()

    if parent is not node_b.getparent():
        raise ValueError("Activities must share same parent")

    children = list(parent)

    idx_a = children.index(node_a)
    idx_b = children.index(node_b)

    # normalize ordering
    if idx_a > idx_b:
        node_a, node_b = node_b, node_a
        idx_a, idx_b = idx_b, idx_a

    if idx_b != idx_a + 1:
        raise ValueError("Activities are not consecutive")

    ns = "{http://cpee.org/ns/description/1.0}"

    # create nested parallel
    parallel = ET.Element(
        f"{ns}parallel",
        wait="-1",
        cancel="last"
    )

    branch1 = ET.Element(f"{ns}parallel_branch")
    branch2 = ET.Element(f"{ns}parallel_branch")

    branch1.append(copy.deepcopy(node_a))
    branch2.append(copy.deepcopy(node_b))

    parallel.append(branch1)
    parallel.append(branch2)

    # insert parallel before first node
    parent.insert(idx_a, parallel)

    # remove originals
    parent.remove(node_a)
    parent.remove(node_b)

    return {
        "type": "parallelize",
        "first_activity_label": first_activity_label,
        "second_activity_label": second_activity_label
    }

def get_parallel_branch(node):

    current = node

    while current is not None:

        if ET.QName(current).localname == "parallel_branch":
            return current

        current = current.getparent()

    return None


def get_parallel(branch):

    parent = branch.getparent()

    if parent is None:
        return None

    if ET.QName(parent).localname == "parallel":
        return parent

    return None


def sequentialize_parallel(root, first_activity_label, second_activity_label):
    """
    Converts two parallel branches into a sequence.

    Examples:

    Branch1: A
    Branch2: B
    =>
    A -> B

    Branch1: L -> A
    Branch2: B -> K
    =>
    L -> A -> B -> K

    Branch1: A
    Branch2: B
    Branch3: C
    =>
    parallel(
        branch1: A -> B
        branch2: C
    )
    """

    process_root = get_process_description(root)

    node_a = find_unique_by_label(process_root, first_activity_label)
    node_b = find_unique_by_label(process_root, second_activity_label)

    branch_a = get_parallel_branch(node_a)
    branch_b = get_parallel_branch(node_b)

    if branch_a is None or branch_b is None:
        raise ValueError("Activities are not inside parallel branches")

    if branch_a is branch_b:
        raise ValueError("Activities already in same branch")

    parallel = get_parallel(branch_a)

    if parallel is None or parallel is not get_parallel(branch_b):
        raise ValueError("Activities are not in same parallel")

    # ---------------------------------------------------
    # move all content from branch_b into branch_a
    # ---------------------------------------------------

    children_b = list(branch_b)

    for child in children_b:
        branch_b.remove(child)
        branch_a.append(child)

    # ---------------------------------------------------
    # remove empty branch_b
    # ---------------------------------------------------

    parallel.remove(branch_b)

    # ---------------------------------------------------
    # if only one branch remains, flatten parallel
    # ---------------------------------------------------

    remaining_branches = [
        c for c in parallel
        if ET.QName(c).localname == "parallel_branch"
    ]

    if len(remaining_branches) == 1:

        surviving_branch = remaining_branches[0]

        parallel_parent = parallel.getparent()

        parallel_index = parallel_parent.index(parallel)

        surviving_children = list(surviving_branch)

        # remove parallel
        parallel_parent.remove(parallel)

        # insert children directly
        for i, child in enumerate(surviving_children):
            surviving_branch.remove(child)
            parallel_parent.insert(parallel_index + i, child)

    return {
        "type": "sequentialize_parallel",
        "first_activity_label": first_activity_label,
        "second_activity_label": second_activity_label
    }

def clone_call_template(root, new_id, new_label):

    process_root = get_process_description(root)

    template = process_root.xpath(".//d:call", namespaces=NS)

    if not template:
        raise ValueError("No call template found")

    template = template[0]

    new_call = copy.deepcopy(template)

    new_call.set("id", new_id)
    new_call.set("endpoint", "")

    label_elem = new_call.xpath(
        "./d:parameters/d:label",
        namespaces=NS
    )[0]

    label_elem.text = new_label

    return new_call


def find_following_xor_old(activity_node):

    parent = activity_node.getparent()

    if parent is None:
        return None

    children = list(parent)

    idx = children.index(activity_node)

    for child in children[idx + 1:]:

        if ET.QName(child).localname == "choose":
            return child

    return None


def find_xor_by_condition(root, condition):

    process_root = get_process_description(root)

    xors = process_root.xpath(".//d:choose", namespaces=NS)

    for xor in xors:

        alternatives = xor.xpath(
            "./d:alternative",
            namespaces=NS
        )

        for alt in alternatives:

            if alt.get("condition") == condition:
                return xor

    raise ValueError(
        f"No XOR found containing condition '{condition}'"
    )


def add_xor_branch(
    root,
    existing_branch_condition,
    new_branch_condition,
    new_activity_label
):
    """
    Adds a new alternative branch to an existing XOR.

    existing_branch_condition:
        identifies WHICH xor to modify

    new_branch_condition:
        condition of the NEW branch
    """

    xor = find_xor_by_condition(root, existing_branch_condition)

    ns = "{http://cpee.org/ns/description/1.0}"

    # --------------------------------------------
    # create alternative
    # --------------------------------------------

    alternative = ET.Element(
        f"{ns}alternative",
        condition=new_branch_condition
    )

    probability = ET.Element(f"{ns}_probability")

    ET.SubElement(probability, f"{ns}_probability_min")
    ET.SubElement(probability, f"{ns}_probability_max")
    ET.SubElement(probability, f"{ns}_probability_avg")

    alternative.append(probability)

    # --------------------------------------------
    # create call
    # --------------------------------------------

    new_id = f"n_{uuid.uuid4().hex[:6]}"

    new_call = clone_call_template(
        root,
        new_id,
        new_activity_label
    )

    alternative.append(new_call)

    # --------------------------------------------
    # insert before otherwise
    # --------------------------------------------

    otherwise = xor.xpath("./d:otherwise", namespaces=NS)

    if otherwise:
        xor.insert(
            xor.index(otherwise[0]),
            alternative
        )
    else:
        xor.append(alternative)

    return {
        "type": "add_xor_branch",
        "existing_branch_condition": existing_branch_condition,
        "new_branch_condition": new_branch_condition,
        "new_activity_label": new_activity_label
    }


def remove_branch(root, target_activity_label):
    """
    Removes the ENTIRE branch containing the activity.

    Supported:
    - parallel_branch
    - XOR alternative
    - otherwise branch

    If removing a parallel branch leaves only one branch,
    the parallel is flattened automatically.
    """

    process_root = get_process_description(root)

    target = find_unique_by_label(
        process_root,
        target_activity_label
    )

    current = target

    branch = None

    while current is not None:

        tag = ET.QName(current).localname

        if tag in ["parallel_branch", "alternative", "otherwise"]:
            branch = current
            break

        current = current.getparent()

    if branch is None:
        raise ValueError(
            f"No removable branch found for '{target_activity_label}'"
        )

    parent = branch.getparent()

    branch_type = ET.QName(branch).localname

    # ---------------------------------------------------
    # remove branch
    # ---------------------------------------------------

    parent.remove(branch)

    # ---------------------------------------------------
    # flatten parallel if only one branch remains
    # ---------------------------------------------------

    if ET.QName(parent).localname == "parallel":

        remaining = [
            c for c in parent
            if ET.QName(c).localname == "parallel_branch"
        ]

        if len(remaining) == 1:

            surviving_branch = remaining[0]

            parallel_parent = parent.getparent()

            parallel_index = parallel_parent.index(parent)

            surviving_children = list(surviving_branch)

            parallel_parent.remove(parent)

            for i, child in enumerate(surviving_children):

                surviving_branch.remove(child)

                parallel_parent.insert(
                    parallel_index + i,
                    child
                )

    # ---------------------------------------------------
    # remove empty XOR
    # ---------------------------------------------------

    if ET.QName(parent).localname == "choose":

        alternatives = [
            c for c in parent
            if ET.QName(c).localname in [
                "alternative",
                "otherwise"
            ]
        ]

        if len(alternatives) == 0:

            choose_parent = parent.getparent()

            choose_parent.remove(parent)

    return {
        "type": "remove_branch",
        "target_activity_label": target_activity_label,
        "removed_branch_type": branch_type
    }

def remove_branch_by_condition(root, target_condition):
    """
    Removes an XOR alternative branch by its target_condition.

    Example:
        remove target_condition:
        data.assessment_status == "rejected"

    Handles:
    - flattening XORs with one remaining branch
    - removing empty XORs
    """

    process_root = get_process_description(root)

    alternatives = process_root.xpath(
        ".//d:alternative",
        namespaces=NS
    )

    target = None

    for alt in alternatives:

        if alt.get("condition") == target_condition:
            target = alt
            break

    if target is None:
        raise ValueError(
            f"No alternative found with target_condition '{target_condition}'"
        )

    choose = target.getparent()

    if ET.QName(choose).localname != "choose":
        raise ValueError("Target alternative is not inside choose")

    # ---------------------------------------------------
    # remove target branch
    # ---------------------------------------------------

    choose.remove(target)

    remaining = [
        c for c in choose
        if ET.QName(c).localname in [
            "alternative",
            "otherwise"
        ]
    ]

    # ---------------------------------------------------
    # remove empty choose
    # ---------------------------------------------------

    if len(remaining) == 0:

        choose_parent = choose.getparent()

        choose_parent.remove(choose)

    # ---------------------------------------------------
    # flatten XOR with single remaining branch
    # ---------------------------------------------------

    elif len(remaining) == 1:

        surviving = remaining[0]

        choose_parent = choose.getparent()

        choose_index = choose_parent.index(choose)

        surviving_children = list(surviving)

        choose_parent.remove(choose)

        for i, child in enumerate(surviving_children):

            surviving.remove(child)

            choose_parent.insert(
                choose_index + i,
                child
            )

    return {
        "type": "remove_branch_by_condition",
        "target_condition": target_condition
    }

def embed_activity_in_xor(
    root,
    target_activity_label,
    condition,
    mode="skip",
    alternative_activity_label=None
):
    """
    Wraps an activity into a new XOR.

    Modes:

    mode="skip"
        condition -> original activity
        otherwise -> skip activity

    mode="terminate"
        condition -> original activity
        otherwise -> terminate

    mode="alternative_activity"
        condition -> original activity
        otherwise -> alternative activity
    """

    process_root = get_process_description(root)

    activity = find_unique_by_label(
        process_root,
        target_activity_label
    )

    parent = activity.getparent()

    index = parent.index(activity)

    ns = "{http://cpee.org/ns/description/1.0}"

    # ---------------------------------------------------
    # create choose
    # ---------------------------------------------------

    choose = ET.Element(
        f"{ns}choose",
        mode="exclusive"
    )

    # ---------------------------------------------------
    # alternative branch
    # ---------------------------------------------------

    alternative = ET.Element(
        f"{ns}alternative",
        condition=condition
    )

    probability = ET.Element(f"{ns}_probability")

    ET.SubElement(probability, f"{ns}_probability_min")
    ET.SubElement(probability, f"{ns}_probability_max")
    ET.SubElement(probability, f"{ns}_probability_avg")

    alternative.append(probability)

    # move original activity
    parent.remove(activity)

    alternative.append(activity)

    choose.append(alternative)

    # ---------------------------------------------------
    # otherwise branch
    # ---------------------------------------------------

    otherwise = ET.Element(f"{ns}otherwise")

    # ----------------------------------------
    # skip
    # ----------------------------------------

    if mode == "skip":
        pass

    # ----------------------------------------
    # terminate
    # ----------------------------------------

    elif mode == "terminate":

        terminate = ET.Element(f"{ns}terminate")

        otherwise.append(terminate)

    # ----------------------------------------
    # alternative activity
    # ----------------------------------------

    elif mode == "alternative_activity":

        if alternative_activity_label is None:
            raise ValueError(
                "alternative_activity_label required"
            )

        new_id = f"n_{uuid.uuid4().hex[:6]}"

        alternative_call = clone_call_template(
            root,
            new_id,
            alternative_activity_label
        )

        otherwise.append(alternative_call)

    else:
        raise ValueError(f"Unknown mode: {mode}")

    choose.append(otherwise)

    # ---------------------------------------------------
    # insert XOR
    # ---------------------------------------------------

    parent.insert(index, choose)

    return {
        "type": "embed_activity_in_xor",
        "target_activity_label": target_activity_label,
        "condition": condition,
        "mode": mode
    }

# ============================================================
# PRE-CONDITION LOOP
# ============================================================

def embed_pre_loop(
    root,
    start_activity_label,
    end_activity_label,
    condition
):
    """
    Wraps a fragment inside a PRE-condition loop.

    WHILE condition:
        fragment

    The loop checks the condition BEFORE execution.
    """

    process_root = get_process_description(root)

    start_node = find_unique_by_label(process_root, start_activity_label)
    end_node = find_unique_by_label(process_root, end_activity_label)

    parent = start_node.getparent()

    if parent is not end_node.getparent():
        raise ValueError(
            "Fragment boundaries must share same parent"
        )

    children = list(parent)

    start_idx = children.index(start_node)
    end_idx = children.index(end_node)

    if start_idx > end_idx:
        raise ValueError(
            "start activity must appear before end activity"
        )

    ns = "{http://cpee.org/ns/description/1.0}"

    # -------------------------------------------------------
    # create loop
    # -------------------------------------------------------

    loop = ET.Element(
        f"{ns}loop",
        mode="pre_test",
        condition=condition
    )

    # -------------------------------------------------------
    # move fragment into loop
    # -------------------------------------------------------

    fragment = children[start_idx:end_idx + 1]

    for node in fragment:
        parent.remove(node)
        loop.append(node)

    # -------------------------------------------------------
    # insert loop
    # -------------------------------------------------------

    parent.insert(start_idx, loop)

    return {
        "type": "embed_pre_loop",
        "start_activity_label": start_activity_label,
        "end_activity_label": end_activity_label,
        "condition": condition
    }


# ============================================================
# POST-CONDITION LOOP
# ============================================================

def embed_post_loop(
    root,
    start_activity_label,
    end_activity_label,
    condition
):
    """
    Wraps a fragment inside a POST-condition loop.

    DO:
        fragment
    WHILE condition

    The loop checks condition AFTER execution.
    """

    process_root = get_process_description(root)

    start_node = find_unique_by_label(process_root, start_activity_label)
    end_node = find_unique_by_label(process_root, end_activity_label)

    parent = start_node.getparent()

    if parent is not end_node.getparent():
        raise ValueError(
            "Fragment boundaries must share same parent"
        )

    children = list(parent)

    start_idx = children.index(start_node)
    end_idx = children.index(end_node)

    if start_idx > end_idx:
        raise ValueError(
            "start activity must appear before end activity"
        )

    ns = "{http://cpee.org/ns/description/1.0}"

    # -------------------------------------------------------
    # create loop
    # -------------------------------------------------------

    loop = ET.Element(
        f"{ns}loop",
        mode="post_test",
        condition=condition
    )

    # -------------------------------------------------------
    # move fragment
    # -------------------------------------------------------

    fragment = children[start_idx:end_idx + 1]

    for node in fragment:
        parent.remove(node)
        loop.append(node)

    # -------------------------------------------------------
    # insert loop
    # -------------------------------------------------------

    parent.insert(start_idx, loop)

    return {
        "type": "embed_post_loop",
        "start_activity_label": start_activity_label,
        "end_activity_label": end_activity_label,
        "condition": condition
    }

def local_name(elem):
    return elem.tag.split("}")[-1]

def remove_loop(root, target_activity_label):

    process_root = get_process_description(root)

    activity = find_unique_by_label(
        process_root,
        target_activity_label
    )

    current = activity
    loop = None

    # ---------------------------------------------------
    # find surrounding loop
    # ---------------------------------------------------

    while current is not None:

        if local_name(current) == "loop":
            loop = current
            break

        current = current.getparent()

    if loop is None:
        raise ValueError(
            f"No surrounding loop found for '{target_activity_label}'"
        )

    parent = loop.getparent()

    loop_index = parent.index(loop)

    loop_children = list(loop)

    # ---------------------------------------------------
    # remove loop wrapper
    # ---------------------------------------------------

    parent.remove(loop)

    # ---------------------------------------------------
    # flatten loop contents
    # ---------------------------------------------------

    for i, child in enumerate(loop_children):

        loop.remove(child)

        parent.insert(loop_index + i, child)

    return {
        "type": "remove_loop",
        "target_activity_label": target_activity_label
    }

def modify_loop_condition(
    root,
    target_activity_label,
    new_condition
):
    """
    Finds the nearest surrounding loop
    containing the activity and updates
    its condition.

    Works for:
    - pre_test loops
    - post_test loops
    """

    process_root = get_process_description(root)

    activity = find_unique_by_label(
        process_root,
        target_activity_label
    )

    current = activity
    loop = None

    # ---------------------------------------------------
    # find surrounding loop
    # ---------------------------------------------------

    while current is not None:

        if local_name(current) == "loop":
            loop = current
            break

        current = current.getparent()

    if loop is None:
        raise ValueError(
            f"No surrounding loop found for '{target_activity_label}'"
        )

    old_condition = loop.get("condition")

    # ---------------------------------------------------
    # update condition
    # ---------------------------------------------------

    loop.set("condition", new_condition)

    return {
        "type": "modify_loop_condition",
        "target_activity_label": target_activity_label,
        "old_condition": old_condition,
        "new_condition": new_condition
    }

def modify_timeout(
    root,
    target_activity_label,
    new_timeout
):
    """
    Modifies the timeout value of a timeout activity.

    Example:
        modify timeout from 900 to 1200

    Works on activities like:
        <call endpoint="timeout">
            ...
            <timeout>900</timeout>
    """

    process_root = get_process_description(root)

    activity = find_unique_by_label(
        process_root,
        target_activity_label
    )

    # ---------------------------------------------------
    # validate timeout activity
    # ---------------------------------------------------

    endpoint = activity.get("endpoint")

    if endpoint != "timeout":
        raise ValueError(
            f"Activity '{target_activity_label}' is not a timeout activity"
        )

    # ---------------------------------------------------
    # find timeout element
    # ---------------------------------------------------

    timeout_elem = activity.find(
        ".//{*}arguments/{*}timeout"
    )

    if timeout_elem is None:
        raise ValueError(
            f"No <timeout> element found in '{target_activity_label}'"
        )

    old_timeout = timeout_elem.text

    # ---------------------------------------------------
    # update timeout
    # ---------------------------------------------------

    timeout_elem.text = str(new_timeout)

    return {
        "type": "modify_timeout",
        "target_activity_label": target_activity_label,
        "old_timeout": old_timeout,
        "new_timeout": str(new_timeout)
    }