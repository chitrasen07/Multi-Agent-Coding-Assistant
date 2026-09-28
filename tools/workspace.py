import tempfile
from pathlib import Path

_active: tempfile.TemporaryDirectory | None = None


def create_project(name: str) -> Path:
    global _active
    workspace = tempfile.TemporaryDirectory(prefix="multi-agent-coding-")
    project = _inside(Path(workspace.name), _project_name(name))
    project.mkdir()
    previous = _active
    _active = workspace
    if previous is not None:
        previous.cleanup()
    return project


def create_folders(project: Path, folders: list[str]) -> None:
    for folder in folders:
        _inside(project, folder).mkdir(parents=True, exist_ok=True)


def write_file(project: Path, relative_path: str, content: str) -> None:
    path = _inside(project, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def read_file(project: Path, relative_path: str) -> str:
    return _inside(project, relative_path).read_text(encoding="utf-8")


def _project_name(name: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "-_" else "-" for char in name.strip())
    cleaned = cleaned.strip("-_.")
    if not cleaned:
        raise ValueError("Invalid project name.")
    return cleaned[:64]


def _inside(root: Path, relative: str) -> Path:
    raw = relative.strip()
    path = Path(raw)
    if (
        not raw
        or path.is_absolute()
        or any(part in {"..", ""} for part in path.parts)
    ):
        raise ValueError(f"Path is outside the workspace: {relative}")

    candidate = (root / path).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"Path is outside the workspace: {relative}")
    return candidate
