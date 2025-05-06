# src/crowsight/codebase_analyzer.py

import json
import hashlib
from pathlib import Path

from tree_sitter import Language
from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from tree_sitter_language_pack import get_parser

from .parser_engine import ParserEngine
from .simple_query import SimpleQuery

from loguru import logger
from . import configure_logger

# CrowSight Record Store file extension
DEFAULT_MANIFEST_EXT = ".crs"
DEFAULT_MANIFEST_NAME = f"manifest{DEFAULT_MANIFEST_EXT}"


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
        *args,
        manifest: str = None,
        log_config: dict = None,
        force: bool = False,
    ):
        """
        Overloads:
          CodebaseAnalyzer(path, manifest="file.crs", ...)
          CodebaseAnalyzer(path, "file.crs", ...)
          CodebaseAnalyzer("file.crs", ...)
        """
        # Configure logging
        configure_logger(**(log_config or {}))

        # Force re-analysis flag
        self.force = force

        # Determine path_arg and manifest_arg from args
        path_arg = None
        manifest_arg = manifest

        if len(args) >= 1:
            path_arg = args[0]
            # If a second positional arg was given, override manifest
            if len(args) >= 2:
                manifest_arg = args[1]
            else:
                manifest_arg = manifest
        else:
            path_arg = "."
            manifest_arg = manifest

        # Validate project path
        try:
            self.root = Path(path_arg)
        except TypeError as e:
            raise ValueError(f"Invalid project path: {path_arg!r}") from e

        # Validate manifest path if provided
        if manifest_arg is not None:
            try:
                self.manifest_path = Path(manifest_arg)
            except TypeError as e:
                raise ValueError(f"Invalid manifest path: {manifest_arg!r}") from e
        else:
            self.manifest_path = None

        logger.info(f"Initializing CrowSight on '{self.root}'")

        # Internal state
        self.files = []
        self.unknowns = []
        self.by_lang = {}
        self.parsers = {}
        self.results = {}

        # Discover source files
        self._discover_files()

        # Group files by detected language
        self._group_by_language()

        # Initialize parser engines
        self._init_parsers()

        # Manifest handling
        if self.manifest_path:
            if self.manifest_path.exists():
                self._load_manifest()
            else:
                self._write_empty_manifest()

    def _discover_files(self):
        if self.root.is_file():
            candidates = [self.root]
        else:
            candidates = self.root.rglob("*")

        for p in candidates:
            if not p.is_file():
                continue

            ext = p.suffix.lstrip(".")
            if ext in self.EXT_LANG_MAP:
                self.files.append(p)
            else:
                self.unknowns.append(p)

        logger.info(
            f"Discovered {len(self.files)} supported files "
            f"and {len(self.unknowns)} unknown files"
        )

    def _group_by_language(self):
        for f in self.files:
            ext = f.suffix.lstrip(".")
            lang = self.EXT_LANG_MAP[ext]
            if lang not in self.by_lang:
                self.by_lang[lang] = []
            self.by_lang[lang].append(f)

        counts = {lang: len(fs) for lang, fs in self.by_lang.items()}
        logger.debug(f"Files grouped by language: {counts}")

    def _init_parsers(self):
        for lang in self.by_lang:
            ts_parser = get_parser(lang)
            engine = ParserEngine(ts_parser)
            self.parsers[lang] = engine

        logger.info(
            f"Initialized parsers " f"for languages: {list(self.parsers.keys())}"
        )

    def _write_empty_manifest(self):
        logger.info(f"Creating empty manifest '{self.manifest_path}'")
        empty = {"files": {}, "unknown_files": []}
        try:
            self.manifest_path.write_text(json.dumps(empty, indent=2))
        except OSError as e:
            logger.error(f"Failed to write empty manifest: {e}")

    def _load_manifest(self):
        try:
            raw = self.manifest_path.read_text()
        except OSError as e:
            logger.error(f"Cannot read manifest '{self.manifest_path}': {e}")
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Malformed manifest JSON: {e}")
            return

        files = data.get("files", {})
        # Convert keys back to Path
        for fp, info in files.items():
            self.results[Path(fp)] = info

        logger.success(f"Loaded manifest with {len(self.results)} entries")

    @staticmethod
    def _checksum(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    def analyze(self):
        updated = {}

        for f in self.files:
            sha = self._checksum(f)
            cached = self.results.get(f)

            if not self.force and cached and cached.get("checksum") == sha:
                logger.debug(f"Skipping unchanged file: {f}")
                updated[f] = cached
                continue

            ext = f.suffix.lstrip(".")
            lang = self.EXT_LANG_MAP[ext]
            engine = self.parsers[lang]

            try:
                code = f.read_bytes()
            except OSError as e:
                logger.error(f"Failed to read file {f}: {e}")
                continue

            wrapped = engine.parse_wrapped(code)

            info = {
                "checksum": sha,
                "functions": engine.find_functions(wrapped),
                "imports": engine.find_imports(wrapped),
                "calls": engine.find_calls(wrapped),
                "classes": engine.find_classes(wrapped),
            }

            updated[f] = info

            logger.info(
                f"Analyzed {f.name}: "
                f"{len(info['functions'])} funcs, "
                f"{len(info['imports'])} imports"
            )

        self.results = updated
        logger.success("Analysis complete")

    def write_manifest(self):
        """
        Write CrowSight Record Store (CRS) manifest, dropping any NodeWrapper
        references so that the data is pure JSON-serializable.
        """
        if not self.manifest_path:
            logger.warning("No manifest path set; skipping write_manifest()")
            return

        serializable = {"files": {}, "unknown_files": []}

        # Unknown files are already plain strings
        serializable["unknown_files"] = [str(p) for p in self.unknowns]

        for fp, info in self.results.items():
            # 1. Functions: keep name & arg_count only
            funcs = []
            for fn in info.get("functions", []):
                funcs.append(
                    {
                        "name": fn.get("name"),
                        "arg_count": fn.get("arg_count"),
                    }
                )

            # 2. Imports: already a list of strings
            imps = info.get("imports", [])

            # 3. Calls: keep only the 'called' name
            calls = []
            for c in info.get("calls", []):
                calls.append({"called": c.get("called")})

            # 4. Classes: keep name & bases only
            classes = []
            for cls in info.get("classes", []):
                classes.append(
                    {
                        "name": cls.get("name"),
                        "bases": cls.get("bases", []),
                    }
                )

            # 5. Checksum
            checksum = info.get("checksum")

            serializable["files"][str(fp)] = {
                "checksum": checksum,
                "functions": funcs,
                "imports": imps,
                "calls": calls,
                "classes": classes,
            }

        try:
            self.manifest_path.write_text(json.dumps(serializable, indent=2))
            logger.success(f"Saved manifest to '{self.manifest_path}'")
        except OSError as e:
            logger.error(f"Unable to write manifest: {e}")

    # High-level getters

    def find_functions(self):
        return {str(fp): info["functions"] for fp, info in self.results.items()}

    def find_imports(self):
        return {str(fp): info["imports"] for fp, info in self.results.items()}

    def find_calls(self):
        return {str(fp): info["calls"] for fp, info in self.results.items()}

    def find_classes(self):
        return {str(fp): info["classes"] for fp, info in self.results.items()}

    def run_query(self, pattern: str):
        results = {}

        for f, info in self.results.items():
            if info.get("_queried") and not self.force:
                continue

            ext = f.suffix.lstrip(".")
            lang = self.EXT_LANG_MAP[ext]
            parser = self.parsers[lang]

            try:
                code = f.read_bytes()
            except OSError as e:
                logger.error(f"Cannot re-read file {f}: {e}")
                continue

            wrapped = parser.parse_wrapped(code)
            sq = SimpleQuery(get_language(lang))
            caps = sq.run(pattern, wrapped)

            if caps:
                results[str(f)] = [(n, node.text) for n, node in caps]

            info["_queried"] = True

        return results

    def register_custom(self, ext: str, so_path: str, lang_name: str):
        """
        Register a custom grammar for extension (no dot).
        """
        self.EXT_LANG_MAP[ext] = lang_name

        for p in self.root.rglob(f"*.{ext}"):
            if p.is_file():
                self.files.append(p)
                self.by_lang.setdefault(lang_name, []).append(p)

        lang = Language(so_path, lang_name)
        parser = Parser()
        parser.set_language(lang)
        self.parsers[lang_name] = ParserEngine(parser)

        logger.success(f"Registered custom grammar '{lang_name}' for '.{ext}'")
