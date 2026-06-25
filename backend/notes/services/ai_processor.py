import json

import requests
from django.conf import settings

REQUIRED_KEYS = {
    "cleaned_note",
    "summary",
    "people",
    "topics",
    "events",
    "follow_up_questions",
}

PROMPT_TEMPLATE = """You are processing a personal note.

Extract structured information from the input.

Rules:

* Do not hallucinate
* Only extract what is explicitly or reasonably implied
* Keep cleaned_note concise but readable
* Summary must be 1-2 lines
* People should be names only
* Topics should be high-level categories

Return ONLY valid JSON.

Input:
{user_input}"""


def process_note(raw_input: str) -> dict:
    if not settings.AI_API_KEY or not settings.AI_BASE_URL:
        raise RuntimeError("AI_API_KEY and AI_BASE_URL must be configured.")

    prompt = PROMPT_TEMPLATE.format(user_input=raw_input)
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if settings.AI_MODEL:
        payload["model"] = settings.AI_MODEL

    response = requests.post(
        _chat_completions_url(),
        headers={
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    return _normalize_output(_extract_json(response.json()))


def _extract_json(response_data: dict) -> dict:
    if REQUIRED_KEYS.issubset(response_data):
        return response_data

    content = response_data.get("output_text")
    if content is None and response_data.get("choices"):
        choice = response_data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or choice.get("text")

    if not isinstance(content, str):
        raise ValueError("AI response did not contain JSON content.")

    return json.loads(content)


def _normalize_output(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("AI response JSON must be an object.")

    return {
        "cleaned_note": str(data.get("cleaned_note") or ""),
        "summary": str(data.get("summary") or ""),
        "people": _string_list(data.get("people")),
        "topics": _string_list(data.get("topics")),
        "events": _string_list(data.get("events")),
        "follow_up_questions": _string_list(data.get("follow_up_questions")),
    }


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def _chat_completions_url() -> str:
    base_url = settings.AI_BASE_URL.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/chat/completions"
