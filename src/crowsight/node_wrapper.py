from tree_sitter import Node
from loguru import logger


class NodeWrapper:
    def __init__(self, node: Node, source: bytes):
        self._node = node
        self.source = source
        logger.debug(f"Wrapped node '{node.type}' [{node.start_byte}:{node.end_byte}]")

    @property
    def type(self) -> str:
        return self._node.type

    @property
    def text(self) -> str:
        text = self.source[self._node.start_byte : self._node.end_byte].decode()
        return text

    @property
    def children(self) -> list["NodeWrapper"]:
        return [NodeWrapper(c, self.source) for c in self._node.children]

    def descendants(self):
        """Yield self and all descendant nodes (pre-order)."""
        yield self
        for child in self.children:
            logger.trace(f"Descending into child '{child.type}'")
            yield from child.descendants()

    def field(self, name: str) -> "NodeWrapper | None":
        """Return the named child field, or None if absent."""
        c = self._node.child_by_field_name(name)
        if c:
            logger.trace(f"Accessing field '{name}' on node '{self.type}'")
            return NodeWrapper(c, self.source)
        return None
