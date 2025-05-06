from tree_sitter import Node
from loguru import logger


class NodeWrapper:
    """Wraps a tree-sitter Node and its source bytes."""

    def __init__(self, node: Node, source: bytes):
        self._node = node
        self.source = source
        logger.trace(f"Wrapped node {node.type}")

    @property
    def type(self) -> str:
        return self._node.type

    @property
    def text(self) -> str:
        return self.source[self._node.start_byte : self._node.end_byte].decode("utf8")

    @property
    def children(self):
        return [NodeWrapper(c, self.source) for c in self._node.children]

    def descendants(self):
        yield self
        for child in self.children:
            yield from child.descendants()

    def field(self, name: str):
        c = self._node.child_by_field_name(name)
        return NodeWrapper(c, self.source) if c else None
