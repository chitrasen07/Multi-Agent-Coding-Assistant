import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from graph.workflow import run
from tools.execute import execute_project
from tools.package import build_zip
from tools.validate import validate_project
from tools.workspace import cleanup_project, read_file

load_dotenv()


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _language(path: str) -> str | None:
    return {
        ".html": "html",
        ".css": "css",
        ".js": "javascript",
        ".py": "python",
        ".json": "json",
        ".md": "markdown",
    }.get(Path(path).suffix.lower())


def _generate(prompt: str) -> dict:
    result = run(prompt)
    project = Path(result["project_path"])
    errors = validate_project(project, result["architecture"], result["plan"])
    files = []
    for item in result["generated_files"]:
        try:
            content = read_file(project, item["path"])
        except (OSError, ValueError):
            content = ""
        files.append({"path": item["path"], "status": item["status"], "content": content})

    if errors:
        return {
            "result": result,
            "files": files,
            "errors": errors,
            "zip_bytes": None,
            "file_name": None,
            "execution": None,
        }

    zip_bytes = build_zip(project, [item["path"] for item in files])
    file_name = f"{project.name}.zip"
    try:
        execution = execute_project(project)
    finally:
        try:
            cleanup_project(project)
        except OSError:
            pass
    return {
        "result": result,
        "files": files,
        "errors": [],
        "zip_bytes": zip_bytes,
        "file_name": file_name,
        "execution": execution,
    }


def _show_progress(project: dict) -> None:
    result = project["result"]
    steps = ["Planner", "Architect", "Coder", "Reviewer"]
    for _ in range(result.get("fix_cycles", 0)):
        steps.extend(["Fixer", "Reviewer"])
    if not project["errors"]:
        steps.append("Final Project")
    st.subheader("Progress")
    st.markdown(" → ".join(steps))


def _show_plan(result: dict) -> None:
    plan = result["plan"]
    st.subheader("Planner")
    st.markdown(f"**Project type:** {plan['project_type']}")
    st.markdown("**Features**\n" + _bullets(plan["features"]))
    st.markdown("**Technical requirements**\n" + _bullets(plan["technical_requirements"]))
    st.markdown("**Implementation steps**\n" + _numbered(plan["implementation_steps"]))


def _show_architecture(result: dict) -> None:
    architecture = result["architecture"]
    folders = architecture["folders"] or ["None"]
    st.subheader("Architecture")
    st.markdown(f"**Project name:** {architecture['project_name']}")
    st.markdown("**Folders**\n" + _bullets(folders))
    st.markdown("**Files**")
    for file in architecture["files"]:
        st.markdown(f"**{file['path']}**\n\n{file['purpose']}\n\nTask: {file['task']}")


def _show_review(result: dict) -> None:
    review = result["review"]
    st.subheader("Review")
    st.markdown(f"**Status:** {review['status']}")
    st.markdown("**Issues**\n" + _bullets(review["issues"] or ["None"]))
    st.markdown("**Affected files**\n" + _bullets(review["affected_files"] or ["None"]))


def _show_fix(result: dict) -> None:
    cycles = result.get("fix_cycles", 0)
    if cycles == 0:
        return
    review = result["review"]
    st.subheader("Fixer")
    if review["status"] == "FAIL":
        st.markdown(
            f"**Status:** Retry limit reached after {cycles} cycle(s). "
            f"{result.get('fix_status', '')}"
        )
    else:
        st.markdown(f"**Status:** {result.get('fix_status', 'Fixes applied.')}")


def _show_files(files: list[dict]) -> None:
    st.subheader("Generated files")
    st.markdown("**Files**\n" + _bullets(f"`{item['path']}` — {item['status']}" for item in files))
    for item in files:
        st.markdown(f"**{item['path']}**")
        st.code(item["content"], language=_language(item["path"]))


def _show_project(project: dict) -> None:
    _show_progress(project)
    _show_plan(project["result"])
    _show_architecture(project["result"])
    _show_review(project["result"])
    _show_fix(project["result"])
    _show_files(project["files"])
    if project["errors"]:
        st.error("Project validation failed.")
        st.markdown(_bullets(project["errors"]))
        return
    st.download_button(
        "Download ZIP",
        data=project["zip_bytes"],
        file_name=project["file_name"],
        mime="application/zip",
    )
    if project["execution"]:
        st.subheader("Execution")
        st.markdown(project["execution"])


st.set_page_config(page_title="Multi-Agent Coding Assistant")
st.title("Multi-Agent Coding Assistant")

if "project" not in st.session_state:
    st.session_state.project = None

prompt = st.text_area("Project request", height=160)

if st.button("Generate"):
    if not prompt.strip():
        st.warning("Enter a project request.")
    else:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
        else:
            try:
                st.session_state.project = _generate(prompt.strip())
            except Exception as exc:
                st.session_state.project = None
                st.error(str(exc))

if st.session_state.project:
    _show_project(st.session_state.project)
