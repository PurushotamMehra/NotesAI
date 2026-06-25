import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from rest_framework.test import APIClient

from notes.models import Note
from notes.services.search_service import semantic_search
from notes.views import _build_chat_context, _serialize_chat_source


TEST_NOTE = "Jhon wants to interview for a Java developer position on Sunday."
FIRST_QUESTION = "What role is Jhon trying for?"
FOLLOW_UP_QUESTION = "When is it?"


class Command(BaseCommand):
    help = "Create a test note and print each backend RAG handoff."

    def handle(self, *args, **options):
        try:
            connection.ensure_connection()
        except Exception as exc:
            self.stdout.write("database connection: no")
            self.stdout.write(f"database failure: {_safe_error(exc)}")
            return

        self.stdout.write("database connection: yes")
        client = APIClient()
        client.raise_request_exception = False
        http_host = _http_host()

        create_response = client.post(
            "/api/notes/",
            {"raw_input": TEST_NOTE, "input_type": "text"},
            format="json",
            HTTP_HOST=http_host,
        )
        self.stdout.write(f"note create status: {create_response.status_code}")
        if create_response.status_code >= 400:
            self.stdout.write(
                f"note create response: {_safe_json(_response_payload(create_response))}"
            )
            return

        note = Note.objects.order_by("-created_at").first()
        if note is None:
            self.stdout.write("created note id: (missing)")
            return

        self.stdout.write(f"created note id: {note.id}")
        self.stdout.write(f"raw/content text field: {note.raw_input}")
        self.stdout.write(f"cleaned/processed text field: {note.cleaned_note}")
        self.stdout.write(f"summary field: {note.summary}")
        self.stdout.write(f"embedding exists: {_yes_no(note.embedding is not None)}")
        self.stdout.write(f"embedding vector length: {_vector_length(note.embedding)}")

        if not (note.cleaned_note or "").strip():
            self.stdout.write("source text fallback: cleaned_note is empty; raw_input is required")
        if not (note.raw_input or "").strip():
            self.stdout.write("source text error: raw_input is empty")

        try:
            results = semantic_search(FIRST_QUESTION, limit=6)
        except Exception as exc:
            results = []
            self.stdout.write(f"semantic search failure: {_safe_error(exc)}")

        self.stdout.write(f"semantic search result count: {len(results)}")
        self.stdout.write(f"result note ids: {[result.id for result in results]}")
        self.stdout.write(
            "result scores/distances: "
            f"{[_distance_for_display(result) for result in results]}"
        )

        context = _build_chat_context(results)
        self.stdout.write("exact source text passed into the chat prompt:")
        self.stdout.write(context or "(empty)")

        serialized_sources = [_serialize_chat_source(result) for result in results]
        self.stdout.write("exact sources returned by the API serializer:")
        self.stdout.write(_safe_json(serialized_sources))

        chat_response = client.post(
            "/api/chat/",
            {"query": FIRST_QUESTION},
            format="json",
            HTTP_HOST=http_host,
        )
        first_payload = _response_payload(chat_response)
        self.stdout.write(f"first chat status: {chat_response.status_code}")
        self.stdout.write("first chat response:")
        self.stdout.write(_safe_json(first_payload))

        follow_up_response = client.post(
            "/api/chat/",
            {
                "query": FOLLOW_UP_QUESTION,
                "session_id": _session_id(first_payload),
            },
            format="json",
            HTTP_HOST=http_host,
        )
        self.stdout.write(f"follow-up chat status: {follow_up_response.status_code}")
        self.stdout.write("follow-up chat response:")
        self.stdout.write(_safe_json(_response_payload(follow_up_response)))


def _vector_length(vector) -> str:
    if vector is None:
        return "0"
    try:
        return str(len(vector))
    except TypeError:
        return "(unknown)"


def _distance_for_display(result) -> str:
    distance = getattr(result, "distance", None)
    if distance is None:
        return "(missing)"
    try:
        return f"{float(distance):.6f}"
    except (TypeError, ValueError):
        return str(distance)


def _safe_json(value) -> str:
    return json.dumps(value, indent=2, default=str)


def _response_payload(response):
    if hasattr(response, "data"):
        return response.data
    return {
        "status_code": response.status_code,
        "reason": getattr(response, "reason_phrase", ""),
    }


def _session_id(payload) -> int | None:
    if isinstance(payload, dict):
        return payload.get("session_id")
    return None


def _http_host() -> str:
    for host in settings.ALLOWED_HOSTS:
        if host not in {"*", ".localhost"}:
            return host
    return "localhost"


def _safe_error(exc: Exception) -> str:
    return str(exc).replace("\n", " ")[:240]


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
