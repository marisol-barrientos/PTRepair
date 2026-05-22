

def normalize_label(label: str) -> str:
    return label.strip().lower()


def is_call(node):
    return node.tag.endswith("call")


def get_label(node):
    """
    Unified label extractor:
    - Only returns labels for <call> elements
    - Supports both simple and full CPEE models
    """
    if not is_call(node):
        return None

    # Case 1: attribute-based (simple models)
    if "label" in node.attrib:
        return node.attrib["label"].strip()

    # Case 2: CPEE structure → parameters/label
    label_elem = node.find(".//{*}parameters/{*}label")
    if label_elem is not None and label_elem.text:
        return label_elem.text.strip()

    return None


def find_unique_by_label(root, label):
    target = normalize_label(label)
    matches = []

    for node in root.iter():
        node_label = get_label(node)
        if node_label and normalize_label(node_label) == target:
            matches.append(node)

    if len(matches) == 0:
        raise ValueError(f"No node found with label '{label}'")

    if len(matches) > 1:
        ids = [n.attrib.get("id") for n in matches]
        raise ValueError(
            f"Ambiguous label '{label}' found in nodes {ids}"
        )

    return matches[0]


def validate_unique_labels(root):
    labels = {}

    for node in root.iter():
        label = get_label(node)

        if label:
            norm = normalize_label(label)
            node_id = node.attrib.get("id")

            if norm in labels:
                raise ValueError(
                    f"Duplicate label '{label}' found "
                    f"(ids: {labels[norm]} and {node_id})"
                )

            labels[norm] = node_id