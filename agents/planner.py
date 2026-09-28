from agents.llm import chat_json, require_text, require_texts

SYSTEM = """You are a software planner.
Convert the user's request into a project plan.
Respond with a JSON object only, using these keys:
- project_type: string
- features: array of strings
- technical_requirements: array of strings
- implementation_steps: array of strings, in order
Do not include source code."""


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
