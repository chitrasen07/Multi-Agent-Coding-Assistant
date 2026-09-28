import io
import zipfile
from pathlib import Path

from tools.workspace import read_file


def build_zip(project: Path, relative_paths: list[str]) -> bytes:
    paths = list(dict.fromkeys(relative_paths))
    if not paths:
        raise ValueError("The project has no files to package.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in paths:
            archive.writestr(_entry(project.name, relative), read_file(project, relative))
    data = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise ValueError(f"ZIP entry is corrupt: {corrupt}")
        names = set(archive.namelist())
    missing = [_entry(project.name, relative) for relative in paths if _entry(project.name, relative) not in names]
    if missing:
        raise ValueError("ZIP is missing project files.")
    return data


def _entry(project_name: str, relative: str) -> str:
    return f"{project_name}/{Path(relative).as_posix()}"
