# src/crowsight/codebase_analyzer.py

import json
from pathlib import Path

from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language, get_parser

from .parser_engine import ParserEngine
from .simple_query import SimpleQuery


class CodebaseAnalyzer:
    EXT_LANG_MAP = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "go": "go",
        "java": "java",
    }

    def __init__(self, path: str, manifest: str = "manifest.json"):
        self.root = Path(path)
        self.out_manifest = manifest

        # All discovered source files
        self.files: list[Path] = []
        # Files with unknown extensions
        self.unknowns: list[Path] = []
        # Mapping lang_name -> [Path, Path, ...]
        self.by_lang: dict[str, list[Path]] = {}
        # Mapping lang_name -> ParserEngine
        self.parsers: dict[str, ParserEngine] = {}
        # Mapping Path -> parsed & wrapped AST root
        self.trees: dict[Path, any] = {}

        self._discover_files()
        self._group_by_language()
        self._init_parsers()

    def _discover_files(self):
        if self.root.is_file():
            self.files = [self.root]
        else:
            # Recursively find files whose extension is in EXT_LANG_MAP
            for p in self.root.rglob("*"):
                if not p.is_file():
                    continue
                ext = p.suffix.lstrip(".")
                if ext in self.EXT_LANG_MAP:
                    self.files.append(p)
                else:
                    self.unknowns.append(p)

    def _group_by_language(self):
        for f in self.files:
            lang = self.EXT_LANG_MAP[f.suffix.lstrip(".")]
            self.by_lang.setdefault(lang, []).append(f)

    def _init_parsers(self):
        # For each language detected, get its pre-built parser and wrap it
        for lang, files in self.by_lang.items():
            ts_parser = get_parser(lang)  # returns a tree_sitter.Parser
            self.parsers[lang] = ParserEngine(ts_parser)

    def analyze(self):
        """Parse each file once and store the wrapped AST."""
        for lang, files in self.by_lang.items():
            engine = self.parsers[lang]
            for f in files:
                code = f.read_bytes()
                self.trees[f] = engine.parse_wrapped(code)

    def write_manifest(self):
        manifest = {
            "by_language": {
                lang: [str(p) for p in files] for lang, files in self.by_lang.items()
            },
            "unknown_files": [str(p) for p in self.unknowns],
        }
        with open(self.out_manifest, "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, indent=2)
        print(f"Manifest written to {self.out_manifest!r}")

    def run_query(self, pattern: str):
        """
        Run a raw S-expression query across all parsed trees.
        Returns a dict mapping file-path → list of (capture_name, text).
        """
        results: dict[str, list[tuple[str, str]]] = {}
        for lang, files in self.by_lang.items():
            ts_lang = get_language(lang)  # Language object
            sq = SimpleQuery(ts_lang)
            for f in files:
                wrapped = self.trees.get(f)
                if not wrapped:
                    continue
                caps = sq.run(pattern, wrapped)
                if caps:
                    results[str(f)] = [(name, node.text) for name, node in caps]
        return results

    # High-level helpers

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
        Register a custom grammar for extension `ext` (e.g. 'mylang'),
        loading from the compiled shared lib at `so_path`. After registering,
        you can call analyze() again to parse any newly-matched files.
        """
        # 1. Map new extension to language name
        self.EXT_LANG_MAP[ext] = lang_name

        # 2. Discover any files with this extension
        for p in self.root.rglob(f"*.{ext}"):
            if p.is_file():
                self.files.append(p)
                self.by_lang.setdefault(lang_name, []).append(p)

        # 3. Load the new grammar
        ts_lang = Language(so_path, lang_name)
        parser = Parser()
        parser.set_language(ts_lang)
        self.parsers[lang_name] = ParserEngine(parser)

    def _lang_of(self, path: Path) -> str:
        return self.EXT_LANG_MAP[path.suffix.lstrip(".")]
