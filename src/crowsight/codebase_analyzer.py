import json
from pathlib import Path
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language, get_parser
from .parser_engine import ParserEngine
from .simple_query import SimpleQuery
from loguru import logger
from . import configure_logger


class CodebaseAnalyzer:
    EXT_LANG_MAP = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "go": "go",
        "java": "java",
    }

    def __init__(
        self,
        path: str,
        manifest: str = "manifest.json",
        log_config: dict = None,
    ):
        # 1) Configure logging
        configure_logger(**(log_config or {}))
        logger.info(f"Initializing CodebaseAnalyzer on '{path}'")

        # 2) Setup paths and data structures
        self.root = Path(path)
        self.out_manifest = manifest
        self.files: list[Path] = []
        self.unknowns: list[Path] = []
        self.by_lang: dict[str, list[Path]] = {}
        self.parsers: dict[str, ParserEngine] = {}
        self.trees: dict[Path, any] = {}

        # 3) Discover and prepare
        self._discover_files()
        self._group_by_language()
        self._init_parsers()

    def _discover_files(self):
        if self.root.is_file():
            self.files = [self.root]
        else:
            for p in self.root.rglob("*"):
                if not p.is_file():
                    continue
                ext = p.suffix.lstrip(".")
                if ext in self.EXT_LANG_MAP:
                    self.files.append(p)
                else:
                    self.unknowns.append(p)
        logger.info(
            f"Discovered {len(self.files)} supported files, "
            f"{len(self.unknowns)} unknown files"
        )

    def _group_by_language(self):
        for f in self.files:
            lang = self.EXT_LANG_MAP[f.suffix.lstrip(".")]
            self.by_lang.setdefault(lang, []).append(f)
        logger.debug(
            f"Files grouped by language: { {k: len(v) for k,v in self.by_lang.items()} }"
        )

    def _init_parsers(self):
        for lang in self.by_lang:
            ts_parser = get_parser(lang)
            self.parsers[lang] = ParserEngine(ts_parser)
        logger.info(f"Initialized parsers for languages: {list(self.parsers.keys())}")

    def analyze(self):
        logger.info("Starting analysis of codebase")
        for lang, files in self.by_lang.items():
            engine = self.parsers[lang]
            logger.info(f"Parsing {len(files)} '{lang}' files")
            for f in files:
                logger.debug(f"Parsing file {f}")
                code = f.read_bytes()
                self.trees[f] = engine.parse_wrapped(code)
        logger.success("Analysis complete")

    def write_manifest(self):
        manifest = {
            "by_language": {
                lang: [str(p) for p in fs] for lang, fs in self.by_lang.items()
            },
            "unknown_files": [str(p) for p in self.unknowns],
        }
        with open(self.out_manifest, "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, indent=2)
        logger.success(f"Manifest written to '{self.out_manifest}'")

    def run_query(self, pattern: str):
        results: dict[str, list[tuple[str, str]]] = {}
        for lang, files in self.by_lang.items():
            ts_lang = get_language(lang)
            sq = SimpleQuery(ts_lang)
            for f in files:
                wrapped = self.trees.get(f)
                if not wrapped:
                    continue
                caps = sq.run(pattern, wrapped)
                if caps:
                    results[str(f)] = [(name, node.text) for name, node in caps]
        return results

    def find_functions(self, min_args: int = 0):
        out = {}
        for f, wrapped in self.trees.items():
            lang = self._lang_of(f)
            funcs = self.parsers[lang].find_functions(wrapped, min_args)
            if funcs:
                out[str(f)] = funcs
        return out

    def find_imports(self):
        out = {}
        for f, wrapped in self.trees.items():
            lang = self._lang_of(f)
            imps = self.parsers[lang].find_imports(wrapped)
            if imps:
                out[str(f)] = imps
        return out

    def find_calls(self):
        out = {}
        for f, wrapped in self.trees.items():
            lang = self._lang_of(f)
            calls = self.parsers[lang].find_calls(wrapped)
            if calls:
                out[str(f)] = calls
        return out

    def find_classes(self):
        out = {}
        for f, wrapped in self.trees.items():
            lang = self._lang_of(f)
            cls = self.parsers[lang].find_classes(wrapped)
            if cls:
                out[str(f)] = cls
        return out

    def register_custom(self, ext: str, so_path: str, lang_name: str):
        """
        Register a custom grammar:
        - ext: file extension (no dot)
        - so_path: path to compiled Tree-sitter .so
        - lang_name: language identifier
        """
        # Map extension → lang
        self.EXT_LANG_MAP[ext] = lang_name

        # Discover new files
        for p in self.root.rglob(f"*.{ext}"):
            if p.is_file():
                logger.debug(f"Registering custom file {p} for '{lang_name}'")
                self.files.append(p)
                self.by_lang.setdefault(lang_name, []).append(p)

        # Load grammar and parser
        ts_lang = Language(so_path, lang_name)
        parser = Parser()
        parser.set_language(ts_lang)
        self.parsers[lang_name] = ParserEngine(parser)
        logger.success(f"Registered custom language '{lang_name}' for *.{ext}")

    def _lang_of(self, path: Path) -> str:
        return self.EXT_LANG_MAP[path.suffix.lstrip(".")]
