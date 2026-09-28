import json
import re
from pathlib import Path

from tools.workspace import read_file

_ATTR = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.I)
_URL = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)


def validate_project(project: Path, architecture: dict, plan: dict) -> list[str]:
    errors = []
    contents: dict[str, str] = {}
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
        errors.extend(_check_syntax(relative, text))
        contents[relative] = text

    errors.extend(_check_references(project, contents))
    errors.extend(_check_web(contents, _requirements(architecture, plan)))
    return errors


def _requirements(architecture: dict, plan: dict) -> str:
    parts = []
    for key in ("features", "technical_requirements", "implementation_steps"):
        parts.extend(str(item) for item in plan.get(key) or [])
    for spec in architecture.get("files") or []:
        parts.append(str(spec.get("purpose", "")))
        parts.append(str(spec.get("task", "")))
    return "\n".join(parts).lower()


def _check_syntax(relative: str, text: str) -> list[str]:
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


def _check_references(project: Path, contents: dict[str, str]) -> list[str]:
    errors = []
    for path, text in contents.items():
        for ref in _ATTR.findall(text) + _URL.findall(text):
            relative = _project_ref(path, ref)
            if relative is None:
                continue
            if not _is_file(project, relative):
                errors.append(f"Broken file reference in {path}: {ref}")
    return errors


def _check_web(contents: dict[str, str], requirements: str) -> list[str]:
    html_paths = [path for path in contents if path.lower().endswith((".html", ".htm"))]
    css_paths = [path for path in contents if path.lower().endswith(".css")]
    js_paths = [path for path in contents if _page_script(path)]
    if not html_paths:
        return []

    errors = []
    html = "\n".join(contents[path] for path in html_paths)
    css = "\n".join(contents[path] for path in css_paths)
    js = "\n".join(contents[path] for path in js_paths)
    linked = _linked_files(html_paths, contents)

    for path in css_paths:
        if _posix(path) not in linked:
            errors.append(f"{path} is not referenced by an HTML file.")
    for path in js_paths:
        if _posix(path) not in linked:
            errors.append(f"{path} is not referenced by an HTML file.")

    if js_paths and _mentions(requirements, r"interactive|click|button|calculator|\binput\b"):
        if not re.search(r"querySelector|getElementById|getElementsBy|querySelectorAll", js):
            errors.append("JavaScript does not select the page elements.")
        if not re.search(r"addEventListener|\bon(?:click|input|change|submit)\s*=", js + html):
            errors.append("The page has no event handling.")

    if _mentions(requirements, r"responsive|mobile|small screen"):
        if not re.search(r"@media|display\s*:\s*flex|display\s*:\s*grid|max-width|min-width|viewport", css + html, re.I):
            errors.append("Responsive layout was requested but was not found.")

    if _mentions(requirements, r"\b(?:clear|reset)\b"):
        if not re.search(r"\b(?:clear|reset)\b", html + js, re.I):
            errors.append("Clear or reset behavior was requested but was not found.")

    if _mentions(requirements, r"division by zero|divide by zero|divided by zero"):
        if not re.search(r"(?:===|==|!==|!=)\s*0\b|isFinite|Number\.isFinite|\bInfinity\b", js):
            errors.append("Division by zero handling was requested but was not found.")

    if _mentions(requirements, r"invalid input|invalid number|not a number"):
        if not re.search(r"isNaN|Number\.isNaN|\binvalid\b", js, re.I):
            errors.append("Invalid input handling was requested but was not found.")

    if _mentions(requirements, r"calculator|\badd\b|\bsubtract\b|\bmultiply\b|\bdivide\b|operator|equals"):
        if not re.search(r"<button\b|<input\b", html, re.I):
            errors.append("Calculator controls were requested but no buttons or inputs were found.")
        elif not re.search(r"\d", html):
            errors.append("Numeric controls were requested but were not found.")
        if not re.search(r"[+\-*/×÷]|data-operation|operator|\b(?:add|subtract|multiply|divide)\b", html + js, re.I):
            errors.append("Operator handling was requested but was not found.")
        if not any(token in js for token in ("+", "-", "*", "/")):
            errors.append("Arithmetic operations were requested but were not found in JavaScript.")
    return errors


def _linked_files(html_paths: list[str], contents: dict[str, str]) -> set[str]:
    linked = set()
    for path in html_paths:
        for ref in _ATTR.findall(contents[path]):
            relative = _project_ref(path, ref)
            if relative:
                linked.add(_posix(relative))
    return linked


def _mentions(requirements: str, pattern: str) -> bool:
    return re.search(pattern, requirements, re.I) is not None


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
    if path.is_absolute() or any(part == ".." for part in path.parts):
        candidate = (project / path).resolve()
        root = project.resolve()
        if candidate != root and root not in candidate.parents:
            return False
        return candidate.is_file()
    return (project / path).is_file()


def _page_script(path: str) -> bool:
    name = Path(path).name.lower()
    return name.endswith(".js") and ".config." not in name


def _posix(path: str) -> str:
    return Path(path).as_posix()
