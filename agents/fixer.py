from pathlib import Path

from agents.coder import _source
from agents.llm import chat_text
from tools.workspace import read_file, write_file

SYSTEM = """You are a software fixer.
Repair one source file so it resolves the review issues.
Return only the full updated file contents.
Do not add markdown fences or explanation.
Change only what is required to fix issues in this file."""


def fixer(state: dict) -> dict:
    project = Path(state["project_path"])
    generated = [{**item} for item in state["generated_files"]]
    fixed = []
    for path in state["review"]["affected_files"]:
        try:
            current = read_file(project, path)
        except (OSError, ValueError):
            current = ""
        try:
            updated = _source(chat_text(SYSTEM, _request(state, path, current)))
            write_file(project, path, updated)
        except ValueError:
            continue
        fixed.append(path)
        for item in generated:
            if item["path"] == path:
                item["status"] = "fixed"
                break
        else:
            generated.append({"path": path, "status": "fixed"})

    cycles = state.get("fix_cycles", 0) + 1
    if fixed:
        status = f"Fixed {len(fixed)} file(s) in cycle {cycles}."
    else:
        status = f"No files changed in cycle {cycles}."
    return {
        "generated_files": generated,
        "fix_cycles": cycles,
        "fix_status": status,
    }


def _request(state: dict, path: str, current: str) -> str:
    spec = next(
        (item for item in state["architecture"]["files"] if item["path"] == path),
        None,
    )
    purpose = spec["purpose"] if spec else ""
    task = spec["task"] if spec else ""
    issues = "\n".join(state["review"]["issues"])
    return (
        f"File: {path}\n"
        f"Purpose: {purpose}\n"
        f"Task: {task}\n"
        f"Issues:\n{issues}\n"
        f"Current contents:\n{current}"
    )
