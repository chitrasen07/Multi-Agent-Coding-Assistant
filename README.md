# Multi-Agent Coding Assistant

An AI coding assistant that turns a software request into a plan and a project architecture. The Streamlit app sends the request through a LangGraph workflow: Planner, then Architect.

## Current features

- Prompt text area and Generate button
- Groq chat completions through the official Python client
- `GROQ_API_KEY` loaded from the environment with python-dotenv
- Planner agent: project type, features, technical requirements, and implementation steps
- Architect agent: project name, folders, files, the purpose of each file, and a coding task for each file

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
