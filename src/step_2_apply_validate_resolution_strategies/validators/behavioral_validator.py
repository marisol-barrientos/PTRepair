from lxml import etree as ET

NS = {
"d": "http://cpee.org/ns/description/1.0"
}

class BehavioralValidator:

    """
    Lightweight behavioral validation.

    Current responsibilities:
    - detect obviously unreachable XORs
    - detect suspicious infinite loops
    - detect problematic terminate inside parallel
    - detect empty execution paths

    """

    def validate(self, root):

        self.validate_choose_executability(root)

        self.validate_loop_termination_risk(root)

        self.validate_parallel_terminate_risk(root)

    # =====================================================
    # XOR EXECUTABILITY
    # =====================================================

    def validate_choose_executability(self, root):

        chooses = root.xpath(
            ".//d:choose",
            namespaces=NS
        )

        for choose in chooses:

            alternatives = choose.xpath(
                "./d:alternative",
                namespaces=NS
            )

            otherwise = choose.xpath(
                "./d:otherwise",
                namespaces=NS
            )

            # ---------------------------------------------
            # no branches at all
            # ---------------------------------------------

            if not alternatives and not otherwise:

                raise ValueError(
                    "Behavioral risk: choose block "
                    "has no executable branch"
                )

            # ---------------------------------------------
            # suspicious impossible conditions
            # heuristic only
            # ---------------------------------------------

            impossible_conditions = 0

            for alt in alternatives:

                cond = (
                    alt.attrib.get("condition", "")
                    .strip()
                    .lower()
                )

                if cond in [
                    "false",
                    "0",
                    "none"
                ]:

                    impossible_conditions += 1

            if (
                impossible_conditions == len(alternatives)
                and not otherwise
            ):

                raise ValueError(
                    "Behavioral risk: all XOR branches "
                    "appear unreachable"
                )

    # =====================================================
    # LOOP TERMINATION RISK
    # =====================================================

    def validate_loop_termination_risk(self, root):

        loops = root.xpath(
            ".//d:loop",
            namespaces=NS
        )

        for loop in loops:

            condition = (
                loop.attrib.get("condition", "")
                .strip()
                .lower()
            )

            # ---------------------------------------------
            # obvious infinite loop indicators
            # heuristic only
            # ---------------------------------------------

            if condition in [
                "true",
                "1"
            ]:

                raise ValueError(
                    "Behavioral risk: loop condition "
                    "appears always true"
                )

    # =====================================================
    # TERMINATE INSIDE PARALLEL
    # =====================================================

    def validate_parallel_terminate_risk(self, root):

        parallels = root.xpath(
            ".//d:parallel",
            namespaces=NS
        )

        for parallel in parallels:

            terminates = parallel.xpath(
                ".//d:terminate",
                namespaces=NS
            )

            if terminates:

                raise ValueError(
                    "Behavioral risk: terminate "
                    "inside parallel block may "
                    "cause synchronization anomalies"
                )