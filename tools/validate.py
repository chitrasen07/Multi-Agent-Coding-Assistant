import json
from pathlib import Path

from tools.workspace import read_file


def validate_project(project: Path, architecture: dict, plan: dict) -> list[str]:
    errors = []
    contents = []
    paths = [spec["path"] for spec in architecture["files"]]
    if not paths:
        errors.append("Architecture has no files.")
    for relative in paths:
        try:
            text = read_file(project, relative)
        except FileNotFoundError:
            errors.append(f"Missing file: {relative}")
            continue
        except (OSError, ValueError) as exc:
            errors.append(f"Unreadable file {relative}: {exc}")
            continue
        if not text.strip():
            errors.append(f"Empty file: {relative}")
            continue
        errors.extend(_check_contents(relative, text))
        contents.append(text)

    combined = "\n".join(contents).lower()
    for feature in plan.get("features", []):
        expected = str(feature).strip().lower()
        if expected and expected not in combined:
            errors.append(f"Missing functionality: {feature}")
    return errors


def _check_contents(relative: str, text: str) -> list[str]:
    suffix = Path(relative).suffix.lower()
    if suffix == ".py":
        try:
            compile(text, relative, "exec")
        except SyntaxError as exc:
            return [f"Syntax error in {relative}: {exc.msg}"]
    elif suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError:
            return [f"Invalid JSON: {relative}"]
    elif suffix in {".html", ".htm"} and "<" not in text:
        return [f"{relative} is not HTML."]
    return []
