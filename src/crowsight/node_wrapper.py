
from tree_sitter import Node

class NodeWrapper:
    def __init__(self, node: Node, source: bytes):
        self._node = node
        self.source = source

    @property
    def type(self) -> str:
        return self._node.type

    @property
    def text(self) -> str:
        return self.source[self._node.start_byte:self._node.end_byte].decode()

    @property
    def children(self) -> list["NodeWrapper"]:
        return [NodeWrapper(c, self.source) for c in self._node.children]

    def descendants(self):
        """Yield self and all descendant nodes (pre-order)."""
        yield self
        for child in self.children:
            yield from child.descendants()

    def field(self, name: str) -> "NodeWrapper | None":
        """Return the named child field, or None if absent."""
        c = self._node.child_by_field_name(name)
        return NodeWrapper(c, self.source) if c else None