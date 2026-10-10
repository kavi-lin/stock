"""Select complete Theme Detector reports without confusing narrative sidecars."""

import json
import sys
import time
from pathlib import Path

THEME_CACHE_DIR = Path("skills/theme-detector/cache")


def latest_theme_report(cache_dir: Path) -> tuple[Path, dict, float] | None:
    candidates = []
    for path in cache_dir.glob("theme_detector_????-??-??_??????.json"):
        try:
            candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for mtime, path in sorted(candidates, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(data, dict) or data.get("report_type") != "theme_detector"
                    or not isinstance(data.get("themes"), dict)
                    or not isinstance(data["themes"].get("all"), list)):
                raise ValueError("not a primary theme report")
            age = time.time() - mtime
            if age >= 0:
                return path, data, age
        except (OSError, ValueError) as exc:
            print(f"WARNING: Skipping invalid theme cache {path.name} ({type(exc).__name__})", file=sys.stderr)
    return None
