import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "openai/gpt-oss-120b"


def chat_json(system: str, user: str) -> dict:
    data = json.loads(_complete(system, user, json_mode=True))
    if not isinstance(data, dict):
        raise ValueError("Model response was not a JSON object.")
    return data


def chat_text(system: str, user: str) -> str:
    text = _complete(system, user, json_mode=False).strip()
    if not text:
        raise ValueError("Model response was empty.")
    return text


def _complete(system: str, user: str, *, json_mode: bool) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    client = Groq(api_key=api_key, timeout=120.0)
    request = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    if json_mode:
        request["response_format"] = {"type": "json_object"}
    completion = client.chat.completions.create(**request)
    return completion.choices[0].message.content or ""


def require_text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Model response is missing {key}.")
    return value.strip()


def require_texts(data: dict, key: str) -> list[str]:
    value = data.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError(f"Model response is missing {key}.")
    return [item.strip() for item in value]
