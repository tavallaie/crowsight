from tree_sitter import Query
from .node import NodeWrapper
from loguru import logger


class QueryEngine:
    """Runs S-expression queries on wrapped ASTs."""

    def __init__(self, language):
        self.language = language
        logger.info(f"QueryEngine ready for {language}")

    def query(self, pattern: str, root: NodeWrapper):
        q = Query(self.language, pattern)
        caps = q.captures(root._node)
        logger.debug(f"Query returned {len(caps)} captures")
        return [(name, NodeWrapper(n, root.source)) for n, name in caps]
