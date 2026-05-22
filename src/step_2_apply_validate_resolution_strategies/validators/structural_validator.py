from lxml import etree as ET

NS = {
"d": "http://cpee.org/ns/description/1.0"
}

class StructuralValidator:

    """
    Validates syntactic and structural correctness
    of the process model.

    Responsibilities:
    - unique IDs
    - unique labels
    - valid parallel blocks
    - valid choose blocks
    - valid loops
    - correct branch placement
    """

    def validate(self, root):

        warnings = []

        self.validate_unique_ids(root)

        duplicate_warnings = (
            self.validate_unique_labels(root)
        )

        warnings.extend(
            duplicate_warnings
        )

        self.validate_parallel_blocks(root)

        self.validate_choose_blocks(root)

        self.validate_loop_blocks(root)

        self.validate_branch_placement(root)

        return warnings

    # =====================================================
    # UNIQUE IDS
    # =====================================================

    def validate_unique_ids(self, root):

        ids = set()

        for elem in root.iter():

            elem_id = elem.attrib.get("id")

            if elem_id is None:
                continue

            if elem_id in ids:

                raise ValueError(
                    f"Duplicate ID detected: {elem_id}"
                )

            ids.add(elem_id)

    # =====================================================
    # UNIQUE LABELS
    # =====================================================

    def validate_unique_labels(self, root):

        labels = set()

        duplicated_labels = set()

        for label_elem in root.xpath(
                ".//d:label",
                namespaces=NS
        ):

            label = (
                    label_elem.text or ""
            ).strip()

            if not label:
                continue

            if label in labels:

                duplicated_labels.add(label)

            else:

                labels.add(label)

        warnings = []

        for label in sorted(
                duplicated_labels
        ):
            warning = (
                f"WARNING: Duplicate "
                f"label detected: {label}"
            )

            warnings.append(warning)

        return warnings
    # =====================================================
    # PARALLEL BLOCKS
    # =====================================================

    def validate_parallel_blocks(self, root):

        parallels = root.xpath(
            ".//d:parallel",
            namespaces=NS
        )

        for parallel in parallels:

            branches = [
                c for c in parallel
                if ET.QName(c).localname == "parallel_branch"
            ]

            # parallel requires at least 2 branches

            if len(branches) < 2:

                raise ValueError(
                    "Parallel block must contain "
                    "at least 2 branches"
                )

            # branches cannot be empty

            for branch in branches:

                if len(branch) == 0:

                    raise ValueError(
                        "Parallel branch cannot be empty"
                    )

    # =====================================================
    # CHOOSE BLOCKS
    # =====================================================

    def validate_choose_blocks(self, root):

        chooses = root.xpath(
            ".//d:choose",
            namespaces=NS
        )

        for choose in chooses:

            branches = [
                c for c in choose
                if ET.QName(c).localname in [
                    "alternative",
                    "otherwise"
                ]
            ]

            if len(branches) == 0:

                raise ValueError(
                    "Choose block must contain "
                    "at least one branch"
                )

            otherwise_count = len([
                c for c in choose
                if ET.QName(c).localname == "otherwise"
            ])

            if otherwise_count > 1:

                raise ValueError(
                    "Choose block can contain "
                    "at most one otherwise branch"
                )

    # =====================================================
    # LOOP BLOCKS
    # =====================================================

    def validate_loop_blocks(self, root):

        loops = root.xpath(
            ".//d:loop",
            namespaces=NS
        )

        for loop in loops:

            if len(loop) == 0:

                raise ValueError(
                    "Loop cannot be empty"
                )

            mode = loop.attrib.get("mode")

            if mode not in [
                "pre_test",
                "post_test"
            ]:

                raise ValueError(
                    f"Invalid loop mode: {mode}"
                )

    # =====================================================
    # BRANCH PLACEMENT
    # =====================================================

    def validate_branch_placement(self, root):

        for elem in root.iter():

            tag = ET.QName(elem).localname

            parent = elem.getparent()

            if parent is None:
                continue

            parent_tag = ET.QName(parent).localname

            # ---------------------------------------------

            if tag == "parallel_branch":

                if parent_tag != "parallel":

                    raise ValueError(
                        "parallel_branch outside parallel"
                    )

            # ---------------------------------------------

            if tag in [
                "alternative",
                "otherwise"
            ]:

                if parent_tag != "choose":

                    raise ValueError(
                        f"{tag} outside choose block"
                    )