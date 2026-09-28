import json
import re

from agents.llm import chat_json, require_text

SYSTEM = """You are a software architect.
Turn the project plan into a concrete project architecture.
Respond with a JSON object only, using these keys:
- project_name: short lowercase name using letters, numbers, and hyphens
- folders: array of folder paths to create
- files: array of objects with path, purpose, and task
Each task is the coding work for that file. Do not write source code.
Use only technologies named in the user request.
If the user asks for HTML, CSS, and JavaScript and does not ask for a framework or bundler, design a static site with those files only.
Do not add package.json, Vite, webpack, React, or Node tooling unless the user explicitly asks for that tool.
If the user explicitly asks for React, Vite, TypeScript, or another build tool, include the files that tool needs."""

_REQUESTED_TOOLING = re.compile(
    r"\b(vite|webpack|rollup|parcel|react|vue|angular|svelte|next(?:\.js)?|nuxt|typescript|npm|node\.js)\b",
    re.I,
)
_TOOLING_FILE = re.compile(
    r"(?:^|/)(?:package(?:-lock)?\.json|vite\.config\.[a-z]+|webpack\.config\.[a-z]+|tsconfig\.json)$",
    re.I,
)


def architect(state: dict) -> dict:
    design = chat_json(
        SYSTEM,
        "User request:\n"
        + state.get("user_request", "")
        + "\nCreate the architecture for this plan:\n"
        + json.dumps(state["plan"]),
    )
    folders = _folders(design.get("folders"))
    files = _omit_unrequested_tooling(state.get("user_request", ""), _files(design.get("files")))
    return {
        "architecture": {
            "project_name": require_text(design, "project_name"),
            "folders": folders,
            "files": files,
        }
    }


def _omit_unrequested_tooling(user_request: str, files: list[dict[str, str]]) -> list[dict[str, str]]:
    if _REQUESTED_TOOLING.search(user_request):
        return files
    kept = [item for item in files if not _TOOLING_FILE.search(item["path"].replace("\\", "/"))]
    if not kept:
        raise ValueError("Architecture has no application files.")
    return kept


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
