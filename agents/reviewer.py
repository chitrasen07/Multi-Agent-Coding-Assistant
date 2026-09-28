import json
import re
from pathlib import Path

from agents.llm import chat_json
from tools.workspace import read_file

SYSTEM = """You are a code reviewer.
Compare the project files with the architecture and plan.
Respond with a JSON object only, using these keys:
- status: PASS or FAIL
- issues: array of strings describing the concrete problem and the file
- affected_files: array of project-relative paths that need changes
Fail for syntax problems, missing files, missing functionality, broken file references, or obvious implementation errors.
Check that values emitted by the UI are the same tokens the script uses to choose behavior.
If a control sends "+" but the handler only recognizes a different name such as "add", fail the file that performs the lookup.
Accept conditionals, switch statements, and lookup tables when they handle the emitted values.
File bodies may be shortened excerpts. Do not fail a file only because an excerpt ends.
Do not fail a project for lacking a framework, bundler, or preferred config template.
Fail a config file only when it is invalid or its paths do not match files in the project.
Pass only when the files satisfy the architecture. When status is PASS, return empty arrays."""

_ATTR = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.I)
_URL = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)


def reviewer(state: dict) -> dict:
    project = Path(state["project_path"])
    contents, issues, affected = _load(project, state["architecture"]["files"])
    _check_references(project, contents, issues, affected)
    _check_python(contents, issues, affected)
    _check_control_handlers(contents, issues, affected)

    model = chat_json(SYSTEM, _model_input(state, contents))
    status = str(model.get("status", "")).strip().upper()
    if status not in {"PASS", "FAIL"}:
        raise ValueError("Review status must be PASS or FAIL.")
    model_issues = [
        issue
        for issue in _string_list(model.get("issues"), allow_empty=status == "PASS")
        if not _excerpt_complaint(issue)
    ]
    allowed = {spec["path"] for spec in state["architecture"]["files"]}
    allowed.update(item["path"] for item in state["generated_files"])
    model_files = [
        path
        for path in _string_list(model.get("affected_files"), allow_empty=True)
        if path in allowed
    ]
    if issues or model_issues:
        status = "FAIL"
    else:
        status = "PASS"
    if status == "PASS":
        return {"review": {"status": "PASS", "issues": [], "affected_files": []}}
    return {
        "review": {
            "status": "FAIL",
            "issues": _unique(issues + model_issues),
            "affected_files": _unique(affected + model_files),
        }
    }


def _model_input(state: dict, contents: dict[str, str]) -> str:
    files = {}
    for path, text in contents.items():
        if len(text) <= 1500:
            files[path] = text
            continue
        files[path] = text[:1500] + "\n[excerpt only; the full file was checked separately]"
    return json.dumps(
        {
            "plan": state["plan"],
            "architecture": state["architecture"],
            "files": files,
        }
    )


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


_DATA_ATTR = re.compile(r"""data-([A-Za-z][\w-]*)\s*=\s*["']([^"']+)["']""")
_OBJECT = re.compile(r"""(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*\{""")
_KEY = re.compile(r"""(['"][^'"]+['"]|[A-Za-z_$][\w$]*|[+\-*/])\s*:""")
_ASSIGN = re.compile(r"""(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]+)""")


def find_control_mismatches(contents: dict[str, str]) -> list[dict]:
    html = {path: text for path, text in contents.items() if path.lower().endswith((".html", ".htm"))}
    values_by_attr: dict[str, list[str]] = {}
    sources_by_attr: dict[str, list[str]] = {}
    for path, text in html.items():
        for attr, value in _DATA_ATTR.findall(text):
            name = attr.lower()
            values_by_attr.setdefault(name, [])
            if value not in values_by_attr[name]:
                values_by_attr[name].append(value)
            sources_by_attr.setdefault(name, [])
            if path not in sources_by_attr[name]:
                sources_by_attr[name].append(path)

    mismatches = []
    for path, text in contents.items():
        if not path.lower().endswith(".js") or ".config." in Path(path).name.lower():
            continue
        for variable, keys in _objects(text):
            for attr, ui_values in values_by_attr.items():
                if not ui_values or not _lookup_uses_attr(text, variable, attr):
                    continue
                if all(value in keys for value in ui_values):
                    continue
                mismatches.append(
                    {
                        "file": path,
                        "variable": variable,
                        "attribute": attr,
                        "ui_values": ui_values,
                        "keys": keys,
                        "sources": sources_by_attr.get(attr, []),
                    }
                )
    return mismatches


def _check_control_handlers(contents: dict[str, str], issues: list[str], affected: list[str]) -> None:
    for mismatch in find_control_mismatches(contents):
        ui = ", ".join(repr(value) for value in mismatch["ui_values"])
        keys = ", ".join(repr(key) for key in mismatch["keys"])
        sources = ", ".join(mismatch["sources"]) or "the page"
        issues.append(
            f"{mismatch['file']}: {sources} sets data-{mismatch['attribute']} to {ui}, "
            f"but {mismatch['variable']} is keyed by {keys}. "
            f"A lookup such as {mismatch['variable']}[{mismatch['ui_values'][0]!r}] does not match. "
            f"Handle the values the UI sends."
        )
        affected.append(mismatch["file"])


def _objects(text: str) -> list[tuple[str, list[str]]]:
    found = []
    for match in _OBJECT.finditer(text):
        body = _brace_body(text, match.end() - 1)
        if body is None:
            continue
        keys = []
        for key in _KEY.findall(body):
            cleaned = key.strip("'\"")
            if cleaned and cleaned not in keys:
                keys.append(cleaned)
        if keys:
            found.append((match.group(1), keys))
    return found


def _brace_body(text: str, open_index: int) -> str | None:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : index]
    return None


def _lookup_uses_attr(text: str, variable: str, attr: str) -> bool:
    camel = re.sub(r"-([a-z])", lambda match: match.group(1).upper(), attr)
    attr_expr = (
        rf"(?:dataset\.{camel}|dataset\[\s*['\"]{re.escape(camel)}['\"]\s*\]|"
        rf"getAttribute\(\s*['\"]data-{re.escape(attr)}['\"]\s*\))"
    )
    if re.search(rf"{re.escape(variable)}\s*\[[^;\]]*?(?:{attr_expr})", text):
        return True
    for name, expression in _ASSIGN.findall(text):
        if re.search(attr_expr, expression) and re.search(
            rf"{re.escape(variable)}\s*\[\s*{re.escape(name)}\s*\]",
            text,
        ):
            return True
    return False


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


def _excerpt_complaint(issue: str) -> bool:
    lowered = issue.lower()
    return "excerpt" in lowered or "truncat" in lowered


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
