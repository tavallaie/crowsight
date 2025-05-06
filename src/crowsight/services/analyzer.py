# src/crowsight/services/analyzer.py

from pathlib import Path
from typing import Union, List, Dict, Any, Tuple
import re
from loguru import logger
from tree_sitter_language_pack import get_parser

from ..core.parser import ParserEngine
from ..core.node import NodeWrapper
from ..cache.manifest import ManifestStore
from ..filters.node_filter import NodeCategory

# 1) Language → Extensions grouping
LANG_EXT_MAP: Dict[str, List[str]] = {
    "actionscript": ["as"],
    "ada": ["adb", "ads"],
    "agda": ["agda"],
    "apex": ["cls", "trigger"],
    "arduino": ["ino"],
    "asm": ["s", "asm"],
    "astro": ["astro"],
    "bash": ["sh", "bash", "zsh"],
    "beancount": ["bean"],
    "bibtex": ["bib"],
    "bicep": ["bicep"],
    "bitbake": ["bb", "bbappend"],
    "c": ["c", "h"],
    "cairo": ["cairo"],
    "capnp": ["capnp"],
    "chatito": ["chatito"],
    "clarity": ["clarity"],
    "clojure": ["clj", "cljs", "cljc"],
    "cmake": ["cmake", "CMakeLists.txt"],
    "commonlisp": ["lisp", "lsp"],
    "cpp": ["cpp", "cc", "cxx", "C", "hpp", "hh", "hxx"],
    "csharp": ["cs"],
    "css": ["css", "pcss", "postcss"],
    "csv": ["csv"],
    "cuda": ["cu", "cuh"],
    "dart": ["dart"],
    "dockerfile": ["Dockerfile"],
    "doxygen": ["dox"],
    "dtd": ["dtd"],
    "elisp": ["el"],
    "elixir": ["ex", "exs"],
    "elm": ["elm"],
    "embeddedtemplate": ["eex", "heex"],
    "erlang": ["erl", "hrl"],
    "fennel": ["fnl"],
    "firrtl": ["fir", "firrtl"],
    "fish": ["fish"],
    "fortran": ["f90", "f95", "f03", "f08", "f77", "for", "f"],
    "gdscript": ["gd", "gdscript"],
    "gitcommit": ["gitcommit"],
    "gitignore": ["gitignore"],
    "gleam": ["gleam"],
    "glsl": ["glsl", "vert", "frag", "geom", "comp"],
    "go": ["go", "mod", "sum"],
    "groovy": ["groovy", "gradle"],
    "haskell": ["hs", "lhs"],
    "hcl": ["hcl", "tf"],
    "html": ["html", "htm"],
    "java": ["java", "jsp"],
    "javascript": ["js", "jsx", "mjs", "cjs"],
    "jsdoc": ["jsdoc"],
    "json": ["json"],
    "jsonnet": ["jsonnet"],
    "julia": ["jl"],
    "kotlin": ["kt", "kts"],
    "latex": ["tex", "latex", "ltx"],
    "lua": ["lua", "luadoc"],
    "make": ["mk", "makefile"],
    "markdown": ["md", "markdown", "mkd"],
    "matlab": ["m"],
    "nix": ["nix"],
    "ocaml": ["ml", "mli"],
    "org": ["org"],
    "perl": ["pl", "pm", "t"],
    "php": ["php", "phtml", "php3", "php4", "php5", "phps"],
    "powershell": ["ps1", "psm1", "psd1"],
    "protocolbuffers": ["proto"],
    "python": ["py", "pyw", "cpy", "gyp", "rpy"],
    "r": ["r", "R", "Rmd"],
    "racket": ["rkt", "rktd", "plt", "scrbl"],
    "ruby": ["rb", "erb", "rake", "gemspec"],
    "rust": ["rs", "rs.in"],
    "scala": ["scala", "sc"],
    "scss": ["scss"],
    "sql": ["sql", "psql", "ddl"],
    "swift": ["swift"],
    "toml": ["toml"],
    "tsx": ["tsx"],
    "typescript": ["ts"],
    "vue": ["vue"],
    "xml": ["xml", "xsd", "wsdl"],
    "yaml": ["yml", "yaml"],
    "zig": ["zig"],
}

