import shutil
import subprocess
import uuid
from pathlib import Path

_IMAGE = "python:3.12-alpine"


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        completed = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def execute_project(project: Path) -> str:
    if not docker_available():
        return "Docker is not available."

    name = f"mac-assistant-{uuid.uuid4().hex[:12]}"
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "256m",
        "--pids-limit",
        "64",
        "--network",
        "none",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "-v",
        f"{project.resolve()}:/site:ro",
        _IMAGE,
        "python",
        "-m",
        "http.server",
        "8000",
        "--directory",
        "/site",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "docker run failed").strip()
            return f"Docker execution failed: {detail[:500]}"
        inspect = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if inspect.stdout.strip() != "true":
            return "Docker container exited before it was ready."
        return "Project served in a read-only Docker container."
    except subprocess.TimeoutExpired:
        return "Docker execution timed out."
    except OSError as exc:
        return f"Docker execution failed: {exc}"
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            timeout=20,
            check=False,
        )
