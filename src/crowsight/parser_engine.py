from tree_sitter import Parser
from .node_wrapper import NodeWrapper

class ParserEngine:
    def __init__(self, ts_parser: Parser):
        # ts_parser from tree-sitter-language-pack.get_parser(lang)
        self._parser = ts_parser

    def parse_wrapped(self, code: bytes) -> NodeWrapper:
        """Parse bytes and return a wrapped root node."""
        tree = self._parser.parse(code)
        return NodeWrapper(tree.root_node, code)

    def find_functions(self, wrapped_root: NodeWrapper, min_args: int = 0):
        results = []
        for node in wrapped_root.descendants():
            if node.type == "function_definition":
                params = node.field("parameters")
                count = sum(1 for c in params.descendants() if c.type == "identifier") if params else 0
                if count >= min_args:
                    name = node.field("name").text
                    results.append({"name": name, "arg_count": count, "node": node})
        return results

    def find_calls(self, wrapped_root: NodeWrapper):
        results = []
        for node in wrapped_root.descendants():
            if node.type == "call_expression":
                fn = node.field("function")
                results.append({"called": fn.text if fn else None, "node": node})
        return results

    def find_imports(self, wrapped_root: NodeWrapper):
        results = []
        for node in wrapped_root.descendants():
            if node.type == "import_statement":
                mods = [c.text for c in node.descendants() if c.type == "dotted_name"]
                results.extend(mods)
            elif node.type == "import_from_statement":
                module = node.field("module").text
                names = [c.text for c in node.field("names").descendants() if c.type == "identifier"]
                results.extend(f"{module}.{n}" for n in names)
        return results

    def find_classes(self, wrapped_root: NodeWrapper):
        results = []
        for node in wrapped_root.descendants():
            if node.type == "class_definition":
                name = node.field("name").text
                bases_node = node.field("superclasses")
                bases = [c.text for c in bases_node.descendants() if c.type == "identifier"] if bases_node else []
                results.append({"name": name, "bases": bases, "node": node})
        return results