# 2) Invert to Extension → Language
EXT_LANG_MAP: Dict[str, str] = {
    ext.lower(): lang for lang, exts in LANG_EXT_MAP.items() for ext in exts
}

# 3) NodeCategory → grammar types
CATEGORY_MAP = {
    NodeCategory.FUNCTION: [
        "function_definition",
        "function_declaration",
        "method_declaration",
    ],
    NodeCategory.IMPORT: [
        "import_statement",
        "import_from_statement",
        "import_spec",
        "import_declaration",
        "preproc_include",
        "use_declaration",
        "export_clause",
    ],
    NodeCategory.CALL: [
        "call_expression",
        "attribute",
        "optional_chain_expression",
        "macro_invocation",
    ],
    NodeCategory.CLASS: [
        "class_definition",
        "class_specifier",
        "struct_specifier",
        "enum_specifier",
        "type_declaration",
        "struct_item",
        "enum_item",
        "trait_item",
    ],
    NodeCategory.COMMENT: ["comment"],
    NodeCategory.LITERAL: [
        "string",
        "string_literal",
        "number",
        "boolean",
        "raw_string_literal",
        "rune_literal",
    ],
    NodeCategory.VARIABLE: [
        "identifier",
        "variable_name",
        "field_identifier",
        "short_var_declaration",
    ],
    NodeCategory.RAW: [],
}


