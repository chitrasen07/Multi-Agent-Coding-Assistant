from agents.llm import chat_json, require_text, require_texts

SYSTEM = """You are a software planner.
Convert the user's request into a project plan.
Respond with a JSON object only, using these keys:
- project_type: string
- features: array of strings
- technical_requirements: array of strings
- implementation_steps: array of strings, in order
Do not include source code.
technical_requirements must list only technologies the user asked for.
Do not add a framework, bundler, or package manager unless the user requested it.
HTML, CSS, and JavaScript alone describe a static page."""


def planner(state: dict) -> dict:
    plan = chat_json(SYSTEM, state["user_request"])
    return {
        "plan": {
            "project_type": require_text(plan, "project_type"),
            "features": require_texts(plan, "features"),
            "technical_requirements": require_texts(plan, "technical_requirements"),
            "implementation_steps": require_texts(plan, "implementation_steps"),
        }
    }
