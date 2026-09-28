# Multi-Agent Coding Assistant

An AI coding assistant that turns a software request into a plan, a project architecture, and source files. The Streamlit app runs a LangGraph workflow: Planner, Architect, then Coder. Generated projects are written to a temporary directory outside this repository.

## Current features

- Prompt text area and Generate button
- Groq chat completions through the official Python client
- `GROQ_API_KEY` loaded from the environment with python-dotenv
- Planner agent: project type, features, technical requirements, and implementation steps
- Architect agent: project name, folders, files, the purpose of each file, and a coding task for each file
- Coder agent: writes each file into a temporary workspace and shows the file list, status, and code

## Installation

Python 3.12 is required.

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, create the environment with `python3.12 -m venv .venv` and activate it with `source .venv/bin/activate`. Copy the example env file with `cp .env.example .env`.

Add your Groq API key to `.env`:

```
GROQ_API_KEY=your_key_here
```

## Run

```bash
streamlit run app.py
```
