from tree_sitter import Parser
from .node_wrapper import NodeWrapper
from loguru import logger


class ParserEngine:
    def __init__(self, ts_parser: Parser):
        """
        ts_parser: a preconfigured tree_sitter.Parser (from get_parser).
        """
        self._parser = ts_parser
        logger.info(f"Initialized ParserEngine for {ts_parser.language.name}")

    def parse_wrapped(self, code: bytes) -> NodeWrapper:
        """
        Parse raw bytes into an AST, then wrap the root node.
        """
        logger.debug("Parsing code into AST")
        tree = self._parser.parse(code)
        logger.debug("AST parsing complete")
        return NodeWrapper(tree.root_node, code)

    def find_functions(self, wrapped_root: NodeWrapper, min_args: int = 0):
        results = []
        logger.debug(f"Finding functions with ≥{min_args} args")
        for node in wrapped_root.descendants():
            if node.type == "function_definition":
                params = node.field("parameters")
                count = (
                    sum(1 for c in params.descendants() if c.type == "identifier")
                    if params
                    else 0
                )
                if count >= min_args:
                    name = node.field("name").text
                    logger.trace(f"Found function '{name}' with {count} args")
                    results.append({"name": name, "arg_count": count, "node": node})
        return results

    def find_calls(self, wrapped_root: NodeWrapper):
        logger.debug("Finding call expressions")
        results = []
        for node in wrapped_root.descendants():
            if node.type == "call_expression":
                fn = node.field("function")
                called = fn.text if fn else None
                logger.trace(f"Found call to '{called}'")
                results.append({"called": called, "node": node})
        return results

    def find_imports(self, wrapped_root: NodeWrapper):
        logger.debug("Finding import statements")
        results = []
        for node in wrapped_root.descendants():
            if node.type == "import_statement":
                mods = [c.text for c in node.descendants() if c.type == "dotted_name"]
                logger.trace(f"Found imports {mods}")
                results.extend(mods)
            elif node.type == "import_from_statement":
                module = node.field("module").text
                names = [
                    c.text
                    for c in node.field("names").descendants()
                    if c.type == "identifier"
                ]
                full = [f"{module}.{n}" for n in names]
                logger.trace(f"Found from-imports {full}")
                results.extend(full)
        return results

    def find_classes(self, wrapped_root: NodeWrapper):
        logger.debug("Finding class definitions")
        results = []
        for node in wrapped_root.descendants():
            if node.type == "class_definition":
                name = node.field("name").text
                bases_node = node.field("superclasses")
                bases = (
                    [c.text for c in bases_node.descendants() if c.type == "identifier"]
                    if bases_node
                    else []
                )
                logger.trace(f"Found class '{name}' bases={bases}")
                results.append({"name": name, "bases": bases, "node": node})
        return results
