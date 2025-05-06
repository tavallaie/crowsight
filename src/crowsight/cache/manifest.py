import json
import hashlib
from pathlib import Path
from loguru import logger


class ManifestStore:
    """Loads, saves, and checksums analysis results."""

    def __init__(self, path: Path):
        self.path = path
        self.data = {"files": {}, "unknown": []}

    def load_if_exists(self):
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
                logger.success(f"Loaded manifest {self.path}")
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")

    def save(self):
        # Ensure the directory exists
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create manifest directory: {e}")

        serializable = {"files": {}, "unknown_files": self.data.get("unknown", [])}
        for fp, info in self.data["files"].items():
            # Wrap each call string in a dict with key "called"
            raw_calls = info.get("calls", [])
            wrapped_calls = []
            for entry in raw_calls:
                if isinstance(entry, dict) and "called" in entry:
                    # Already wrapped (from older versions)
                    wrapped_calls.append(entry)
                else:
                    wrapped_calls.append({"called": entry})

            serializable["files"][fp] = {
                "checksum": info.get("checksum"),
                "functions": info.get("functions", []),
                "imports": info.get("imports", []),
                "calls": wrapped_calls,
                "classes": info.get("classes", []),
            }

        try:
            self.path.write_text(json.dumps(serializable, indent=2))
            logger.success(f"Saved manifest to {self.path}")
        except Exception as e:
            logger.error(f"Failed to write manifest: {e}")

    def checksum(self, path: Path) -> str:
        h = hashlib.sha256(path.read_bytes())
        return h.hexdigest()

    def get(self, path: Path):
        return self.data["files"].get(str(path))

    def update(self, path: Path, info: dict):
        self.data["files"][str(path)] = info

    def record_unknown(self, path: Path):
        self.data["unknown_files"].append(str(path))
