"""Validate that a release tag matches the versions embedded in both programs."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_TARGETS = {
    "fll-maestro.py": "MAESTRO_VERSION",
    "fll-toast.py": "TOAST_VERSION",
}


def read_assignment(path: Path, variable: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == variable for target in targets):
                value = ast.literal_eval(node.value)
                if isinstance(value, str):
                    return value
    raise ValueError(f"{variable} is not a top-level string assignment in {path.name}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_release_version.py VERSION_OR_TAG", file=sys.stderr)
        return 2

    requested = sys.argv[1].removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", requested):
        print(f"invalid release version: {sys.argv[1]!r}", file=sys.stderr)
        return 2

    versions = {
        filename: read_assignment(ROOT / filename, variable)
        for filename, variable in VERSION_TARGETS.items()
    }
    mismatches = {filename: value for filename, value in versions.items() if value != requested}
    if mismatches:
        details = ", ".join(f"{filename}={value}" for filename, value in mismatches.items())
        print(f"release tag v{requested} does not match {details}", file=sys.stderr)
        return 1

    print(f"release version v{requested} matches Maestro and TOAST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
