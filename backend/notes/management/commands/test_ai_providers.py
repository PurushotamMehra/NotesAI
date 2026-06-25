import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from notes.services.embedding_service import generate_embedding


class Command(BaseCommand):
    help = "Manually test configured AI and embedding providers."

    def handle(self, *args, **options):
        self._test_deepseek()
        self._test_gemini_embedding()

    def _test_deepseek(self):
        missing = _missing_settings(
            {
                "AI_API_KEY": settings.AI_API_KEY,
                "AI_BASE_URL": settings.AI_BASE_URL,
                "AI_MODEL": settings.AI_MODEL,
            }
        )
        self.stdout.write(f"DeepSeek model: {settings.AI_MODEL or '(missing)'}")
        if missing:
            self.stdout.write(f"DeepSeek failure: missing {', '.join(missing)}")
            return

        started_at = time.perf_counter()
        try:
            response = requests.post(
                _deepseek_chat_url(),
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.AI_MODEL,
                    "messages": [
                        {"role": "user", "content": "Reply with only: ok"},
                    ],
                    "temperature": 0,
                    "max_tokens": 8,
                },
                timeout=30,
            )
            response.raise_for_status()
            answer = _extract_chat_answer(response.json())
        except Exception as exc:
            latency_ms = _elapsed_ms(started_at)
            self.stdout.write(f"DeepSeek success: no")
            self.stdout.write(f"DeepSeek latency: {latency_ms} ms")
            self.stdout.write(f"DeepSeek failure: {_safe_error(exc)}")
            return

        latency_ms = _elapsed_ms(started_at)
        self.stdout.write(f"DeepSeek success: yes")
        self.stdout.write(f"DeepSeek latency: {latency_ms} ms")
        self.stdout.write(f"DeepSeek response: {_compact_answer(answer)}")

    def _test_gemini_embedding(self):
        missing = _missing_settings(
            {
                "EMBEDDING_API_KEY": settings.EMBEDDING_API_KEY,
                "EMBEDDING_BASE_URL": settings.EMBEDDING_BASE_URL,
                "EMBEDDING_MODEL": settings.EMBEDDING_MODEL,
                "EMBEDDING_DIMENSIONS": settings.EMBEDDING_DIMENSIONS,
            }
        )
        self.stdout.write(
            f"Gemini expected dimensions: {settings.EMBEDDING_DIMENSIONS}"
        )
        if missing:
            self.stdout.write(f"Gemini embedding success: no")
            self.stdout.write(f"Gemini embedding failure: missing {', '.join(missing)}")
            return

        started_at = time.perf_counter()
        try:
            embedding = generate_embedding("test memory note")
        except Exception as exc:
            latency_ms = _elapsed_ms(started_at)
            self.stdout.write(f"Gemini embedding success: no")
            self.stdout.write(f"Gemini latency: {latency_ms} ms")
            self.stdout.write(f"Gemini embedding failure: {_safe_error(exc)}")
            return

        latency_ms = _elapsed_ms(started_at)
        vector_length = len(embedding)
        self.stdout.write(f"Gemini embedding success: yes")
        self.stdout.write(f"Gemini returned vector length: {vector_length}")
        self.stdout.write(f"Gemini latency: {latency_ms} ms")
        if vector_length != settings.EMBEDDING_DIMENSIONS:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: Gemini returned "
                    f"{vector_length} dimensions, expected "
                    f"{settings.EMBEDDING_DIMENSIONS}."
                )
            )


def _deepseek_chat_url() -> str:
    base_url = settings.AI_BASE_URL.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/chat/completions"


def _extract_chat_answer(response_data: dict) -> str:
    if response_data.get("choices"):
        choice = response_data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content") or choice.get("text")
        if isinstance(content, str):
            return content.strip()

    content = response_data.get("output_text")
    if isinstance(content, str):
        return content.strip()

    raise ValueError("AI response did not contain answer content.")


def _missing_settings(values: dict) -> list[str]:
    return [name for name, value in values.items() if not value]


def _elapsed_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"HTTP {exc.response.status_code}: {_truncate(exc.response.text)}"
    return _truncate(str(exc))


def _compact_answer(answer: str) -> str:
    return _truncate(answer.strip().replace("\n", " "))


def _truncate(value: str, limit: int = 240) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."
