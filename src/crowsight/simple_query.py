from tree_sitter import Query
from .node_wrapper import NodeWrapper
from loguru import logger


class SimpleQuery:
    def __init__(self, language):
        """
        language: a tree_sitter.Language object
        """
        self.language = language
        logger.info(f"SimpleQuery initialized for language '{language.name}'")

    def run(self, pattern: str, wrapped_root: NodeWrapper):
        """
        Execute a raw S-expression Query across the AST.
        Returns: list of (capture_name, NodeWrapper) tuples.
        """
        logger.debug(f"Running raw query:\n{pattern.strip()}")
        q = Query(self.language, pattern)
        captures = q.captures(wrapped_root._node)
        logger.debug(f"Query returned {len(captures)} captures")
        return [(name, NodeWrapper(n, wrapped_root.source)) for n, name in captures]
