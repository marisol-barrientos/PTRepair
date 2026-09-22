from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class NodeType(str, Enum):
    Sequence = "Sequence"
    Parallel = "Parallel"
    Activity = "Activity"
    XChoice = "XChoice"
    IChoice = "IChoice"
    Loop = "Loop"
    Mandatory = "Mandatory"
    Optional = "Optional"


@dataclass
class Node:
    """
    Python equivalent of com.pst.Node (Java).

    Notes:
    - Java uses `ID` for equality. We do the same via `id`.
    - Java uses `childrenStar` as a cached subtree-size metric. We keep it too.
    - Java's setCondition applies only if nodeType == Sequence; same here.
    - Java's setLoopCondition/setExitCondition apply only if nodeType == Loop; same here.
    """

    label: str = ""
    level: int = 0
    parent: Optional["Node"] = None
    children: List["Node"] = field(default_factory=list)

    # Java: ID
    id: int = 0

    # Conditions
    condition: str = ""
    exit_condition: str = ""
    loop_condition: str = ""

    # Java: childrenStar
    children_star: int = 0

    node_type: Optional[NodeType] = None

    # -------------------------
    # Type getters/setters
    # -------------------------
    def get_node_type(self) -> Optional[NodeType]:
        return self.node_type

    def set_node_type(self, nd: NodeType) -> None:
        self.node_type = nd

    # -------------------------
    # Label
    # -------------------------
    def get_label(self) -> str:
        return self.label

    def set_label(self, l: str) -> None:
        self.label = l

    # -------------------------
    # Conditions (match Java restrictions)
    # -------------------------
    def get_condition(self) -> str:
        return self.condition

    def set_condition(self, l: str) -> None:
        # Java: if (nodeType == Sequence) condition = l;
        if self.node_type == NodeType.Sequence:
            self.condition = l

    def get_loop_condition(self) -> str:
        return self.loop_condition

    def set_loop_condition(self, l: str) -> None:
        # Java: only if Loop
        if self.node_type == NodeType.Loop:
            self.loop_condition = l

    def get_exit_condition(self) -> str:
        return self.exit_condition

    def set_exit_condition(self, l: str) -> None:
        # Java: only if Loop
        if self.node_type == NodeType.Loop:
            self.exit_condition = l

    # -------------------------
    # Parent / level
    # -------------------------
    def get_level(self) -> int:
        return self.level

    def set_level(self, l: int) -> None:
        self.level = l

    def set_parent(self, p: Optional["Node"]) -> None:
        self.parent = p

    def get_parent(self) -> Optional["Node"]:
        return self.parent

    # -------------------------
    # Identity / equality
    # -------------------------
    def get_id(self) -> int:
        return self.id

    def set_id(self, nid: int) -> None:
        self.id = nid

    def __eq__(self, other: object) -> bool:
        # Java: equals uses ID only
        if not isinstance(other, Node):
            return False
        return other.id == self.id

    # -------------------------
    # Subtree size metric
    # -------------------------
    def get_children_star_count(self) -> int:
        return self.children_star

    # -------------------------
    # Children operations
    # -------------------------
    def add_child(self, c: "Node", pos: Optional[int] = None) -> None:
        """
        Java has:
          - addChild(Node c) appends
          - addChild(Node c, int pos) inserts at (pos-1) with 1-based index,
            except when empty list -> just add.

        In Python:
          - if pos is None: append
          - else: insert at pos-1 (1-based), with same empty-list behavior.
        """
        if pos is None:
            self.children.append(c)
        else:
            if len(self.children) == 0:
                self.children.append(c)
            else:
                # pos is 1-based, Java: children.add(pos-1, c)
                idx = max(0, pos - 1)
                if idx > len(self.children):
                    # Java would throw; we choose to append for robustness
                    self.children.append(c)
                else:
                    self.children.insert(idx, c)

        c.set_parent(self)

        # Java: childrenStar += 1 + c.getChildrenStarCount()
        self.children_star += 1 + c.get_children_star_count()

    def get_children(self) -> List["Node"]:
        return self.children

    def delete_child(self, child: "Node") -> None:
        """
        Java:
          if (this.children.remove(child)) {
              childrenStar -= (1 + child.getChildren().size());
          }

        Note: Java subtracts (1 + directChildrenCount), NOT child.childrenStarCount.
        That's slightly inconsistent, but we keep it identical.
        """
        try:
            self.children.remove(child)
            self.children_star -= 1 + len(child.get_children())
        except ValueError:
            pass

    def clear_children(self) -> None:
        self.children.clear()

    def copy_children(self) -> List["Node"]:
        """
        Java: returns clone() of each child
        """
        return [n.clone() for n in self.children]

    # -------------------------
    # Clone (deep copy)
    # -------------------------
    def clone(self) -> "Node":
        cln = Node()
        cln.set_node_type(self.node_type)  # type: ignore[arg-type]
        cln.condition = self.condition
        cln.exit_condition = self.exit_condition
        cln.loop_condition = self.loop_condition
        cln.label = self.label
        cln.id = self.id
        cln.level = self.level

        # Deep copy children
        for nd in self.children:
            cln.add_child(nd.clone())

        return cln

    # -------------------------
    # String representation (Java toString)
    # -------------------------
    def __str__(self) -> str:
        nt = self.node_type
        label = self.label or ""
        cond = getattr(self, "condition", None) or ""

        # helper to append condition nicely
        def with_cond(text: str) -> str:
            if cond:
                return f"{text} [cond: {cond}]"
            return text

        if nt == NodeType.Activity:
            base = f"Activity({label})"
            return with_cond(base)

        if nt == NodeType.IChoice:
            return with_cond("Inclusive Choice Block")

        if nt == NodeType.Loop:
            return with_cond("Loop Block")

        if nt == NodeType.Mandatory:
            return with_cond("Mandatory part of the loop")

        if nt == NodeType.Optional:
            return with_cond("Optional part of the loop")

        if nt == NodeType.Parallel:
            return with_cond("Parallel Block")

        if nt == NodeType.Sequence:
            return with_cond("Sequence Block")

        # XChoice or unknown
        return with_cond("Exclusive Choice Block")

    def clone_subtree(self) -> "Node":
        # create shallow copy of current node
        new_node = Node(
            label=self.label,
            node_type=self.node_type,
            condition=getattr(self, "condition", None)
        )

        # recursively copy children
        new_node.children = []
        for child in getattr(self, "children", []):
            cloned_child = child.clone_subtree()
            cloned_child.parent = new_node
            new_node.children.append(cloned_child)

        return new_node