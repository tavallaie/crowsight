from tree_sitter import Parser
from .node import NodeWrapper
from loguru import logger


class ParserEngine:
    """Parses raw bytes into a wrapped AST via tree-sitter."""

    def __init__(self, ts_parser: Parser):
        self._parser = ts_parser
        logger.info(f"ParserEngine initialized for {ts_parser!r}")

    def parse(self, source: bytes) -> NodeWrapper:
        tree = self._parser.parse(source)
        logger.debug("Parsed AST")
        return NodeWrapper(tree.root_node, source)

    # High-level helpers (delegate to tree-walking code)
    def find_functions(self, root: NodeWrapper):
        results = []
        for node in root.descendants():
            if node.type == "function_definition":
                name = node.field("name").text
                params = node.field("parameters")
                count = 0
                if params:
                    count = sum(
                        1 for c in params.descendants() if c.type == "identifier"
                    )
                results.append({"name": name, "arg_count": count, "node": node})
        return results

    def find_imports(self, root: NodeWrapper):
        results = []
        for node in root.descendants():
            if node.type == "import_statement":
                results.extend(
                    c.text for c in node.descendants() if c.type == "dotted_name"
                )
            elif node.type == "import_from_statement":
                mod = node.field("module")
                names = node.field("names")
                if mod and names:
                    m = mod.text
                    results.extend(
                        f"{m}.{c.text}"
                        for c in names.descendants()
                        if c.type == "identifier"
                    )
        return results

    def find_calls(self, root: NodeWrapper):
        return [
            {"called": c.text, "node": c}
            for c in root.descendants()
            if c.type == "call_expression"
        ]

    def find_classes(self, root: NodeWrapper):
        results = []
        for node in root.descendants():
            if node.type == "class_definition":
                name = node.field("name").text
                bases = node.field("superclasses")
                b = (
                    [c.text for c in bases.descendants() if c.type == "identifier"]
                    if bases
                    else []
                )
                results.append({"name": name, "bases": b, "node": node})
        return results
