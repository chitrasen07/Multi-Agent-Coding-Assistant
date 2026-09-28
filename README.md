# Multi-Agent Coding Assistant

A Streamlit application that turns a software request into a small project. LangGraph runs a planner, architect, coder, and reviewer. A failed review is sent to a fixer and reviewed again, up to two times. The finished project is checked, packaged as a ZIP, and can be served in a read-only Docker container when Docker is running.

Generated files stay in a temporary directory outside this repository. That directory is removed after the ZIP is created.

## Architecture

The Streamlit app collects a request and calls one LangGraph workflow. Agents share a single state: the user request, project plan, architecture, generated project path, and generated files, plus the latest review. Groq provides the model responses through the official Python client. The file manager writes only inside the temporary workspace.

```text
Project request
    ↓
Planner
    ↓
Architect
    ↓
Coder
    ↓
Reviewer
    ├── PASS → Final project
    └── FAIL → Fixer → Reviewer
                    ↓
              Final project
    ↓
Validation → ZIP → optional Docker → cleanup
```

The fixer runs at most twice. If the review still fails, the workflow stops.

## Agents

- **Planner** turns the request into a project type, features, technical requirements, and implementation steps.
- **Architect** defines the project name, folders, files, the purpose of each file, and a coding task for each file.
- **Coder** writes those files into the temporary workspace.
- **Reviewer** checks for missing files, missing functionality, broken references, syntax problems, and other obvious errors.
- **Fixer** updates only the files named in a failed review.

## Tech stack

- Python 3.12
- Streamlit
- LangGraph
- Groq API
- python-dotenv
- Docker, optional, for sandboxed static serving

## Installation

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, create the environment with `python3.12 -m venv .venv`, activate it with `source .venv/bin/activate`, and copy the env file with `cp .env.example .env`.

## Environment variables

| Name | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Groq API key used by the agents |

Put the key in `.env`. Do not commit that file.

```text
GROQ_API_KEY=your_key_here
```

## Running the application

```bash
streamlit run app.py
```

Open the local URL Streamlit prints. Enter a request and choose Generate. When validation passes, use Download ZIP. If Docker is running, the app also reports whether the project started in a read-only container. Generated code is not executed on the host.

## Example prompt

```text
Build a calculator web app with add, subtract, multiply and divide buttons.
```

## Project workflow

1. The planner and architect produce a plan and a file layout.
2. The coder writes that layout into a temporary workspace.
3. The reviewer checks the files. A failure goes to the fixer, then back to the reviewer.
4. Validation confirms the expected files exist, can be read, and pass basic content checks.
5. The app builds a ZIP and only then deletes the temporary workspace.
6. When Docker is available, the project is served from a read-only container with no host code execution.
