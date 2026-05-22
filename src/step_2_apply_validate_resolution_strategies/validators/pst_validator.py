# validators/pst_validator.py

from lxml import etree as ET

class PSTValidator:


    """
    Validates process-tree / block-structuredness
    properties.

    Responsibilities:
    - proper hierarchical nesting
    - no malformed crossing structures
    - valid parent-child relationships
    """

    def validate(self, root):

        self.validate_no_crossing_structures(root)

        self.validate_no_nested_parallel_branch(root)

    # =====================================================
    # NO CROSSING STRUCTURES
    # =====================================================

    def validate_no_crossing_structures(self, root):

        """
        Ensures control-flow blocks are
        properly nested.

        Prevents malformed overlapping
        control-flow structures.
        """

        for elem in root.iter():

            tag = ET.QName(elem).localname

            if tag in [
                "parallel",
                "choose",
                "loop"
            ]:

                self._validate_recursive_structure(elem)

    # =====================================================
    # RECURSIVE STRUCTURE VALIDATION
    # =====================================================

    def _validate_recursive_structure(self, node):

        for child in node:

            if child.getparent() is not node:

                raise ValueError(
                    "Malformed PST hierarchy detected"
                )

            self._validate_recursive_structure(child)

    # =====================================================
    # PARALLEL BRANCH NESTING
    # =====================================================

    def validate_no_nested_parallel_branch(self, root):

        for branch in root.iter():

            if ET.QName(branch).localname != "parallel_branch":
                continue

            parent = branch.getparent()

            if parent is None:

                raise ValueError(
                    "parallel_branch without parent"
                )

            if ET.QName(parent).localname != "parallel":

                raise ValueError(
                    "parallel_branch outside parallel"
                )

