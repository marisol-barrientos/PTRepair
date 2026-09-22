from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import xml.etree.ElementTree as ET

from src.model.node import Node, NodeType


@dataclass
class ProcessStructureTree:
    """
    Python equivalent of com.pst.ProcessStructureTree (Java).

    This class maintains:
      - root: Node
      - nodes: flat list of all nodes in the tree (like Java)
      - a static-like id counter for assigning new IDs
    """

    root: Optional[Node] = None
    nodes: List[Node] = field(default_factory=list)

    _id_counter: int = 0

    # -------------------------
    # ID assignment (static in Java)
    # -------------------------
    def _get_next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    # -------------------------
    # Constructors analogs
    # -------------------------
    @classmethod
    def from_root(cls, r: Node) -> "ProcessStructureTree":
        pst = cls()
        pst.root = r
        r.set_id(pst._get_next_id())
        r.set_level(0)
        pst.nodes = [r]
        return pst

    # -------------------------
    # Basic insert operations
    # -------------------------
    def insert_node_basic(self, child: Node, parent: Node) -> None:
        if parent in self.nodes:
            child.set_id(self._get_next_id())
            child.set_level(parent.get_level() + 1)
            parent.add_child(child)
            self.nodes.append(child)

    def insert_node(self, child: Node, parent: Node, pos: Optional[int] = None) -> None:
        """
        Java has:
          insertNode(child,parent)  -> insertNodeBasic + processChilNodes(child)
          insertNode(child,parent,pos) -> assigns id, parent.addChild(child,pos), nodes.add(child), processChilNodes(child)

        We support both with `pos` optional.
        """
        if parent not in self.nodes:
            return

        if pos is None:
            self.insert_node_basic(child, parent)
        else:
            child.set_id(self._get_next_id())
            # Java doesn't set level here explicitly (bug/oversight), but it should;
            # we set it to match insert_node_basic behavior.
            child.set_level(parent.get_level() + 1)
            parent.add_child(child, pos=pos)
            self.nodes.append(child)

        if child in self.nodes:
            self._process_child_nodes(child)

    def _process_child_nodes(self, p: Node) -> None:
        """
        Java: processChilNodes(child)
        It copies children, clears children, then re-inserts them via insertNodeBasic
        so they get IDs/levels and the nodes list is populated.
        """
        more_nodes: List[Node] = []
        current_node: Node = p
        more_nodes.extend(current_node.get_children())

        while len(more_nodes) > 0:
            children = current_node.copy_children()
            current_node.clear_children()

            for nd in children:
                more_nodes.extend(nd.get_children())
                self.insert_node_basic(nd, current_node)

            if len(more_nodes) > 0:
                current_node = more_nodes.pop(0)

    # -------------------------
    # Path / order / LCP
    # -------------------------
    def find_path(self, ch: Node, pa: Node) -> Optional[List[Node]]:
        result: List[Node] = [ch]
        tmp = ch.get_parent()
        if tmp is None:
            return None

        while tmp != pa:
            result.insert(0, tmp)
            tmp = tmp.get_parent()
            if tmp is None:
                return None

        result.insert(0, pa)
        return result

    def find_path_to_root(self, some_child: Node) -> List[Node]:
        result: List[Node] = [some_child]
        tmp = some_child.get_parent()
        while tmp is not None:
            result.insert(0, tmp)
            tmp = tmp.get_parent()
        return result

    def least_common_parent(self, a: Node, b: Node) -> Optional[Node]:
        if a not in self.nodes or b not in self.nodes:
            return None

        path1 = self.find_path_to_root(a)
        path2 = self.find_path_to_root(b)

        s1, s2 = len(path1), len(path2)

        if s1 < s2:
            for i in range(s1 - 1, -1, -1):
                if path1[i] in path2:
                    return path1[i]
        else:
            for i in range(s2 - 1, -1, -1):
                if path2[i] in path1:
                    return path2[i]

        return self.root

    def get_order(self, ch: Node, pa: Node) -> int:
        """
        Java:
          - if ch==pa -> -1
          - if either not in nodes -> -1
          - if parent not Sequence -> 0
          - findPath(ch,pa) returns list; order is position of result[1] among pa.children (1-based)
        """
        if ch == pa:
            return -1
        if ch not in self.nodes or pa not in self.nodes:
            return -1
        if pa.get_node_type() != NodeType.Sequence:
            return 0

        result = self.find_path(ch, pa)
        if result is None:
            return -1

        # result[1] is the node directly under pa on the path
        if len(result) < 2:
            return -1

        cnt = 1
        for child in pa.get_children():
            if child == result[1]:
                return cnt
            cnt += 1
        return 0

    # -------------------------
    # Queries
    # -------------------------
    def get_occurrences_of_label(self, label: str) -> List[Node]:
        res: List[Node] = []
        for n in self.nodes:
            if n.get_label().lower() == label.lower():
                res.append(n)
        return res

    def get_activities(self) -> List[Node]:
        return [n for n in self.nodes if n.get_node_type() == NodeType.Activity]

    # -------------------------
    # Clone
    # -------------------------
    def _complete_cloning(self, n: Node, parent: Optional[Node]) -> None:
        n.set_parent(parent)
        if n not in self.nodes:
            self.nodes.append(n)
        for nd in n.get_children():
            self._complete_cloning(nd, n)

    def clone(self) -> "ProcessStructureTree":
        if self.root is None:
            return ProcessStructureTree()

        new_root = self.root.clone()
        new_tree = ProcessStructureTree()
        new_tree.root = new_root
        new_tree._id_counter = self._id_counter

        # keep same root id as Java does
        new_tree.root.set_id(self.root.get_id())
        new_tree._complete_cloning(new_tree.root, None)
        return new_tree

    # -------------------------
    # Execution checks
    # -------------------------
    def always_executed(self, block: Node, label: str) -> bool:
        nt = block.get_node_type()
        if nt == NodeType.Activity:
            return block.get_label().lower() == label.lower()

        if nt in (NodeType.Sequence, NodeType.Parallel):
            for nd in block.get_children():
                if self.always_executed(nd, label):
                    return True
            return False

        if nt in (NodeType.XChoice, NodeType.IChoice):
            for nd in block.get_children():
                if not self.always_executed(nd, label):
                    return False
            return True

        # loop
        kids = block.get_children()
        if not kids:
            return False
        if kids[0].get_node_type() == NodeType.Mandatory:
            return self.always_executed(kids[0].get_children()[0], label)
        return self.always_executed(kids[1].get_children()[0], label)

    def sometime_executed(self, block: Node, label: str) -> bool:
        nt = block.get_node_type()
        if nt == NodeType.Activity:
            return block.get_label().lower() == label.lower()

        if nt in (NodeType.Sequence, NodeType.XChoice, NodeType.IChoice, NodeType.Parallel):
            for nd in block.get_children():
                if self.sometime_executed(nd, label):
                    return True
            return False

        # loop
        kids = block.get_children()
        if not kids:
            return False
        if kids[0].get_node_type() == NodeType.Mandatory:
            return self.sometime_executed(kids[0].get_children()[0], label)
        return self.sometime_executed(kids[1].get_children()[0], label)

    # -------------------------
    # Subsequence helpers
    # -------------------------
    def get_subsequence_after(self, n: Node) -> Node:
        subseq = n.get_parent().clone()
        to_delete: List[Node] = []
        for m in subseq.get_children():
            if self.get_order(m, subseq) <= self.get_order(n, n.get_parent()):
                to_delete.append(m)
        for d in to_delete:
            subseq.delete_child(d)
        return subseq

    def get_subsequence_before(self, n: Node) -> Node:
        subseq = n.get_parent().clone()
        to_delete: List[Node] = []
        for m in subseq.get_children():
            if self.get_order(m, subseq) >= self.get_order(n, n.get_parent()):
                to_delete.append(m)
        for d in to_delete:
            subseq.delete_child(d)
        return subseq

    def get_supersequence_of(self, seq: Node) -> List[Node]:
        """
        Returns sequence nodes that contain seq as an ordered subsequence.
        More robust than Java's string hack.
        """

        def normalize(label):
            return label.lower()

        # extract labels of target sequence
        target_labels = [
            normalize(n.label)
            for n in seq.get_children()
            if hasattr(n, "label")
        ]

        result = []

        for n in self.nodes:
            if n.get_node_type() != NodeType.Sequence:
                continue

            candidate_labels = [
                normalize(c.label)
                for c in n.get_children()
                if hasattr(c, "label")
            ]

            # check subsequence (order preserved)
            i = 0
            for lbl in candidate_labels:
                if i < len(target_labels) and lbl == target_labels[i]:
                    i += 1

            if i == len(target_labels):
                result.append(n)

        return result

    # -------------------------
    # Delete
    # -------------------------
    def delete_node(self, ch: Node, parent: Node) -> None:
        if parent not in self.nodes:
            return

        parent.delete_child(ch)

        more_nodes: List[Node] = []
        current_node: Node = ch
        more_nodes.extend(current_node.get_children())

        while len(more_nodes) > 0:
            if current_node in self.nodes:
                self.nodes.remove(current_node)

            for nd in current_node.get_children():
                more_nodes.extend(nd.get_children())

            if len(more_nodes) > 0:
                current_node = more_nodes.pop(0)

    # -------------------------
    # Neighbor navigation
    # -------------------------
    def get_next_node(self, n: Node) -> Optional[Node]:
        if n.get_parent() is None or n.get_parent().get_node_type() != NodeType.Sequence:
            return None
        parent = n.get_parent()
        for nn in parent.get_children():
            if self.get_order(nn, parent) > self.get_order(n, parent):
                return nn
        return None

    def get_previous_node(self, n: Node) -> Optional[Node]:
        if n.get_parent() is None or n.get_parent().get_node_type() != NodeType.Sequence:
            return None
        parent = n.get_parent()
        candidate = None
        for nn in parent.get_children():
            if self.get_order(nn, parent) < self.get_order(n, parent):
                candidate = nn
        return candidate

    def get_enclosing_block(self, n: Node, nt: NodeType) -> Optional[Node]:
        parent = n.get_parent()
        while parent is not None:
            if parent.get_node_type() == nt:
                return parent
            parent = parent.get_parent()
        return None

    def get_representative_node_at_level(self, ch: Node, level: int) -> Optional[Node]:
        if ch.get_level() < level:
            return None
        if ch.get_level() == level:
            return ch
        if ch.get_parent() is None:
            return None
        return self.get_representative_node_at_level(ch.get_parent(), level)

    # -------------------------
    # Printing
    # -------------------------
    def _depth_first(self, nd: Node, depth: int) -> str:
        result = ("\t" * depth) + str(nd) + "\n"
        for child in nd.get_children():
            result += self._depth_first(child, depth + 1)
        return result

    def print_tree(self) -> str:
        if self.root is None:
            return ""
        return self._depth_first(self.root, 0)

    # -------------------------
    # XML loading (PST XML format)
    # -------------------------
    def load_tree_from_file(self, file_name: str) -> None:
        doc = self._parse_file(file_name)
        if doc is None:
            raise ValueError(f"Could not parse XML: {file_name}")

        xml_root = doc.getroot()

        p_root = Node(node_type=NodeType.Sequence)
        self.root = p_root
        self.root.set_id(self._get_next_id())
        self.root.set_level(0)
        self.nodes = [p_root]

        for child in list(xml_root):
            self._handle_subtree(self.root, child)

    def _parse_file(self, file_name: str) -> Optional[ET.ElementTree]:
        try:
            return ET.parse(str(Path(file_name)))
        except Exception:
            return None

    def _handle_subtree(self, current_parent: Node, xml_node: ET.Element) -> None:
        tag = xml_node.tag.upper()

        if tag == "SEQUENCE":
            p_child = self._handle_sequence_node(xml_node)
            self.insert_node(p_child, current_parent)
            for child in list(xml_node):
                self._handle_subtree(p_child, child)

        elif tag == "ACTIVITY":
            p_child = self._handle_activity_node(xml_node)
            self.insert_node(p_child, current_parent)

        elif tag == "XCHOICE":
            p_child = self._handle_xchoice_node(xml_node)
            self.insert_node(p_child, current_parent)
            for child in list(xml_node):
                self._handle_subtree(p_child, child)

        elif tag == "ICHOICE":
            p_child = self._handle_ichoice_node(xml_node)
            self.insert_node(p_child, current_parent)
            for child in list(xml_node):
                self._handle_subtree(p_child, child)

        elif tag == "PARALLEL":
            p_child = self._handle_parallel_node(xml_node)
            self.insert_node(p_child, current_parent)
            for child in list(xml_node):
                self._handle_subtree(p_child, child)

        else:
            # ignore unknown tags
            return

    def _handle_sequence_node(self, nd: ET.Element) -> Node:
        result = Node(node_type=NodeType.Sequence)
        if "condition" in nd.attrib:
            result.set_condition(nd.attrib["condition"])
        if "label" in nd.attrib:
            result.set_label(nd.attrib["label"])
        return result

    def _handle_xchoice_node(self, nd: ET.Element) -> Node:
        return Node(node_type=NodeType.XChoice)

    def _handle_ichoice_node(self, nd: ET.Element) -> Node:
        return Node(node_type=NodeType.IChoice)

    def _handle_parallel_node(self, nd: ET.Element) -> Node:
        return Node(node_type=NodeType.Parallel)

    def _handle_activity_node(self, nd: ET.Element) -> Node:
        result = Node(node_type=NodeType.Activity)
        if "condition" in nd.attrib:
            # Java mistakenly calls setCondition for Activity but it only sets for Sequence.
            # We mimic Java by setting directly (else you'd lose this info).
            result.condition = nd.attrib["condition"]
        if "label" in nd.attrib:
            result.set_label(nd.attrib["label"])
        return result

    # -------------------------
    # Normalization
    # -------------------------
    def normalize_tree(self) -> None:
        result = self._normalize_control_flow()
        while result:
            result = self._normalize_control_flow()

    def _normalize_control_flow(self) -> bool:
        to_delete: List[Node] = []
        clones: List[Node] = [n.clone() for n in self.nodes]

        for n in clones:
            # find equivalent node by ID
            eq_node = None
            for s in self.nodes:
                if s == n:
                    eq_node = s
                    break
            if eq_node is None:
                continue

            nt = n.get_node_type()

            if nt in (NodeType.Parallel, NodeType.XChoice, NodeType.IChoice):
                if len(n.get_children()) == 1:
                    only = n.get_children()[0]
                    for c in only.get_children():
                        self.insert_node(c, eq_node.get_parent(), self.get_order(eq_node, eq_node.get_parent()))
                    to_delete.append(eq_node)
                elif len(n.get_children()) == 0:
                    to_delete.append(eq_node)

            elif nt == NodeType.Sequence:
                if len(n.get_children()) == 0:
                    to_delete.append(eq_node)

        something_deleted = False
        for d in to_delete:
            if d.get_parent() is None:
                continue
            self.delete_node(d, d.get_parent())
            something_deleted = True

        return something_deleted

    def get_subtree_nodes(self, node: Node) -> List[Node]:
        """
        Returns all nodes in the subtree rooted at `node` (including itself).
        """
        result = []

        def dfs(n: Node):
            result.append(n)
            for c in n.get_children():
                dfs(c)

        dfs(node)
        return result
