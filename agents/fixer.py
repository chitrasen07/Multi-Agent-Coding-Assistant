import re
from pathlib import Path

_ENTRY = re.compile(
    r"""(?P<key>['"][^'"]+['"]|[A-Za-z_$][\w$]*|[+\-*/])\s*:\s*(?P<value>['"][^'"]*['"])"""
)

from agents.coder import _source
from agents.llm import chat_text
from agents.reviewer import find_control_mismatches
from tools.workspace import read_file, write_file

SYSTEM = """You are a software fixer.
Repair one source file so it resolves the review issues.
Return only the full updated file contents.
Do not add markdown fences or explanation.
Change only what is required to fix issues in this file.
If UI controls emit values that this file does not handle, accept those exact values.
Preserve working behavior. Do not return the file unchanged."""


def fixer(state: dict) -> dict:
    project = Path(state["project_path"])
    generated = [{**item} for item in state["generated_files"]]
    fixed = []
    unchanged = []
    for path in state["review"]["affected_files"]:
        try:
            current = read_file(project, path)
        except (OSError, ValueError):
            current = ""
        try:
            updated = _source(chat_text(SYSTEM, _request(state, project, path, current)))
        except ValueError:
            updated = current
        updated = _repair_lookups(state, project, path, updated)
        if _same(updated, current):
            unchanged.append(path)
            continue
        try:
            write_file(project, path, updated)
        except ValueError:
            unchanged.append(path)
            continue
        fixed.append(path)
        for item in generated:
            if item["path"] == path:
                item["status"] = "fixed"
                break
        else:
            generated.append({"path": path, "status": "fixed"})

    cycles = state.get("fix_cycles", 0) + 1
    if fixed and not unchanged:
        status = f"Fixed {len(fixed)} file(s) in cycle {cycles}."
    elif fixed:
        status = (
            f"Fixed {len(fixed)} file(s) in cycle {cycles}. "
            f"Unchanged: {', '.join(unchanged)}."
        )
    else:
        status = f"No files changed in cycle {cycles}."
    return {
        "generated_files": generated,
        "fix_cycles": cycles,
        "fix_status": status,
    }


def _request(state: dict, project: Path, path: str, current: str) -> str:
    spec = next(
        (item for item in state["architecture"]["files"] if item["path"] == path),
        None,
    )
    purpose = spec["purpose"] if spec else ""
    task = spec["task"] if spec else ""
    issues = "\n".join(state["review"]["issues"])
    related = []
    budget = 5000
    for item in state["architecture"]["files"]:
        other = item["path"]
        if other == path or budget <= 0:
            continue
        try:
            text = read_file(project, other)
        except (OSError, ValueError):
            continue
        snippet = text[:budget]
        related.append(f"--- {other} ---\n{snippet}")
        budget -= len(snippet)
    context = "\n\n".join(related)
    return (
        f"File: {path}\n"
        f"Purpose: {purpose}\n"
        f"Task: {task}\n"
        f"Issues:\n{issues}\n"
        f"Related files:\n{context}\n"
        f"Current contents:\n{current}"
    )


def _repair_lookups(state: dict, project: Path, path: str, updated: str) -> str:
    contents = {}
    for item in state["architecture"]["files"]:
        other = item["path"]
        if other == path:
            contents[other] = updated
            continue
        try:
            contents[other] = read_file(project, other)
        except (OSError, ValueError):
            continue
    for mismatch in find_control_mismatches(contents):
        if mismatch["file"] != path:
            continue
        updated = _rekey_lookup(updated, mismatch["variable"], mismatch["ui_values"])
    return updated


def _rekey_lookup(text: str, variable: str, ui_values: list[str]) -> str:
    match = re.search(rf"(?:const|let|var)\s+{re.escape(variable)}\s*=\s*\{{", text)
    if match is None:
        return text
    open_index = match.end() - 1
    body = _brace_body(text, open_index)
    if body is None:
        return text
    accepted = set(ui_values)

    def replace(entry: re.Match) -> str:
        key = entry.group("key").strip("'\"")
        value = entry.group("value")
        literal = value[1:-1]
        if key in accepted or literal not in accepted:
            return entry.group(0)
        return f"{_quote(literal)}: {value}"

    repaired = _ENTRY.sub(replace, body)
    if repaired == body:
        return text
    return text[: open_index + 1] + repaired + text[open_index + 1 + len(body) :]


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


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


def _same(updated: str, current: str) -> bool:
    return updated.replace("\r\n", "\n").strip() == current.replace("\r\n", "\n").strip()
