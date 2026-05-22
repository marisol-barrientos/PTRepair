#    Copyright (C) <2025>  <Johannes Löbbecke>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import xml.etree.ElementTree as ET

def is_semantic_node(node):
    """
    Returns True only for semantically relevant process nodes.
    """
    if node.tag.endswith("call"):
        label = node.find(".//label")
        if label is not None:
            if label.text is not None:
                if label.text.strip() != "":
                    return True
        return False

    semantic_tags = [
        "choose",
        "parallel",
        "loop",
        "terminate",
        "stop",
        "escape"
    ]

    for tag in semantic_tags:
        if node.tag.endswith(tag):
            return True

    return False

def siblings(a, b, parentmap):
    parent = parentmap.get(a)

    if parent is None:
        return False

    if parent is not parentmap.get(b):
        return False

    children = [
        child for child in list(parent)
        if is_semantic_node(child)
    ]

    try:
        idx = next(
            i for i, child in enumerate(children)
            if child.attrib.get("id") == a.attrib.get("id")
        )

        return (
            idx + 1 < len(children)
            and children[idx + 1].tag == b.tag
        )

    except StopIteration:
        return False

def exists_by_label(root, mlabel):

    namespace = {
        "ns0":
            "http://cpee.org/ns/description/1.0"
    }

    if root is None:

        print(
            "exists_by_label: "
            "root is None"
        )

        return None

    if mlabel is None:

        print(
            "exists_by_label: "
            "mlabel is None"
        )

        return None

    target = (
        str(mlabel)
        .strip()
        .lower()
    )

    # ---------------------------------------------------------
    # search CALL nodes
    # ---------------------------------------------------------

    for call in root.findall(
        ".//ns0:call",
        namespace
    ):

        label = call.find(
            "ns0:parameters/ns0:label",
            namespace
        )

        if label is None:
            continue

        if label.text is None:
            continue

        current = (
            label.text
            .strip()
            .lower()
        )

        if current == target:

            return call

    # ---------------------------------------------------------
    # search MANIPULATE nodes
    # ---------------------------------------------------------

    for manipulate in root.findall(
        ".//ns0:manipulate",
        namespace
    ):

        label = manipulate.attrib.get(
            "label"
        )

        if label is None:
            continue

        current = (
            label
            .strip()
            .lower()
        )

        if current == target:

            return manipulate

    # ---------------------------------------------------------
    # debug output
    # ---------------------------------------------------------

    print(
        f"exists_by_label: "
        f"no match found for "
        f"'{mlabel}'"
    )

    print("Available labels:")

    # CALL labels

    for call in root.findall(
        ".//ns0:call",
        namespace
    ):

        label = call.find(
            "ns0:parameters/ns0:label",
            namespace
        )

        if (
            label is not None
            and label.text is not None
        ):

            print(
                " -",
                repr(
                    label.text.strip()
                )
            )

    # MANIPULATE labels

    for manipulate in root.findall(
        ".//ns0:manipulate",
        namespace
    ):

        label = manipulate.attrib.get(
            "label"
        )

        if label is not None:

            print(
                " -",
                repr(
                    label.strip()
                )
            )

    return None
def build_parent_map(root):
    return {child: parent for parent in root.iter() for child in parent}

def get_ancestors(root, ele):
    if ele is None:
        return []

    parent_map = build_parent_map(root)

    ancestors = []
    current = ele

    while current is not None:
        ancestors.append(current)
        current = parent_map.get(current)

    return ancestors

def get_shared_ancestors(root, ele1, ele2):
    ancestors1 = get_ancestors(root, ele1)
    ancestors2 = get_ancestors(root, ele2)

    shared_ancestors = [
        ancestor for ancestor in ancestors1
        if ancestor in ancestors2
    ]

    return ancestors1, ancestors2, shared_ancestors

def compare_ele_old(root, ele1, ele2):
    ancestors1, ancestors2, shared_ancestors = get_shared_ancestors(
        root,
        ele1,
        ele2
    )

    shared_ex_branch = 0
    exclusive = 0
    parallel = 0
    shared_par_branch = 0

    for ancestor in shared_ancestors:
        if ancestor.tag.endswith("otherwise") or ancestor.tag.endswith("alternative"):
            shared_ex_branch += 1

        if ancestor.tag.endswith("parallel_branch"):
            shared_par_branch += 1

        if ancestor.tag.endswith("choose"):
            exclusive += 1

        elif ancestor.tag.endswith("parallel"):
            parallel += 1

    if exclusive > shared_ex_branch:
        return 0

    elif parallel > shared_par_branch:
        return -1

    else:
        for element in root.iter():
            if element == ele1:
                return 1

            elif element == ele2:
                return 2

