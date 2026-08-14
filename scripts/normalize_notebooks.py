"""Normalize repository notebooks without adding a notebook dependency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIRS = (ROOT / "notebooks", ROOT / "examples")
LIVE_CELL_MARKERS = ("get_deepseek_client", "semantic_graph.invoke")
NOTEBOOK_METADATA = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    },
    "language_info": {"name": "python", "version": "3.12"},
}


def notebook_paths() -> list[Path]:
    paths: list[Path] = []
    for directory in NOTEBOOK_DIRS:
        if directory.exists():
            paths.extend(directory.rglob("*.ipynb"))
    return sorted(paths)


def normalize(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    notebook = json.loads(original)
    notebook["metadata"] = NOTEBOOK_METADATA

    for cell in notebook.get("cells", []):
        cell["metadata"] = {}
        if cell.get("cell_type") == "code":
            cell["execution_count"] = None
            source = "".join(cell.get("source", []))
            if path.name == "02_conditional_routing.ipynb" and any(
                marker in source for marker in LIVE_CELL_MARKERS
            ):
                cell["outputs"] = []

    normalized = json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"
    if normalized == original:
        return False
    path.write_text(normalized, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Report drift without writing files."
    )
    args = parser.parse_args()
    changed: list[Path] = []
    for path in notebook_paths():
        before = path.read_text(encoding="utf-8")
        if args.check:
            notebook = json.loads(before)
            notebook["metadata"] = NOTEBOOK_METADATA
            for cell in notebook.get("cells", []):
                cell["metadata"] = {}
                if cell.get("cell_type") == "code":
                    cell["execution_count"] = None
                    source = "".join(cell.get("source", []))
                    if path.name == "02_conditional_routing.ipynb" and any(
                        marker in source for marker in LIVE_CELL_MARKERS
                    ):
                        cell["outputs"] = []
            after = json.dumps(notebook, ensure_ascii=False, indent=1) + "\n"
            if after != before:
                changed.append(path)
        elif normalize(path):
            changed.append(path)

    for path in changed:
        print(path.relative_to(ROOT))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
