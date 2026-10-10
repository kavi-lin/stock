#!/usr/bin/env python3
"""Map real FRED fetch output into the Phase 0 contract without renewing clocks."""
import argparse
import copy
import subprocess
import sys
from pathlib import Path

from run_data import ROOT, atomic_json, fresh, read_json, source

sys.path.insert(0, str(ROOT))
from sector.scripts.phase0_read_caches import _slim_fred


def assemble(data):
    result = copy.deepcopy(data)
    if not fresh(source(data, kind="phase0", fetched_at=data.get("fetched_at"))):
        raise ValueError("Phase 0 source clock missing or expired; fetch real data again")
    if result.get("fred_available") is True:
        raw = result.get("fred_snapshot") or {}
        slim = _slim_fred(raw)
        for key, value in slim.items():
            if value is None:
                continue
            if key in raw and raw[key] != value:
                raise ValueError(f"FRED source disagrees with flattened field: {key}")
            raw[key] = value
        result["fred_snapshot"] = raw
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="Phase 0 draft containing actual FRED fetch output")
    ap.add_argument("--out", required=True, help="new canonical path; never overwritten")
    args = ap.parse_args(argv)
    path = Path(args.out)
    try:
        if path.exists():
            raise ValueError("Phase 0 output already exists; preserve it and use a new path")
        atomic_json(path, assemble(read_json(args.input)))
        return subprocess.run([sys.executable, str(ROOT / "investment/scripts/validate_phase0.py"),
                               "--path", str(path)], cwd=ROOT).returncode
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
