class PSTNode:
    def __init__(
        self,
        label,
        node_type,
        children=None,
        branch_type=None,
        condition=None,
        data=None,
        resource=None,
        time=None,
        time_type=None
    ):
        self.label = label
        self.node_type = node_type
        self.children = children or []
        self.branch_type = branch_type
        self.condition = condition
        self.data = data or {"read": [], "write": []}
        self.resource = resource or []
        self.time = time
        self.time_type = time_type
        self.parallel = None

        # 🔥 NEW: temporal semantics
        self.time_links = {
            "affects": [],     # activities cancelled / constrained
            "triggers": None   # activity triggered after timeout
        }

    def add_child(self, child):
        if child:
            child.parent = self
            self.children.append(child)

    def __repr__(self):
        return f"{self.node_type.upper()}({self.label})"