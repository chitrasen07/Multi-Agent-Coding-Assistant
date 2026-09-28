import os

import streamlit as st
from dotenv import load_dotenv

from graph.workflow import run

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
