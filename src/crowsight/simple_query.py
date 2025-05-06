from tree_sitter import Query
from .node_wrapper import NodeWrapper

class SimpleQuery:
    def __init__(self, language):
        """
        language: a tree_sitter.Language object
        """
        self.language = language

    def run(self, pattern: str, wrapped_root: NodeWrapper):
        """
        Execute a raw S-expression pattern across the AST.
        Returns a list of (capture_name, NodeWrapper) pairs.
        """
        q = Query(self.language, pattern)
        captures = q.captures(wrapped_root._node)
        return [(name, NodeWrapper(n, wrapped_root.source)) for n, name in captures]
