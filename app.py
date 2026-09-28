import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from graph.workflow import run
from tools.workspace import read_file

load_dotenv()


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _show_plan(result: dict) -> None:
    st.subheader("Planner")
    st.markdown(f"**Project type:** {result['project_type']}")
    st.markdown("**Features**\n" + _bullets(result["features"]))
    st.markdown("**Technical requirements**\n" + _bullets(result["technical_requirements"]))
    st.markdown("**Implementation steps**\n" + _numbered(result["implementation_steps"]))


def _show_architecture(result: dict) -> None:
    st.subheader("Architect")
    st.markdown(f"**Project name:** {result['project_name']}")
    st.markdown("**Folders**\n" + _bullets(result["folders"]))
    st.markdown("**Files**")
    for file in result["files"]:
        st.markdown(
            f"**{file['path']}**\n\n{file['purpose']}\n\nTask: {file['task']}"
        )


def _show_code(result: dict) -> None:
    project = Path(result["project_path"])
    generated = result["generated_files"]
    st.subheader("Coder")
    st.markdown(f"**Workspace:** `{project}`")
    st.markdown(f"**Status:** {len(generated)} file(s) written")
    st.markdown("**Files**\n" + _bullets(
        f"`{item['path']}` — {item['status']}" for item in generated
    ))
    for item in generated:
        st.markdown(f"**{item['path']}**")
        st.code(read_file(project, item["path"]), language=_language(item["path"]))


def _language(path: str) -> str | None:
    return {
        ".html": "html",
        ".css": "css",
        ".js": "javascript",
        ".py": "python",
        ".json": "json",
        ".md": "markdown",
    }.get(Path(path).suffix.lower())


st.set_page_config(page_title="Multi-Agent Coding Assistant")
st.title("Multi-Agent Coding Assistant")

prompt = st.text_area("Prompt", height=160)

if st.button("Generate"):
    if not prompt.strip():
        st.warning("Enter a prompt.")
    else:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
        else:
            try:
                result = run(prompt.strip())
            except Exception as exc:
                st.error(str(exc))
            else:
                _show_plan(result)
                _show_architecture(result)
                _show_code(result)
