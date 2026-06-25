import requests
from django.conf import settings

FALLBACK_ANSWER = "I could not find that in your notes yet."

PROMPT_TEMPLATE = """You are answering based ONLY on the provided notes.

Rules:

* Do NOT use outside knowledge
* Do NOT hallucinate
* If the answer is not in the notes, say:
  'I could not find that in your notes yet.'
* Be natural and conversational
* Keep the answer short by default
* Do not write phrases like "Based solely on the provided notes"
* Do not include source lists or note IDs in the answer text

Notes:
{context}

Question:
{query}"""

REWRITE_PROMPT_TEMPLATE = """Turn the current user message into a standalone retrieval query for searching notes.

Use the recent conversation only to resolve references like it, he, she, they, that, this interview, or the meeting.
Do not answer the question.
Do not add facts that are not implied by the conversation.
Return only the standalone retrieval query.

Recent conversation:
{history}

Current user message:
{query}"""


def generate_answer(query: str, notes: list) -> str:
    if not settings.AI_API_KEY or not settings.AI_BASE_URL:
        raise RuntimeError("AI_API_KEY and AI_BASE_URL must be configured.")

    context = "\n\n".join(str(note) for note in notes if str(note).strip())
    prompt = PROMPT_TEMPLATE.format(context=context, query=query)
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
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

    answer = _extract_answer(response.json()).strip()
    return answer or FALLBACK_ANSWER


def rewrite_retrieval_query(query: str, history: list[dict]) -> str:
    if not settings.AI_API_KEY or not settings.AI_BASE_URL:
        raise RuntimeError("AI_API_KEY and AI_BASE_URL must be configured.")

    prompt = REWRITE_PROMPT_TEMPLATE.format(
        history=_format_history(history),
        query=query,
    )
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
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
        timeout=20,
    )
    response.raise_for_status()

    rewritten = _extract_answer(response.json()).strip()
    return rewritten or query


def _extract_answer(response_data: dict) -> str:
    content = response_data.get("output_text")
    if content is None and response_data.get("choices"):
        choice = response_data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or choice.get("text")

    if not isinstance(content, str):
        raise ValueError("AI response did not contain answer content.")

    return content


def _format_history(history: list[dict]) -> str:
    lines = []
    for message in history:
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role and content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) or "(none)"


def _chat_completions_url() -> str:
    base_url = settings.AI_BASE_URL.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/chat/completions"
