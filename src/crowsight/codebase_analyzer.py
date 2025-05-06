# crowsight/codebase_analyzer.py

import json
from pathlib import Path
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

    def __init__(self, path: str, out_manifest: str = "manifest.json"):
        self.root = Path(path)
        self.out_manifest = out_manifest
        self.files = []
        self.unknowns = []
        self.by_lang = {}
        self.parsers = {}
        self.trees = {}

        self._discover_files()
        self._group_by_language()
        self._init_parsers()

    def _discover_files(self):
        if self.root.is_file():
            self.files = [self.root]
        else:
            for p in self.root.rglob("*"):
                if p.is_file() and p.suffix.lstrip(".") in self.EXT_LANG_MAP:
                    self.files.append(p)

    def _group_by_language(self):
        for f in self.files:
            ext = f.suffix.lstrip(".")
            lang = self.EXT_LANG_MAP.get(ext)
            if lang:
                self.by_lang.setdefault(lang, []).append(f)
            else:
                self.unknowns.append(f)

    def _init_parsers(self):
        for lang in self.by_lang:
            ts_lang = get_language(lang)
            ts_parser = get_parser(lang)
            self.parsers[lang] = ParserEngine(ts_parser)

    def analyze(self):
        for lang, files in self.by_lang.items():
            engine = self.parsers[lang]
            for f in files:
                code = f.read_bytes()
                self.trees[f] = engine.parse_wrapped(code)

    def write_manifest(self):
        data = {
            "by_language": {lang: [str(p) for p in fs] for lang, fs in self.by_lang.items()},
            "unknown_files": [str(p) for p in self.unknowns],
        }
        with open(self.out_manifest, "w", encoding="utf8") as fp:
            json.dump(data, fp, indent=2)
        print(f"Manifest written to {self.out_manifest!r}")

    def run_query(self, pattern: str):
        results = {}
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

    def find_functions(self, min_args=0):
        out = {}
        for f, w in self.trees.items():
            funcs = self.parsers[self._lang_of(f)].find_functions(w, min_args)
            if funcs:
                out[str(f)] = funcs
        return out

    def find_imports(self):
        out = {}
        for f, w in self.trees.items():
            imps = self.parsers[self._lang_of(f)].find_imports(w)
            if imps:
                out[str(f)] = imps
        return out

    def find_calls(self):
        out = {}
        for f, w in self.trees.items():
            calls = self.parsers[self._lang_of(f)].find_calls(w)
            if calls:
                out[str(f)] = calls
        return out

    def find_classes(self):
        out = {}
        for f, w in self.trees.items():
            classes = self.parsers[self._lang_of(f)].find_classes(w)
            if classes:
                out[str(f)] = classes
        return out

    def register_custom(self, name: str, so_path: str):
        """Load a user-compiled grammar and reinitialize parsing."""
        ts_lang = get_language(name) if False else None  # placeholder
        # if you want truly custom, use Language(so_path, name)
        from tree_sitter import Language
        ts_lang = Language(so_path, name)
        ts_parser = ParserEngine(get_parser(name) if False else ParserEngine(Parser(Language(so_path, name))))
        self.parsers[name] = ParserEngine(Parser(Language(so_path, name)))
        self.by_lang[name] = []
        # you’d need to rescan files for this extension and re-run analyze()

    def _lang_of(self, path: Path) -> str:
        return self.EXT_LANG_MAP[path.suffix.lstrip(".")]
