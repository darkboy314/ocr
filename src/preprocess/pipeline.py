"""Run the F1 -> F2 -> F3 preprocessing notebooks as one pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path


# Change this path to select the directory containing the three notebooks and input data.
WORKING_DIR = Path("input/Final_Algorithm")

_NOTEBOOKS = (
    "F_Module 1 - Operation Statistics Essentials-V4-CP.ipynb",
    "F_Module 2 - Table of Operation_V4-CP.ipynb",
    "F_Module 3 - Report Automation.ipynb",
)


def _execute_notebook(path: Path, namespace: dict[str, object]) -> None:
    with path.open(encoding="utf-8") as notebook_file:
        notebook = json.load(notebook_file)

    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if source.strip():
            exec(compile(source, str(path), "exec"), namespace)


def run_pipeline(working_dir: Path | str = WORKING_DIR) -> dict[str, object]:
    """Execute F1, F2, and F3 in order using one shared namespace."""
    working_path = Path(working_dir).expanduser().resolve()
    notebook_paths = [working_path / notebook_name for notebook_name in _NOTEBOOKS]
    missing = [str(path) for path in notebook_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing preprocessing notebook(s): " + ", ".join(missing)
        )

    previous_directory = Path.cwd()
    namespace: dict[str, object] = {
        "__name__": "__preprocess_pipeline__",
        "__file__": str(notebook_paths[0]),
    }
    try:
        os.chdir(working_path)
        for notebook_path in notebook_paths:
            _execute_notebook(notebook_path, namespace)
    finally:
        os.chdir(previous_directory)
    return namespace


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
