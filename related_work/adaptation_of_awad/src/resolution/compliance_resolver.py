from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

from src.model.node import Node, NodeType
from src.model.pst import ProcessStructureTree
from src.context.business_context import BusinessContext
from src.planning.planner import Planner


class ViolationType(str, Enum):
    none = "none"
    splittingChoice = "splittingChoice"
    DifferentBranches = "DifferentBranches"
    LackofActivity = "LackofActivity"
    InverseOrder = "InverseOrder"


@dataclass
class ComplianceResolver:
    """
    Resolver aligned with Awad/Smirnov/Weske (splitting-choice Algorithm 1),
    plus an EXTRA cleanup pass to remove redundant blocks after resolution.

    Key points:
      - Splitting-choice: for each branch missing B, we:
          (i) delete it if it contains contradicting activities for B, else
          (ii) try to plan to reach B from the state AFTER executing the branch's
               current actions; if no plan -> delete branch; else merge plan into branch.
        This prevents "phantom" merges that add a NEW choice branch.
      - cleanup_redundant_blocks(): collapses XCHOICE with single branch and flattens sequences.
    """
    tree: ProcessStructureTree
    bc: BusinessContext
    planner: Optional[Planner] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # IMPORTANT: don't overwrite a scenario-loaded BusinessContext
        if not self.bc.get_business_context_activities():
            try:
                self.bc.full_load()
            except TypeError:
                self.bc.full_load()  # type: ignore

        if self.planner is None:
            self.planner = Planner(self.bc)

    # -----------------------------
    # Public helpers
    # -----------------------------
    def get_tree(self) -> ProcessStructureTree:
        return self.tree

    def get_business_context(self) -> BusinessContext:
        return self.bc

    # -----------------------------
    # Violation detection
    # -----------------------------
    def get_violation_type_of_leads_to(self, src: Node, dst: Node) -> ViolationType:
        lcp = self.tree.least_common_parent(src, dst)

        if len(self.tree.get_occurrences_of_label(dst.label)) == 0:
            return ViolationType.LackofActivity

        if lcp.node_type in (NodeType.Parallel, NodeType.XChoice, NodeType.IChoice):
            return ViolationType.DifferentBranches

        if lcp.node_type == NodeType.Sequence:
            if self.tree.get_order(dst, lcp) < self.tree.get_order(src, lcp):
                return ViolationType.InverseOrder

            path = self.tree.find_path(dst, lcp)
            for nd in path:
                if nd.node_type in (NodeType.XChoice, NodeType.IChoice):
                    if not self.tree.always_executed(nd, dst.label):
                        return ViolationType.splittingChoice
            return ViolationType.none

        return ViolationType.splittingChoice

    # -----------------------------
    # Resolution entry points
    # -----------------------------
    def resolve_splitting_choice_violation(self, src: Node, dst: Node) -> ProcessStructureTree:
        comp_tree = self.tree
        s = comp_tree.least_common_parent(src, dst)
        if s.node_type != NodeType.Sequence:
            return comp_tree

        # x is the choice block containing b
        x = comp_tree.get_enclosing_block(dst, NodeType.XChoice) or comp_tree.get_enclosing_block(dst, NodeType.IChoice)
        if x is None:
            return comp_tree

        # contradicting activities for b (optional)
        contra_raw = (
                self.bc.get_contradicting_activities(dst.label.lower())
                or self.bc.get_contradicting_activities(dst.label)
                or self.bc.get_contradicting_activities(dst.label.strip().lower())
                or self.bc.get_contradicting_activities(dst.label.strip())
        )
        contra_acts = [a.strip().lower() for a in contra_raw.split(",") if a.strip()] if contra_raw else []

        goal_state = [f"EXECUTED {dst.label.replace(' ', '-')}"]
        to_delete: List[Node] = []

        for branch in list(x.children):
            # branches are supposed to be SEQUENCE nodes under the choice
            branch_seq = branch if branch.node_type == NodeType.Sequence else None
            if branch_seq is None:
                # if your PST loader ever puts non-sequence nodes under XCHOICE, skip safely
                continue

            # skip branches that already contain B (paper line 9 "branch with no b")
            if comp_tree.always_executed(branch_seq, dst.label):
                continue

            # paper lines 10–12: delete if contradicting activities exist in branch
            if contra_acts:
                branch_act_labels = {a.label.strip().lower() for a in self._get_activities(branch_seq)}
                if any(ca in branch_act_labels for ca in contra_acts):
                    to_delete.append(branch_seq)
                    continue

            # paper line 13: plan under branch execution context
            # IMPORTANT: anchor = last activity in THIS branch (state after executing it)
            branch_acts = [a for a in self._get_activities(branch_seq) if a.node_type == NodeType.Activity]
            anchor = branch_acts[-1] if branch_acts else src

            init_states = self.generate_cumulative_effect(anchor, exclude=None)

            plan_tree: Optional[ProcessStructureTree] = None
            for ini in init_states:
                plan_tree = self.planner.find_plan(list(ini), goal_state)  # type: ignore[union-attr]
                if plan_tree is not None:
                    break

            # paper lines 14–15: no plan => delete branch
            if plan_tree is None:
                to_delete.append(branch_seq)
                continue

            # paper line 17: merge plan INTO THIS BRANCH (never into x!)
            # Extract planned activities robustly
            planned_acts: List[Node] = []
            for n in getattr(plan_tree.root, "children", []):
                if n.node_type == NodeType.Activity:
                    planned_acts.append(n)
                else:
                    # if your planner outputs nested sequences, collect activities inside them
                    planned_acts.extend([a for a in self._get_activities(n) if a.node_type == NodeType.Activity])

            existing = {a.label.strip().lower() for a in self._get_activities(branch_seq)}
            for act in planned_acts:
                lab = act.label.strip().lower()
                if lab in existing:
                    continue
                nn = act.clone()
                nn.parent = branch_seq
                branch_seq.children.append(nn)  # <- guaranteed to stay inside this branch
                existing.add(lab)

        # apply deletions
        for b in to_delete:
            comp_tree.delete_node(b, x)

        return comp_tree

    def resolve_different_branches_violation(self, src: Node, dst: Node) -> Optional[ProcessStructureTree]:
        comp_tree = self.tree
        lcp = comp_tree.least_common_parent(src, dst)
        if lcp.node_type == NodeType.Parallel:
            return self._resolve_parallel_branches_violation(src, dst, lcp)
        if lcp.node_type == NodeType.XChoice:
            return self.resolve_lack_of_activity_violation(src, dst)
        return None

    def resolve_inverse_order_violation(
            self, src: Node, dst: Node
    ) -> Optional[ProcessStructureTree]:
        """
        Corrected version:
        - Dependency is checked on ORIGINAL structure (not sub_seq)
        - Uses semantic + causal dependency detection
        - Prevents invalid parallelization
        """

        # --------------------------------------------------
        # STEP 1: Find initial anchor (before dst)
        # --------------------------------------------------
        prev = self.tree.get_previous_node(dst)
        if prev is None:
            prev = dst.parent.parent if dst.parent and dst.parent.parent else None

        if prev is None:
            return None

        # --------------------------------------------------
        # STEP 2: Feasibility check (Awad et al.)
        # --------------------------------------------------
        p_tree: Optional[ProcessStructureTree] = None

        final_state = [
            f"EXECUTED {src.label.replace(' ', '-')}",
            f"!EXECUTED {dst.label.replace(' ', '-')}",
        ]

        while prev is not None and prev != src:
            init_states = self.generate_cumulative_effect(prev, exclude=None)

            for ini in init_states:
                p_tree = self.planner.find_plan(ini, final_state)
                if p_tree is not None:
                    break

            if p_tree is not None:
                break

            prev = self.tree.get_previous_node(prev)

        if p_tree is None:
            return None

        # --------------------------------------------------
        # 🔥 STEP 3: DEPENDENCY CHECK (BEFORE MODIFICATION)
        # --------------------------------------------------
        requires_dst = False

        parent = src.parent
        if parent and parent.node_type == NodeType.Sequence:

            src_order = self.tree.get_order(src, parent)

            for node in parent.get_children():
                order = self.tree.get_order(node, parent)

                if order <= src_order:
                    continue

                # check full subtree of each future node
                if self.subtree_requires_activity(node, dst.label):
                    requires_dst = True
                    break

        # --------------------------------------------------
        # STEP 4: Extract subsequences (AFTER decision!)
        # --------------------------------------------------
        sub_seq = self.tree.get_subsequence_after(dst)
        sub_seq.add_child(dst.clone(), 1)

        sub_seq2 = self.tree.get_subsequence_after(src)
        sub_seq2.add_child(src.clone(), 1)

        # remove overlaps
        to_del: List[Node] = []
        for o in sub_seq2.children:
            if o in sub_seq.children:
                to_del.append(o)
        for d in to_del:
            sub_seq.delete_child(d)

        # --------------------------------------------------
        # REMOVE original misplaced nodes
        # --------------------------------------------------
        for n in list(sub_seq.children):
            self.tree.delete_node(n, dst.parent)

        # --------------------------------------------------
        # STEP 5: Continuation feasibility
        # --------------------------------------------------
        continuation_goal = []
        for n in sub_seq.children:
            for a in self._get_activities(n):
                continuation_goal.append(f"EXECUTED {a.label.replace(' ', '-')}")

        init_states = self.generate_cumulative_effect(src, exclude=None)

        feasible = False
        for ini in init_states:
            p_tree = self.planner.find_plan(ini, continuation_goal)
            if p_tree is not None:
                feasible = True
                break

        if not feasible:
            return None

        # --------------------------------------------------
        # 🔥 STEP 6: Dependency-aware decision
        # --------------------------------------------------
        if requires_dst:
            # ✅ SEQUENTIAL REORDERING (CORRECT CASE)

            parent = src.parent
            if parent is None:
                return None

            point = self.tree.get_order(src, parent)

            for n in sub_seq.children:
                point += 1
                self.tree.insert_node(n, parent, point)

            return self.tree

        # --------------------------------------------------
        # STEP 7: SAFE PARALLELIZATION
        # --------------------------------------------------
        next_node = self.tree.get_next_node(src)
        parent = src.parent

        if parent is None:
            return None

        # no continuation → append
        if next_node is None:
            point = self.tree.get_order(src, parent)
            for n in sub_seq.children:
                point += 1
                self.tree.insert_node(n, parent, point)
            return self.tree

        # create parallel block
        p_node = Node(node_type=NodeType.Parallel)

        seq1 = self.tree.get_subsequence_after(src)

        self.tree.insert_node(
            p_node, parent, self.tree.get_order(src, parent) + 1
        )

        for n in list(seq1.children):
            self.tree.delete_node(n, parent)

        self.tree.insert_node(seq1, p_node)
        self.tree.insert_node(sub_seq, p_node)

        return self.tree

    # -----------------------------
    # Lack-of-Activity resolution
    # -----------------------------
    def _insertion_anchor_after_src(self, src_node: Node) -> Tuple[Node, int]:
        parent = src_node.parent
        if parent is None:
            return (src_node, 1)

        next_node = self.tree.get_next_node(src_node)

        if next_node is not None and next_node.node_type in (NodeType.Parallel, NodeType.XChoice, NodeType.IChoice):
            pos = self.tree.get_order(next_node, parent)  # 1-based index of block
            return (parent, pos)

        pos = self.tree.get_order(src_node, parent) + 1
        return (parent, pos)

    def resolve_lack_of_activity_violation(
            self, src: Node, dst: Node
    ) -> Optional[ProcessStructureTree]:

        def _normalize(label: str) -> str:
            return label.strip().lower()

        contradicting_nodes: List[Node] = []
        contradicting_acts: List[str] = []

        # -------------------------------
        # 1. Get contradicting activities
        # -------------------------------
        contra = self.bc.get_contradicting_activities(_normalize(dst.get_label()))
        if contra:
            for s in contra.split(","):
                s = _normalize(s)
                if s and s not in contradicting_acts:
                    contradicting_acts.append(s)

        # -------------------------------
        # 2. Collect contradicting nodes
        # -------------------------------
        def is_inside_xor(node: Node) -> bool:
            p = node.get_parent()
            while p:
                if p.get_node_type() == NodeType.XChoice:
                    return True
                p = p.get_parent()
            return False

        for s in contradicting_acts:
            for n in self.tree.get_occurrences_of_label(s):
                if is_inside_xor(n):
                    return None
                contradicting_nodes.append(n)

        # -------------------------------
        # Helper: existing labels
        # -------------------------------
        def existing_labels() -> set:
            return {
                _normalize(n.get_label())
                for n in self.tree.nodes
                if n.get_node_type() == NodeType.Activity
            }

        # -------------------------------
        # Helper: plan A → B
        # -------------------------------
        def plan_a_to_b() -> Optional[ProcessStructureTree]:
            init_states = self.generate_cumulative_effect(src, exclude=None)
            goal_state = [f"executed {_normalize(dst.get_label()).replace(' ', '-')}"]

            for ini in init_states:
                plan = self.planner.find_plan(ini, goal_state)
                if plan:
                    return plan
            return None

        # -------------------------------
        # 🔥 NEW: Extract postconditions
        # -------------------------------
        def get_postconditions(plan_tree) -> set:
            posts = set()
            for act in plan_tree.get_activities():
                post = self.bc.activities_postconditions_positive.get(
                    _normalize(act.get_label())
                )
                if post:
                    posts.add(post)
            return posts

        # -------------------------------
        # 🔥 NEW: Get downstream nodes
        # -------------------------------
        def get_downstream_nodes(node: Node) -> List[Node]:
            parent = node.get_parent()
            if not parent:
                return []

            order = self.tree.get_order(node, parent)
            downstream = []

            for sibling in parent.get_children()[order + 1:]:
                downstream.extend(self.tree.get_subtree_nodes(sibling))

            return [
                n for n in downstream
                if n.get_node_type() == NodeType.Activity
            ]

        # -------------------------------
        # 🔥 NEW: Postcondition safety check
        # -------------------------------
        def is_postcondition_safe(plan_tree, insert_after: Node) -> bool:

            def contradicts(p: str, required: List[str]) -> bool:
                for r in required:

                    # direct negation (fallback)
                    if p == f"not {r}" or r == f"not {p}":
                        return True

                    # 🔥 USE BC FUNCTION
                    contra_p = self.bc.get_contradicting_state(p)
                    if contra_p and contra_p == r:
                        return True

                    contra_r = self.bc.get_contradicting_state(r)
                    if contra_r and contra_r == p:
                        return True

                return False

            posts = get_postconditions(plan_tree)
            downstream = get_downstream_nodes(insert_after)

            for node in downstream:
                label = _normalize(node.get_label())

                # ---- check against future preconditions
                pre = self.bc.activities_preconditions.get(label)
                if pre:
                    required = [p.strip() for p in pre.split("and")]

                    for p in posts:
                        if contradicts(p, required):
                            return False

                # ---- check against future postconditions
                post_future = self.bc.activities_postconditions_positive.get(label)
                if post_future:
                    for p in posts:
                        if contradicts(p, [post_future]):
                            return False

            return True

        # -------------------------------
        # 🔥 Control-flow aware insertion
        # -------------------------------
        def find_insertion_node() -> Optional[Node]:
            parent = src.get_parent()
            if parent is None:
                return src

            required = self.bc.activities_preconditions.get(_normalize(dst.get_label()))
            if not required:
                return src

            required_parts = [r.strip() for r in required.split("and")]

            best_node = src
            best_order = self.tree.get_order(src, parent)

            for node in parent.get_children():

                # -------- Activity
                if node.get_node_type() == NodeType.Activity:
                    post = self.bc.activities_postconditions_positive.get(
                        _normalize(node.get_label())
                    )
                    if post and post in required_parts:
                        order = self.tree.get_order(node, parent)
                        if order > best_order:
                            best_node = node
                            best_order = order

                # -------- Parallel
                elif node.get_node_type() == NodeType.Parallel:

                    branches = node.get_children()
                    producers = []

                    for branch in branches:
                        found = False
                        for sub in self.tree.get_subtree_nodes(branch):
                            if sub.get_node_type() != NodeType.Activity:
                                continue
                            post = self.bc.activities_postconditions_positive.get(
                                _normalize(sub.get_label())
                            )
                            if post and post in required_parts:
                                found = True
                                break
                        producers.append(found)

                    if all(producers):
                        order = self.tree.get_order(node, parent)
                        if order > best_order:
                            best_node = node
                            best_order = order

                    elif any(producers):
                        for i, branch in enumerate(branches):
                            if producers[i]:
                                seq = branch
                                while seq.get_node_type() != NodeType.Sequence:
                                    seq = seq.get_children()[0]
                                return seq.get_children()[-1]

                # -------- XOR
                elif node.get_node_type() == NodeType.XChoice:

                    branches = node.get_children()
                    producers = []

                    for branch in branches:
                        found = False
                        for sub in self.tree.get_subtree_nodes(branch):
                            if sub.get_node_type() != NodeType.Activity:
                                continue
                            post = self.bc.activities_postconditions_positive.get(
                                _normalize(sub.get_label())
                            )
                            if post and post in required_parts:
                                found = True
                                break
                        producers.append(found)

                    if any(producers) and not all(producers):
                        return None

                    if all(producers):
                        order = self.tree.get_order(node, parent)
                        if order > best_order:
                            best_node = node
                            best_order = order

            return best_node

        # =========================================================
        # 🔥 CASE 1: CONTRADICTIONS → LOCAL XOR REPLACEMENT
        # =========================================================
        if contradicting_nodes:

            for contra_node in contradicting_nodes:

                parent = contra_node.get_parent()
                if parent is None:
                    return None

                idx = parent.get_children().index(contra_node)

                plan_tree = plan_a_to_b()
                if plan_tree is None:
                    return None

                # 🔥 NEW: safety check
                if not is_postcondition_safe(plan_tree, contra_node):
                    return None

                existing = existing_labels()

                frag_b = Node(node_type=NodeType.Sequence)
                frag_b.set_condition("true")

                for act in plan_tree.get_activities():
                    norm = _normalize(act.get_label())
                    if norm not in existing:
                        new_node = act.clone()
                        new_node.set_label(norm)
                        frag_b.add_child(new_node)
                        existing.add(norm)

                xor = Node(node_type=NodeType.XChoice)
                xor.add_child(contra_node.clone())
                xor.add_child(frag_b)

                parent.get_children()[idx] = xor
                xor.set_parent(parent)

                return self.tree

        # =========================================================
        # 🔥 CASE 2: NORMAL INSERTION
        # =========================================================
        plan_tree = plan_a_to_b()
        if plan_tree is None:
            return None

        insert_after = find_insertion_node()
        if insert_after is None:
            return None

        # 🔥 NEW: safety check
        if not is_postcondition_safe(plan_tree, insert_after):
            return None

        parent = insert_after.get_parent()
        if parent is None:
            return None

        pos = self.tree.get_order(insert_after, parent) + 1
        existing = existing_labels()

        for act in plan_tree.get_activities():
            norm = _normalize(act.get_label())
            if norm in existing:
                continue

            new_node = act.clone()
            new_node.set_label(norm)

            self.tree.insert_node(new_node, parent, pos)
            pos += 1
            existing.add(norm)

        return self.tree

    def resolve_lack_of_activity_violation_almots(
            self, src: Node, dst: Node
    ) -> Optional[ProcessStructureTree]:

        def _normalize(label: str) -> str:
            return label.strip().lower()

        contradicting_nodes: List[Node] = []
        contradicting_acts: List[str] = []

        # -------------------------------
        # 1. Get contradicting activities
        # -------------------------------
        contra = self.bc.get_contradicting_activities(_normalize(dst.get_label()))
        if contra:
            for s in contra.split(","):
                s = _normalize(s)
                if s and s not in contradicting_acts:
                    contradicting_acts.append(s)

        # -------------------------------
        # 2. Collect contradicting nodes
        # -------------------------------
        def is_inside_xor(node: Node) -> bool:
            p = node.get_parent()
            while p:
                if p.get_node_type() == NodeType.XChoice:
                    return True
                p = p.get_parent()
            return False

        for s in contradicting_acts:
            for n in self.tree.get_occurrences_of_label(s):
                if is_inside_xor(n):
                    return None
                contradicting_nodes.append(n)

        # -------------------------------
        # Helper: existing labels
        # -------------------------------
        def existing_labels() -> set:
            return {
                _normalize(n.get_label())
                for n in self.tree.nodes
                if n.get_node_type() == NodeType.Activity
            }

        # -------------------------------
        # Helper: plan A → B
        # -------------------------------
        def plan_a_to_b() -> Optional[ProcessStructureTree]:
            init_states = self.generate_cumulative_effect(src, exclude=None)
            goal_state = [f"executed {_normalize(dst.get_label()).replace(' ', '-')}"]

            for ini in init_states:
                plan = self.planner.find_plan(ini, goal_state)
                if plan:
                    return plan
            return None

        # -------------------------------
        # 🔥 Control-flow aware insertion
        # -------------------------------
        def find_insertion_node() -> Optional[Node]:
            parent = src.get_parent()
            if parent is None:
                return src

            required = self.bc.activities_preconditions.get(_normalize(dst.get_label()))
            if not required:
                return src

            required_parts = [r.strip() for r in required.split("and")]

            best_node = src
            best_order = self.tree.get_order(src, parent)

            for node in parent.get_children():

                # -------- Activity
                if node.get_node_type() == NodeType.Activity:
                    post = self.bc.activities_postconditions_positive.get(
                        _normalize(node.get_label())
                    )
                    if post and post in required_parts:
                        order = self.tree.get_order(node, parent)
                        if order > best_order:
                            best_node = node
                            best_order = order

                # -------- Parallel
                elif node.get_node_type() == NodeType.Parallel:

                    branches = node.get_children()
                    producers = []

                    for branch in branches:
                        found = False
                        for sub in self.tree.get_subtree_nodes(branch):
                            if sub.get_node_type() != NodeType.Activity:
                                continue
                            post = self.bc.activities_postconditions_positive.get(
                                _normalize(sub.get_label())
                            )
                            if post and post in required_parts:
                                found = True
                                break
                        producers.append(found)

                    if all(producers):
                        order = self.tree.get_order(node, parent)
                        if order > best_order:
                            best_node = node
                            best_order = order

                    elif any(producers):
                        for i, branch in enumerate(branches):
                            if producers[i]:
                                seq = branch
                                while seq.get_node_type() != NodeType.Sequence:
                                    seq = seq.get_children()[0]
                                return seq.get_children()[-1]

                # -------- XOR
                elif node.get_node_type() == NodeType.XChoice:

                    branches = node.get_children()
                    producers = []

                    for branch in branches:
                        found = False
                        for sub in self.tree.get_subtree_nodes(branch):
                            if sub.get_node_type() != NodeType.Activity:
                                continue
                            post = self.bc.activities_postconditions_positive.get(
                                _normalize(sub.get_label())
                            )
                            if post and post in required_parts:
                                found = True
                                break
                        producers.append(found)

                    # ❌ partial → invalid
                    if any(producers) and not all(producers):
                        return None

                    if all(producers):
                        order = self.tree.get_order(node, parent)
                        if order > best_order:
                            best_node = node
                            best_order = order

            return best_node

        # =========================================================
        # 🔥 CASE 1: CONTRADICTIONS → LOCAL XOR REPLACEMENT
        # =========================================================
        if contradicting_nodes:

            for contra_node in contradicting_nodes:

                parent = contra_node.get_parent()
                if parent is None:
                    return None

                idx = parent.get_children().index(contra_node)

                plan_tree = plan_a_to_b()
                if plan_tree is None:
                    return None

                existing = existing_labels()

                frag_b = Node(node_type=NodeType.Sequence)
                frag_b.set_condition("true")

                for act in plan_tree.get_activities():
                    norm = _normalize(act.get_label())
                    if norm not in existing:
                        new_node = act.clone()
                        new_node.set_label(norm)
                        frag_b.add_child(new_node)
                        existing.add(norm)

                xor = Node(node_type=NodeType.XChoice)

                # ✔ ONLY the contradicting activity
                xor.add_child(contra_node.clone())

                # ✔ plan branch
                xor.add_child(frag_b)

                parent.get_children()[idx] = xor
                xor.set_parent(parent)

                return self.tree

        # =========================================================
        # 🔥 CASE 2: NO CONTRADICTIONS → NORMAL INSERTION
        # =========================================================
        plan_tree = plan_a_to_b()
        if plan_tree is None:
            return None

        insert_after = find_insertion_node()
        if insert_after is None:
            return None

        parent = insert_after.get_parent()
        if parent is None:
            return None

        pos = self.tree.get_order(insert_after, parent) + 1
        existing = existing_labels()

        for act in plan_tree.get_activities():
            norm = _normalize(act.get_label())
            if norm in existing:
                continue

            new_node = act.clone()
            new_node.set_label(norm)

            self.tree.insert_node(new_node, parent, pos)
            pos += 1
            existing.add(norm)

        return self.tree


    # -----------------------------
    # Cleanup (EXTRA, per your request)
    # -----------------------------
    def cleanup_redundant_blocks(self) -> None:
        """
        Extra cleanup after resolution:
          - Remove empty Sequence branches inside choices
          - Collapse XChoice/IChoice with 1 remaining branch (splice into parent)
          - Flatten nested Sequences (Sequence inside Sequence with condition true)
          - (Optional) Collapse Parallel with 1 branch
        """
        def is_true(cond: Optional[str]) -> bool:
            return (cond is None) or (cond.strip() == "") or (cond.strip().lower() == "true")

        def walk(node: Node) -> None:
            for ch in list(getattr(node, "children", [])):
                walk(ch)

            # Remove empty branches inside choice blocks
            if node.node_type in (NodeType.XChoice, NodeType.IChoice):
                for br in list(node.children):
                    if br.node_type == NodeType.Sequence and len(br.children) == 0:
                        self.tree.delete_node(br, node)

            # Remove duplicate branches in XChoice/IChoice:
            # if two branches contain the same activity-label sequence, keep only one.
            if node.node_type in (NodeType.XChoice, NodeType.IChoice):
                def branch_signature(br: Node) -> Tuple[str, ...]:
                    # signature = ordered activity labels in this branch
                    acts = [a.label.strip().lower() for a in self._get_activities(br)]
                    return tuple(acts)

                seen: Set[Tuple[str, ...]] = set()
                duplicates: List[Node] = []
                for br in list(node.children):
                    sig = branch_signature(br)
                    if sig in seen:
                        duplicates.append(br)
                    else:
                        seen.add(sig)

                for br in duplicates:
                    self.tree.delete_node(br, node)

            # Collapse choice block with a single branch
            if node.node_type in (NodeType.XChoice, NodeType.IChoice):
                if len(node.children) == 1:
                    only_branch = node.children[0]
                    parent = node.parent
                    if parent is None:
                        return
                    if node not in parent.children:
                        return
                    idx = parent.children.index(node)

                    # splice: replace choice node with branch contents (if sequence)
                    replacement: List[Node]
                    if only_branch.node_type == NodeType.Sequence:
                        replacement = list(only_branch.children)
                    else:
                        replacement = [only_branch]

                    for r in replacement:
                        r.parent = parent

                    parent.children.pop(idx)
                    for r in reversed(replacement):
                        parent.children.insert(idx, r)

            # Flatten nested sequences
            if node.node_type == NodeType.Sequence:
                new_children: List[Node] = []
                changed = False
                for ch in node.children:
                    if ch.node_type == NodeType.Sequence and is_true(getattr(ch, "condition", None)):
                        for g in ch.children:
                            g.parent = node
                            new_children.append(g)
                        changed = True
                    else:
                        new_children.append(ch)
                if changed:
                    node.children = new_children

            # Optional: collapse Parallel with one branch
            if node.node_type == NodeType.Parallel:
                if len(node.children) == 1:
                    only_branch = node.children[0]
                    parent = node.parent
                    if parent is None:
                        return
                    if node not in parent.children:
                        return
                    idx = parent.children.index(node)
                    only_branch.parent = parent
                    parent.children[idx] = only_branch

        walk(self.tree.root)

    # -----------------------------
    # Helpers
    # -----------------------------
    def _get_activities(self, nd: Node) -> List[Node]:
        result: List[Node] = []
        if nd.node_type == NodeType.Activity:
            result.append(nd)
        elif nd.node_type in (NodeType.Sequence, NodeType.Parallel):
            for nn in nd.children:
                result.extend(self._get_activities(nn))
        elif nd.node_type in (NodeType.IChoice, NodeType.XChoice):
            # note: your original behavior only takes first branch for IChoice/XChoice
            for nn in nd.children:
                result.extend(self._get_activities(nn))
                break
        elif nd.node_type == NodeType.Loop:
            for nn in nd.children:
                if nn.node_type == NodeType.Mandatory and nn.children:
                    result.extend(self._get_activities(nn.children[0]))
                    break
        return result

    def generate_cumulative_effect(self, till: Optional[Node], exclude: Optional[Node]) -> List[List[str]]:
        pre_acts: List[List[Node]] = [[]]
        if till is None:
            return []

        pre_acts = self._get_pre_acts(self.tree.root, till, pre_acts)

        init_bases = self.bc.get_initial_state_alternatives()

        fact_bases: List[List[str]] = []
        for pre in pre_acts:
            for init_base in init_bases:
                fact_base: List[str] = list(init_base)

                for act in pre:
                    fact_base = self._remove_contradicting_precondition(act, fact_base)
                    fact_base = self._apply_effect(act, fact_base)

                fact_bases.append(list(fact_base))

        return fact_bases

    def _node_key(self, node: Node) -> str:
        nid = getattr(node, "id", None)
        if nid is not None:
            return f"id:{nid}"
        return f"{node.node_type.value}:{node.label}:{id(node)}"

    def _list_key(self, nodes: List[Node]) -> Tuple[str, ...]:
        return tuple(self._node_key(n) for n in nodes)

    def _get_pre_acts(self, seq: Node, n: Node, pre_acts: List[List[Node]]) -> List[List[Node]]:
        pre_acts_l: List[List[Node]] = []
        visited_keys: Set[Tuple[str, ...]] = set()

        comp_seq = seq if self.tree.find_path(n, seq) is not None else n.parent

        while pre_acts:
            current_list = pre_acts.pop(0)
            key = self._list_key(current_list)
            if key in visited_keys:
                continue
            visited_keys.add(key)

            first_time = True

            for nd in seq.children:
                if current_list and first_time:
                    last = current_list[-1]
                    if self.tree.get_order(last, seq) > self.tree.get_order(nd, seq):
                        continue
                    if (
                        self.tree.get_order(last, comp_seq) == self.tree.get_order(nd, comp_seq)
                        and nd.node_type == NodeType.XChoice
                    ):
                        continue
                    first_time = False

                if self.tree.get_order(nd, comp_seq) < self.tree.get_order(n, comp_seq):
                    if nd.node_type != NodeType.XChoice:
                        for v in self._get_activities(nd):
                            if v not in current_list:
                                current_list.append(v)
                    else:
                        base = list(current_list)
                        for m in nd.children:
                            pre_acts.append(list(base))
                            pre_acts_l.extend(self._get_pre_acts(m, n, [list(base)]))
                        break

                elif self.tree.get_order(nd, comp_seq) == self.tree.get_order(n, comp_seq):
                    if nd != n:
                        path = self.tree.find_path(n, nd)
                        if path and len(path) > 1:
                            pre_acts_l.extend(self._get_pre_acts(path[1], n, [current_list]))
                    else:
                        if nd.node_type == NodeType.Activity and nd not in current_list:
                            current_list.append(nd)
                        pre_acts_l.append(current_list)

            if current_list not in pre_acts_l:
                pre_acts_l.append(current_list)

        to_del: List[List[Node]] = []
        for outer in pre_acts_l:
            for inner in pre_acts_l:
                outer_s = str(outer).replace("[", "").replace("]", "")
                inner_s = str(inner).replace("[", "").replace("]", "")
                if outer_s.find(inner_s) != -1 and str(outer) != str(inner):
                    to_del.append(inner)

        return [x for x in pre_acts_l if x not in to_del]

    def _remove_contradicting_precondition(self, node: Node, fact_base: List[str]) -> List[str]:
        pre = self.bc.get_activity_data_precondition(node.label) or ""
        if not pre:
            return fact_base

        if "," in pre:
            for sss in pre.split(","):
                for s in sss.split("and"):
                    conta = self.bc.get_contradicting_state(s.strip())
                    if conta:
                        for os in conta.split(","):
                            os = os.strip()
                            if os in fact_base:
                                fact_base.remove(os)
        else:
            for s in pre.split("and"):
                conta = self.bc.get_contradicting_state(s.strip())
                if conta:
                    for os in conta.split(","):
                        os = os.strip()
                        if os in fact_base:
                            fact_base.remove(os)

        return fact_base

    def _apply_effect(self, node: Node, fact_base: List[str]) -> List[str]:
        post_p = self.bc.get_activity_data_postcondition_positive(node.label)
        post_n = self.bc.get_activity_data_postcondition_negative(node.label)

        if post_p:
            if "," in post_p:
                for sss in post_p.split(","):
                    for s in sss.split("and"):
                        s = s.strip()
                        if s and s not in fact_base:
                            fact_base.append(s)
            else:
                for s in post_p.split("and"):
                    s = s.strip()
                    if s:
                        fact_base.append(s)

        if post_n:
            if "," in post_n:
                for dis in post_n.split(","):
                    for s in dis.split("and"):
                        s = s.strip()
                        if s in fact_base:
                            fact_base.remove(s)
            else:
                for s in post_n.split("and"):
                    s = s.strip()
                    if s in fact_base:
                        fact_base.remove(s)

        fact_base.append(f"EXECUTED {node.label.replace(' ', '-')}")
        return fact_base

    # -----------------------------
    # More resolution helpers (unchanged from your original)
    # -----------------------------
    def _resolve_parallel_branches_violation(self, src: Node, dst: Node, lcp: Node) -> ProcessStructureTree:
        p_source = None
        p_destination = None
        for nd in lcp.children:
            if self.tree.find_path(src, nd) is not None:
                p_source = nd
            if self.tree.find_path(dst, nd) is not None:
                p_destination = nd

        if p_source is None or p_destination is None:
            return self.tree

        if self.tree.get_order(src, p_source) <= self.tree.get_order(dst, p_destination):
            move_before: List[Node] = []
            for nd in p_source.children:
                if self.tree.get_order(nd, p_source) <= self.tree.get_order(src, p_source):
                    move_before.append(nd)

            for nd in move_before:
                self.tree.delete_node(nd, p_source)
                self.tree.insert_node(nd, lcp.parent, self.tree.get_order(lcp, lcp.parent) - 1)
        else:
            move_after: List[Node] = []
            for nd in p_destination.children:
                if self.tree.get_order(nd, p_destination) >= self.tree.get_order(dst, p_destination):
                    move_after.append(nd)

            for nd in move_after:
                self.tree.delete_node(nd, p_destination)
                self.tree.insert_node(nd, lcp.parent, self.tree.get_order(lcp, lcp.parent) + 1)

        return self.tree

    def _handle_parallel_contradicting_node(self, parallel: Node, src: Node, contra: Node) -> bool:
        seq = parallel.parent
        seq_src = None
        seq_contra = None

        for n in parallel.children:
            if self.tree.sometime_executed(n, src.label):
                seq_src = n
            if self.tree.sometime_executed(n, contra.label):
                seq_contra = n

        if seq_src is not None:
            self.tree.delete_node(seq_src, seq_src.parent)
            for m in seq_src.children:
                self.tree.insert_node(m, seq, self.tree.get_order(parallel, seq) - 1)

        if seq_contra is not None:
            pos = self.tree.get_order(parallel, seq)
            self.tree.delete_node(seq_contra, seq_contra.parent)
            for m in seq_contra.children:
                pos += 1
                self.tree.insert_node(m, seq, pos)

        return True

    def _handle_next_contradicting_node(self, src: Node, dst: Node, contra: Node) -> bool:
        vt = self.get_violation_type_of_leads_to(src, contra)
        if vt == ViolationType.splittingChoice:
            choice = self.tree.get_enclosing_block(contra, NodeType.XChoice)
            if choice is None:
                return False
        else:
            choice = self.tree.get_previous_node(contra)

        if choice is None:
            return False

        return self._insert_choice_block_for_contradicting_activity(choice, src, dst)

    def _insert_choice_block_for_contradicting_activity(self, choice: Node, src: Node, dst: Node) -> bool:
        cumm_effect = self.generate_cumulative_effect(choice, exclude=None)
        goal_state = [f"EXECUTED {dst.label.replace(' ', '-')}"]

        p_tree: Optional[ProcessStructureTree] = None
        for ini in cumm_effect:
            p_tree = self.planner.find_plan(ini, goal_state)  # type: ignore[union-attr]
            if p_tree is None:
                break

        while p_tree is None:
            if choice == src:
                return False

            choice_before = choice
            choice = self.tree.get_previous_node(choice)
            if choice is None:
                choice = choice_before.parent.parent if choice_before.parent and choice_before.parent.parent else None
                if choice is None:
                    return False

            cumm_effect = self.generate_cumulative_effect(choice, exclude=None)
            for ini in cumm_effect:
                p_tree = self.planner.find_plan(ini, goal_state)  # type: ignore[union-attr]
                if p_tree is None:
                    break

        if p_tree is None:
            return False

        def _trim_plan_prefix(seq_node: Node, insertion_after: Node) -> Node:
            if seq_node.node_type != NodeType.Sequence:
                return seq_node

            already_done_labels = set()
            try:
                pre_lists = self._get_pre_acts(self.tree.root, insertion_after, [[]])
                for pre in pre_lists:
                    for a in pre:
                        already_done_labels.add(a.label.lower())
            except Exception:
                pass

            already_done_labels.add(src.label.lower())

            while seq_node.children:
                first = seq_node.children[0]
                if first.node_type != NodeType.Activity:
                    break
                if first.label.lower() in already_done_labels:
                    seq_node.delete_child(first)
                else:
                    break

            return seq_node

        if choice.node_type == NodeType.XChoice:
            seq = p_tree.root.clone()
            seq = _trim_plan_prefix(seq, choice)
            if not getattr(seq, "children", None):
                return True
            self.tree.insert_node(seq, choice)
            return True

        n_choice = Node(node_type=NodeType.XChoice)

        seq1 = p_tree.root.clone()
        seq1 = _trim_plan_prefix(seq1, choice)

        seq2 = Node(node_type=NodeType.Sequence)

        insert_seq2: List[Node] = []
        for n in choice.parent.children:
            if self.tree.get_order(n, choice.parent) > self.tree.get_order(choice, choice.parent):
                insert_seq2.append(n)

        self.tree.insert_node(n_choice, choice.parent, self.tree.get_order(choice, choice.parent) + 1)

        if getattr(seq1, "children", None):
            self.tree.insert_node(seq1, n_choice)
        else:
            empty_seq = Node(node_type=NodeType.Sequence, condition="true")
            self.tree.insert_node(empty_seq, n_choice)

        self.tree.insert_node(seq2, n_choice)

        for n in insert_seq2:
            self.tree.delete_node(n, choice.parent)
            self.tree.insert_node(n, seq2, len(seq2.children) + 1)

        return True

    def _handle_previous_contradicting_node(self, src: Node, dst: Node, contra: Node) -> bool:
        prev = self.tree.get_previous_node(contra)
        if prev is None:
            prev = contra.parent.parent if contra.parent and contra.parent.parent else None

        if prev is None:
            return False

        p_tree: Optional[ProcessStructureTree] = None
        init_states = self.generate_cumulative_effect(prev, exclude=None)
        final_state = [
            f"EXECUTED {dst.label.replace(' ', '-')}",
            f"!EXECUTED {contra.label.replace(' ', '-')}",
        ]

        for ini in init_states:
            p_tree = self.planner.find_plan(ini, final_state)  # type: ignore[union-attr]
            if p_tree is None:
                break

        while p_tree is None:
            if prev is None:
                return False
            if prev == src:
                return False
            prev = self.tree.get_previous_node(prev)
            if prev is None:
                return False

            init_states = self.generate_cumulative_effect(prev, exclude=None)
            for ini in init_states:
                p_tree = self.planner.find_plan(ini, final_state)  # type: ignore[union-attr]
                if p_tree is None:
                    break

        if p_tree is None:
            return False

        representative = self.tree.get_representative_node_at_level(dst, prev.level)

        p_node = Node(node_type=NodeType.Parallel)
        seq1 = Node(node_type=NodeType.Sequence)
        seq2 = self.tree.get_subsequence_after(prev)

        self.tree.insert_node(p_node, prev.parent, self.tree.get_order(prev, prev.parent) + 1)
        self.tree.insert_node(seq1, p_node)

        for mm in list(seq2.children):
            self.tree.delete_node(mm, prev.parent)
        self.tree.insert_node(seq2, p_node)

        to_delete: List[Node] = []
        for mm in seq2.children:
            if p_tree.sometime_executed(p_tree.root, mm.label):
                to_delete.append(mm)

        for n in to_delete:
            self.tree.delete_node(n, seq2)

        for n in p_tree.root.children:
            if n.label == prev.label:
                continue

            if n.node_type == NodeType.Activity:
                if self.tree.sometime_executed(representative, n.label):
                    self.tree.delete_node(representative, representative.parent)
                    self.tree.insert_node(representative, seq1, len(seq1.children) + 1)
                    break
                else:
                    self.tree.insert_node(n.clone(), seq1, len(seq1.children) + 1)
            else:
                for seq in n.children:
                    for act in seq.children:
                        if self.tree.sometime_executed(representative, act.label):
                            self.tree.delete_node(representative, representative.parent)
                            self.tree.insert_node(representative, seq1, len(seq1.children) + 1)
                            break
                        else:
                            self.tree.insert_node(act.clone(), seq1, len(seq1.children) + 1)

        for nn in p_tree.get_activities():
            to_del = None
            for mm in seq2.children:
                if mm == nn:
                    to_del = mm
            if to_del is not None:
                self.tree.delete_node(to_del, seq2)

        return True

    def find_latest_dependency_node(self, src: Node, plan: List[Node]) -> Optional[Node]:
        best_node = None

        parent = src.parent
        if parent is None or parent.get_node_type() != NodeType.Sequence:
            return None

        src_order = self.tree.get_order(src, parent)

        # look at ALL nodes after src in the sequence
        for candidate in parent.get_children():
            order = self.tree.get_order(candidate, parent)

            if order <= src_order:
                continue  # only nodes AFTER src

            # check if this block contains any planned action
            subtree_nodes = self.tree.get_subtree_nodes(candidate)

            for act in plan:
                for n in subtree_nodes:
                    if n.get_label().lower() == act.label.lower():
                        best_node = candidate  # we want the whole block
                        break

        return best_node

    def subtree_requires_activity(self, node: Node, activity_label: str) -> bool:
        """
        Returns True if any activity in subtree MUST happen AFTER activity_label.
        This includes:
          - precondition dependency
          - causal dependency via planner semantics
        """

        produced_state = self.bc.activities_postconditions_positive.get(
            activity_label.lower()
        )

        if not produced_state:
            return False

        subtree_nodes = self.tree.get_subtree_nodes(node)

        for n in subtree_nodes:
            if n.get_node_type() != NodeType.Activity:
                continue

            label = n.get_label().lower()

            # ----------------------------------------
            # 1. DIRECT PRECONDITION DEPENDENCY
            # ----------------------------------------
            pre = self.bc.activities_preconditions.get(label)
            if pre:
                required = [p.strip() for p in pre.split("and")]

                if produced_state in required:
                    return True

            # ----------------------------------------
            # 2. 🔥 PLANNER-LEVEL DEPENDENCY
            # ----------------------------------------
            # If planner needs DST before this activity
            goal = [f"EXECUTED {n.get_label().replace(' ', '-')}"]

            init_states = self.generate_cumulative_effect(None, exclude=None)

            for ini in init_states:
                plan = self.planner.find_plan(ini, goal)
                if plan:
                    acts = [a.get_label().lower() for a in plan.get_activities()]

                    if activity_label.lower() in acts:
                        return True

        return False

    def branch_satisfies_preconditions(self, branch: Node, dst_label: str) -> bool:
        subtree = self.tree.get_subtree_nodes(branch)

        produced = set()

        for n in subtree:
            if n.get_node_type() != NodeType.Activity:
                continue

            post = self.bc.activities_postconditions_positive.get(
                n.get_label().lower()
            )
            if post:
                produced.add(post)

        pre = self.bc.activities_preconditions.get(dst_label.lower())
        if not pre:
            return True

        required = [c.strip() for c in pre.split("and")]

        return all(r in produced for r in required)