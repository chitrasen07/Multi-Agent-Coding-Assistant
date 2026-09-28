import json

from agents.llm import chat_text
from tools.workspace import create_folders, create_project, write_file

SYSTEM = """You are a software coder.
Write the complete source for one project file.
Return only the file contents. Do not add markdown fences or explanation."""


def coder(state: dict) -> dict:
    architecture = state["architecture"]
    project = create_project(architecture["project_name"])
    create_folders(project, architecture["folders"])
    generated = []
    for spec in architecture["files"]:
        content = _source(chat_text(SYSTEM, _request(state, spec)))
        write_file(project, spec["path"], content)
        generated.append({"path": spec["path"], "status": "written"})
    return {
        "project_path": str(project),
        "generated_files": generated,
    }


def _request(state: dict, spec: dict) -> str:
    architecture = state["architecture"]
    others = [item["path"] for item in architecture["files"]]
    return (
        f"Project: {architecture['project_name']}\n"
        f"Plan:\n{json.dumps(state['plan'])}\n"
        f"File: {spec['path']}\n"
        f"Purpose: {spec['purpose']}\n"
        f"Task: {spec['task']}\n"
        "Project files:\n" + "\n".join(others)
    )


def _source(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
    content = "\n".join(lines).strip()
    if not content:
        raise ValueError("Generated file was empty.")
    return content + "\n"