class CodebaseAnalyzer:
    def __init__(
        self,
        path: str,
        manifest: str = "manifest.crs",
        log_config: dict = None,
        force: bool = False,
    ):
        from .. import configure_logger

        configure_logger(**(log_config or {}))
        logger.info(f"Initializing CrowSight on '{path}', force={force}")

        self.root = Path(path)
        self.force = force
        self.manifest = ManifestStore(Path(manifest))
        self.manifest.load_if_exists()

        self.files: List[Path] = []
        self.by_lang: Dict[str, List[Path]] = {}
        self.parsers: Dict[str, ParserEngine] = {}

        self._discover_and_init_parsers()

    def _discover_and_init_parsers(self):
        for p in [self.root] if self.root.is_file() else self.root.rglob("*"):
            if not p.is_file():
                continue

            ext = p.suffix.lstrip(".").lower()
            lang = EXT_LANG_MAP.get(ext)
            if not lang:
                self.manifest.record_unknown(p)
                continue

            if lang not in self.parsers:
                try:
                    ts_parser = get_parser(lang)
                    self.parsers[lang] = ParserEngine(ts_parser)
                    self.by_lang[lang] = []
                    logger.info(f"Loaded parser for '{lang}' (ext '.{ext}')")
                except Exception as e:
                    logger.warning(f"No parser for '{lang}': {e}")
                    self.manifest.record_unknown(p)
                    continue

            self.by_lang[lang].append(p)
            self.files.append(p)

        logger.info(
            f"Discovered {len(self.files)} files across "
            f"{len(self.by_lang)} languages; "
            f"{len(self.manifest.data.get('unknown_files', []))} unknown files"
        )

    def analyze(self):
        existing = self.manifest.data.get("files", {}).copy()
        new_files: Dict[str, Any] = {}

        for f in self.files:
            key = str(f)
            sha = self.manifest.checksum(f)
            cached = existing.get(key)

            if not self.force and cached and cached.get("checksum") == sha:
                new_files[key] = cached
                continue

            lang = EXT_LANG_MAP[f.suffix.lstrip(".").lower()]
            parser = self.parsers[lang]
            root = parser.parse(f.read_bytes())

            info = {
                "checksum": sha,
                "functions": [
                    {"name": fn["name"], "arg_count": fn["arg_count"]}
                    for fn in parser.find_functions(root)
                ],
                "imports": parser.find_imports(root),
                "calls": [
                    {"called": call["called"]} for call in parser.find_calls(root)
                ],
                "classes": [
                    {"name": cls["name"], "bases": cls["bases"]}
                    for cls in parser.find_classes(root)
                ],
            }
            new_files[key] = info

        self.manifest.data["files"] = new_files
        self.manifest.save()

    def find(
        self,
        *,
        node_type: Union[str, NodeCategory, List[Union[str, NodeCategory]]] = None,
        pattern: str = None,
        lang: Union[str, List[str]] = None,
        args_min: int = None,
        args_max: int = None,
        include_node: bool = False,
    ) -> Dict[str, List[Union[str, Dict[str, Any]]]]:
        # normalize requested node_types
        requested = (
            []
            if node_type is None
            else ([node_type] if not isinstance(node_type, list) else node_type)
        )
        node_types: List[str] = []
        for t in requested:
            if isinstance(t, NodeCategory):
                node_types.extend(CATEGORY_MAP[t])
            else:
                node_types.append(t)
        node_types = list(dict.fromkeys(node_types))

        pat = re.compile(pattern) if pattern else None
        langs = [lang] if isinstance(lang, str) else (lang or [])

        results: Dict[str, List[Union[str, Dict[str, Any]]]] = {}
        for fp, info in self.manifest.data.get("files", {}).items():
            ext = Path(fp).suffix.lstrip(".").lower()
            if langs and ext not in langs:
                continue

            hits: List[Union[str, Dict[str, Any]]] = []

            # functions
            if not node_types or any(
                ft in node_types for ft in CATEGORY_MAP[NodeCategory.FUNCTION]
            ):
                for fn in info.get("functions", []):
                    if args_min is not None and fn["arg_count"] < args_min:
                        continue
                    if args_max is not None and fn["arg_count"] > args_max:
                        continue
                    if pat and not pat.search(fn["name"]):
                        continue
                    entry = {"name": fn["name"], "arg_count": fn["arg_count"]}
                    if include_node:
                        entry["node"] = fn.get("node")
                    hits.append(entry)

            # imports
            imp_types = CATEGORY_MAP[NodeCategory.IMPORT]
            if not node_types or any(it in node_types for it in imp_types):
                for im in info.get("imports", []):
                    if pat and not pat.search(im):
                        continue
                    hits.append(im)

            # calls
            if not node_types or "call_expression" in node_types:
                for call in info.get("calls", []):
                    cname = call["called"]
                    if pat and not pat.search(cname):
                        continue
                    hits.append({"called": cname} if include_node else cname)

            # classes
            cls_types = CATEGORY_MAP[NodeCategory.CLASS]
            if not node_types or any(ct in node_types for ct in cls_types):
                for cls in info.get("classes", []):
                    if pat and not pat.search(cls["name"]):
                        continue
                    val = (
                        {"name": cls["name"], "bases": cls["bases"]}
                        if include_node
                        else cls["name"]
                    )
                    hits.append(val)

            # raw / other grammar nodes
            extra = [
                t
                for t in node_types
                if t
                not in (
                    *CATEGORY_MAP[NodeCategory.FUNCTION],
                    *imp_types,
                    "call_expression",
                    *cls_types,
                )
            ]
            if extra:
                parser = self.parsers[EXT_LANG_MAP[ext]]
                root = parser.parse(Path(fp).read_bytes())
                for node in root.descendants():
                    if node.type in extra:
                        txt = node.text
                        if pat and not pat.search(txt):
                            continue
                        hits.append(
                            {"type": node.type, "text": txt, "node": node}
                            if include_node
                            else txt
                        )

            if hits:
                results[fp] = hits

        return results

    def export_graph(self) -> Tuple[Dict[int, Dict[str, Any]], List[Tuple[int, int]]]:
        """
        Walk every parsed file's AST and return:
          - nodes: { node_id: {"type":..., "text":...} }
          - edges: [ (parent_id, child_id), ... ]
        """
        nodes: Dict[int, Dict[str, Any]] = {}
        edges: List[Tuple[int, int]] = []
        next_id = 1

        for lang, files in self.by_lang.items():
            parser = self.parsers[lang]
            for f in files:
                root = parser.parse(f.read_bytes())

                def walk(nw: NodeWrapper, parent_id: int = None):
                    nonlocal next_id
                    nid = next_id
                    next_id += 1
                    nodes[nid] = {"type": nw.type, "text": nw.text, "file": str(f)}
                    if parent_id is not None:
                        edges.append((parent_id, nid))
                    for child in nw.children:
                        walk(child, nid)

                walk(root, None)

        return nodes, edges
