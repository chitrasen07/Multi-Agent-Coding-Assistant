import json
import re
from pathlib import Path

from agents.llm import chat_json
from tools.workspace import read_file

SYSTEM = """You are a code reviewer.
Compare the project files with the architecture and plan.
Respond with a JSON object only, using these keys:
- status: PASS or FAIL
- issues: array of strings
- affected_files: array of project-relative paths that need changes
Fail for syntax problems, missing files, missing functionality, broken file references, or obvious implementation errors.
Pass only when the files satisfy the architecture. When status is PASS, return empty arrays."""

_ATTR = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.I)
_URL = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)


def reviewer(state: dict) -> dict:
    project = Path(state["project_path"])
    contents, issues, affected = _load(project, state["architecture"]["files"])
    _check_references(project, contents, issues, affected)
    _check_python(contents, issues, affected)

    model = chat_json(
        SYSTEM,
        json.dumps(
            {
                "plan": state["plan"],
                "architecture": state["architecture"],
                "files": contents,
            }
        ),
    )
    status = str(model.get("status", "")).strip().upper()
    if status not in {"PASS", "FAIL"}:
        raise ValueError("Review status must be PASS or FAIL.")
    model_issues = _string_list(model.get("issues"), allow_empty=status == "PASS")
    allowed = {spec["path"] for spec in state["architecture"]["files"]}
    allowed.update(item["path"] for item in state["generated_files"])
    model_files = [
        path
        for path in _string_list(model.get("affected_files"), allow_empty=True)
        if path in allowed
    ]
    if issues:
        status = "FAIL"
    elif status == "FAIL" and not model_issues:
        raise ValueError("A failed review must list issues.")
    if status == "PASS":
        return {"review": {"status": "PASS", "issues": [], "affected_files": []}}
    return {
        "review": {
            "status": "FAIL",
            "issues": _unique(issues + model_issues),
            "affected_files": _unique(affected + model_files),
        }
    }


def _load(project: Path, specs: list[dict]) -> tuple[dict[str, str], list[str], list[str]]:
    contents = {}
    issues = []
    affected = []
    for spec in specs:
        path = spec["path"]
        try:
            contents[path] = read_file(project, path)
        except FileNotFoundError:
            contents[path] = ""
            issues.append(f"Missing file: {path}")
            affected.append(path)
    return contents, issues, affected


def _check_python(contents: dict[str, str], issues: list[str], affected: list[str]) -> None:
    for path, content in contents.items():
        if not path.endswith(".py") or not content:
            continue
        try:
            compile(content, path, "exec")
        except SyntaxError as exc:
            issues.append(f"Syntax error in {path}: {exc.msg}")
            affected.append(path)


def _check_references(
    project: Path,
    contents: dict[str, str],
    issues: list[str],
    affected: list[str],
) -> None:
    for path, content in contents.items():
        for ref in _ATTR.findall(content) + _URL.findall(content):
            relative = _project_ref(path, ref)
            if relative is None:
                continue
            if not _is_file(project, relative):
                issues.append(f"Broken file reference in {path}: {ref}")
                affected.append(path)


def _project_ref(source: str, ref: str) -> str | None:
    raw = ref.strip().split("#", 1)[0].split("?", 1)[0].strip()
    if not raw or raw.startswith(("#", "data:", "mailto:", "javascript:")) or "://" in raw:
        return None
    relative = Path(source).parent / Path(raw)
    if relative.is_absolute():
        return None
    return relative.as_posix()


def _is_file(project: Path, relative: str) -> bool:
    path = Path(relative)
    if path.is_absolute():
        return False
    candidate = (project / path).resolve()
    root = project.resolve()
    if candidate != root and root not in candidate.parents:
        return False
    return candidate.is_file()


def _string_list(value, *, allow_empty: bool) -> list[str]:
    if value is None and allow_empty:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("Review response has an invalid list.")
    if not value and not allow_empty:
        raise ValueError("Review response has an invalid list.")
    return [item.strip() for item in value]


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