def compare_ele(root, ele1, ele2):
    if ele1 is None or ele2 is None:
        raise ValueError(
            f"compare_ele received None.\n"
            f"ele1={ele1}\n"
            f"ele2={ele2}"
        )

    ancestors1, ancestors2, shared = get_shared_ancestors(
        root,
        ele1,
        ele2
    )

    if not shared:
        raise ValueError(
            "No shared ancestors found.\n"
            f"ele1_tag={ele1.tag}\n"
            f"ele1_id={ele1.attrib.get('id')}\n"
            f"ele2_tag={ele2.tag}\n"
            f"ele2_id={ele2.attrib.get('id')}"
        )

    LCA = shared[0].tag

    if LCA.endswith("choose"):
        return 0

    elif LCA.endswith("parallel"):
        return -1

    else:
        for element in root.iter():
            if element == ele1:
                return 1

            elif element == ele2:
                return 2

    return None

def directly_follows_must(root, ele1, ele2):
    ancestors1, ancestors2, shared_ancestors = get_shared_ancestors(
        root,
        ele1,
        ele2
    )

    shared_ex_branch = 0
    exclusive = 0
    parallel = 0
    shared_par_branch = 0

    for ancestor in shared_ancestors:
        if ancestor.tag.endswith("otherwise") or ancestor.tag.endswith("alternative"):
            shared_ex_branch += 1

        if ancestor.tag.endswith("parallel_branch"):
            shared_par_branch += 1

        if ancestor.tag.endswith("choose"):
            exclusive += 1

        elif ancestor.tag.endswith("parallel"):
            parallel += 1

    if exclusive > shared_ex_branch:
        return False

    elif parallel > shared_par_branch:
        return False

    elements = [
        elem for elem in root.iter()
        if (
            elem.tag.endswith('call')
            or elem.tag.endswith("terminate")
            or elem.tag.endswith("start_activity")
            or elem.tag.endswith("end_activity")
        )
    ]

    for i in range(len(elements) - 1):
        if elements[i] is ele1 and elements[i + 1] is ele2:
            return True

    return False

def directly_follows_can(root, ele1, ele2):
    ancestors1, ancestors2, shared_ancestors = get_shared_ancestors(
        root,
        ele1,
        ele2
    )

    shared_ex_branch = 0
    exclusive = 0
    parallel = 0
    shared_par_branch = 0

    for ancestor in shared_ancestors:
        if ancestor.tag.endswith("otherwise") or ancestor.tag.endswith("alternative"):
            shared_ex_branch += 1

        if ancestor.tag.endswith("parallel_branch"):
            shared_par_branch += 1

        if ancestor.tag.endswith("choose"):
            exclusive += 1

        elif ancestor.tag.endswith("parallel"):
            parallel += 1

    if exclusive > shared_ex_branch:
        return False

    elif parallel > shared_par_branch:
        return False

    elements = [
        elem for elem in root.iter()
        if elem.tag.endswith('call')
    ]

    for i in range(len(elements) - 1):
        if elements[i] is ele1 and elements[i + 1] is ele2:
            return True

    last_in_branch = False

    for ancestor in ancestors1:
        if ancestor.tag.endswith("parallel") or ancestor.tag.endswith("choose"):

            elementsall = [
                elem for elem in root.iter()
                if (
                    elem.tag.endswith("call")
                    or elem.tag.endswith("parallel")
                    or elem.tag.endswith("choose")
                    or elem.tag.endswith("parallel_branch")
                    or elem.tag.endswith("alternative")
                    or elem.tag.endswith("otherwise")
                )
            ]

            for i in range(len(elementsall) - 1):
                if elementsall[i] is ele1:
                    if not elementsall[i + 1].tag.endswith("call"):
                        last_in_branch = True

                if elementsall[i] is ele2:
                    return (
                        last_in_branch
                        and not shared_ex_branch == exclusive
                    )

    return False

def cancel_first(tree, a, b):
    ancestors1, ancestors2, shared_ancestors = get_shared_ancestors(
        tree,
        a,
        b
    )

    shared_branch = 0
    parallel = 0

    for ancestor in shared_ancestors:
        if ancestor.tag.endswith("parallel_branch"):
            shared_branch += 1

        elif ancestor.tag.endswith("parallel"):
            if shared_branch <= parallel:
                if (
                    ancestor.attrib.get("wait") == "1"
                    and ancestor.attrib.get("cancel") == "first"
                ):
                    return ancestor

            parallel += 1

    return None

def cancel_last(tree, a, b):
    ancestors1, ancestors2, shared_ancestors = get_shared_ancestors(
        tree,
        a,
        b
    )

    shared_branch = 0
    parallel = 0

    for ancestor in shared_ancestors:
        if ancestor.tag.endswith("parallel_branch"):
            shared_branch += 1

        elif ancestor.tag.endswith("parallel"):
            if shared_branch <= parallel:
                if (
                    ancestor.attrib.get("wait") == "1"
                    and ancestor.attrib.get("cancel") == "last"
                ):
                    return ancestor

            parallel += 1

    return None