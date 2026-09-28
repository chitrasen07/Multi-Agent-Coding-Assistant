import json

from agents.llm import chat_json, require_text

SYSTEM = """You are a software architect.
Turn the project plan into a concrete project architecture.
Respond with a JSON object only, using these keys:
- project_name: short lowercase name using letters, numbers, and hyphens
- folders: array of folder paths to create
- files: array of objects with path, purpose, and task
Each task is the coding work for that file. Do not write source code."""


def architect(state: dict) -> dict:
    design = chat_json(
        SYSTEM,
        "Create the architecture for this plan:\n" + json.dumps(state["plan"]),
    )
    return {
        "architecture": {
            "project_name": require_text(design, "project_name"),
            "folders": _folders(design.get("folders")),
            "files": _files(design.get("files")),
        }
    }


def _folders(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("Model response is missing folders.")
    return [item.strip() for item in value]


def _files(value) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError("Model response is missing files.")

    files = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Each file must include path, purpose, and task.")
        path = item.get("path")
        purpose = item.get("purpose")
        task = item.get("task")
        if not all(isinstance(field, str) and field.strip() for field in (path, purpose, task)):
            raise ValueError("Each file must include path, purpose, and task.")
        files.append(
            {
                "path": path.strip(),
                "purpose": purpose.strip(),
                "task": task.strip(),
            }
        )
    return files
