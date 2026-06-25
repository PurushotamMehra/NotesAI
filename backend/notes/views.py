import threading
import time

from django.conf import settings
from django.db import close_old_connections
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AICallLog,
    ChatMessage,
    ChatSession,
    FollowUpQuestion,
    Note,
    NoteEntity,
    Person,
    Topic,
)
from .serializers import ChatSerializer, NoteSerializer, NoteUpdateSerializer, SearchSerializer
from .services.ai_processor import process_note
from .services.chat_service import FALLBACK_ANSWER, generate_answer, rewrite_retrieval_query
from .services.embedding_service import generate_embedding
from .services.search_service import semantic_search

CHAT_CONTEXT_LIMIT = 6000
PROMPT_VERSION = "note-v1"


class NoteCreateView(APIView):
    def get(self, request):
        notes = Note.objects.order_by("-created_at")[:100]
        return Response(
            {
                "results": [_serialize_chat_source(note) for note in notes],
            }
        )

    def post(self, request):
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_input = serializer.validated_data["raw_input"]
        input_type = serializer.validated_data["input_type"]
        note = Note.objects.create(raw_input=raw_input, input_type=input_type)
        if settings.PROCESS_NOTES_ASYNC:
            _schedule_note_memory_refresh(note.id, rerun_ai=True)
        else:
            _refresh_note_memory(note, rerun_ai=True)
            note.refresh_from_db()
        people, topics = _note_people_topics(note)

        return Response(
            {
                **_serialize_note_result(note),
                "cleaned_note": note.cleaned_note,
                "summary": note.summary,
                "people": people,
                "topics": topics,
            },
            status=status.HTTP_201_CREATED,
        )


class NoteDetailView(APIView):
    def patch(self, request, note_id):
        note = get_object_or_404(Note, id=note_id)
        serializer = NoteUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        rerun_ai = False
        if "raw_input" in serializer.validated_data:
            note.raw_input = serializer.validated_data["raw_input"]
            rerun_ai = True
        if "input_type" in serializer.validated_data:
            note.input_type = serializer.validated_data["input_type"]
        note.save(update_fields=["raw_input", "input_type"])

        _refresh_note_memory(note, rerun_ai=rerun_ai)
        return Response(_serialize_note_result(note))

    def delete(self, request, note_id):
        note = get_object_or_404(Note, id=note_id)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteReprocessView(APIView):
    def post(self, request, note_id):
        note = get_object_or_404(Note, id=note_id)
        _refresh_note_memory(note, rerun_ai=True)
        return Response(_serialize_note_result(note))


class SearchView(APIView):
    def post(self, request):
        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            notes = _semantic_search_with_logging(
                serializer.validated_data["query"],
                serializer.validated_data["limit"],
            )
        except Exception:
            return Response(
                {"detail": "Semantic search is currently unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "results": [_serialize_note_result(note) for note in notes],
            }
        )


class ChatView(APIView):
    def post(self, request):
        serializer = ChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        session = _get_or_create_chat_session(serializer.validated_data.get("session_id"))
        history = _recent_chat_history(session)
        retrieval_query = _rewrite_query_with_fallback(query, history)

        user_message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=query,
            metadata={"retrieval_query": retrieval_query},
        )

        try:
            notes = _semantic_search_with_logging(
                retrieval_query,
                limit=6,
                chat_message=user_message,
            )
        except Exception:
            notes = []

        if not notes:
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=FALLBACK_ANSWER,
                metadata={"sources": [], "reply_to": user_message.id},
            )
            return Response(
                {
                    "answer": assistant_message.content,
                    "session_id": session.id,
                    "sources": [],
                }
            )

        unique_notes = _unique_notes(notes)
        context = _build_chat_context(unique_notes)
        try:
            answer = _log_ai_call(
                "chat_answer",
                settings.AI_MODEL,
                lambda: generate_answer(retrieval_query, [context]),
                chat_message=user_message,
            )
        except Exception:
            answer = FALLBACK_ANSWER

        sources = [_serialize_chat_source(note) for note in unique_notes[:3]]
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=answer,
            metadata={
                "sources": sources,
                "reply_to": user_message.id,
                "retrieval_query": retrieval_query,
            },
        )

        return Response(
            {
                "answer": answer,
                "session_id": session.id,
                "sources": sources,
            }
        )


def _process_with_fallback(raw_input: str) -> dict:
    processed, _ = _process_with_status(raw_input)
    return processed


def _schedule_note_memory_refresh(note_id: int, rerun_ai: bool) -> None:
    def worker() -> None:
        close_old_connections()
        try:
            note = Note.objects.get(id=note_id)
            _refresh_note_memory(note, rerun_ai=rerun_ai)
        finally:
            close_old_connections()

    transaction.on_commit(
        lambda: threading.Thread(
            target=worker,
            name=f"note-memory-refresh-{note_id}",
            daemon=True,
        ).start()
    )


def _process_with_status(raw_input: str, note: Note | None = None) -> tuple[dict, str]:
    try:
        processed = _log_ai_call(
            "note_processing",
            settings.AI_MODEL,
            lambda: process_note(raw_input),
            note=note,
        )
        return _processed_with_text_fallback(raw_input, processed), ""
    except Exception as exc:
        return ({
            "cleaned_note": raw_input,
            "summary": "",
            "people": [],
            "topics": [],
            "events": [],
            "follow_up_questions": [],
        }, str(exc))


def _generate_embedding_with_fallback(text: str):
    embedding, _ = _generate_embedding_with_status(text)
    return embedding


def _generate_embedding_with_status(
    text: str,
    note: Note | None = None,
) -> tuple[list[float] | None, str]:
    try:
        embedding = _log_ai_call(
            "embedding",
            settings.EMBEDDING_MODEL,
            lambda: generate_embedding(text),
            note=note,
        )
        return embedding, ""
    except Exception as exc:
        return None, str(exc)


def _refresh_note_memory(note: Note, rerun_ai: bool) -> tuple[list[str], list[str]]:
    if rerun_ai:
        processed = _apply_processing(note)
    else:
        embedding = _apply_embedding(note, note.cleaned_note or note.raw_input)
        note.embedding = embedding
        note.save(update_fields=["embedding"])
        return _note_people_topics(note)

    embedding = _apply_embedding(note, processed["cleaned_note"])

    with transaction.atomic():
        NoteEntity.objects.filter(note=note).delete()
        FollowUpQuestion.objects.filter(note=note).delete()
        people = _link_people(note, processed["people"])
        topics = _link_topics(note, processed["topics"])
        _store_follow_up_questions(note, processed["follow_up_questions"])
        note.embedding = embedding
        note.save(update_fields=["embedding"])

    return people, topics


def _apply_processing(note: Note) -> dict:
    note.processing_status = Note.ProcessingStatus.PENDING
    note.processing_error = ""
    note.ai_model = settings.AI_MODEL
    note.prompt_version = PROMPT_VERSION
    note.processing_started_at = timezone.now()
    note.processing_completed_at = None
    note.save(
        update_fields=[
            "processing_status",
            "processing_error",
            "ai_model",
            "prompt_version",
            "processing_started_at",
            "processing_completed_at",
        ]
    )

    processed, error = _process_with_status(note.raw_input, note=note)
    note.cleaned_note = processed["cleaned_note"]
    note.summary = processed["summary"]
    note.processing_status = (
        Note.ProcessingStatus.FALLBACK if error else Note.ProcessingStatus.COMPLETED
    )
    note.processing_error = error
    note.processing_completed_at = timezone.now()
    note.save(
        update_fields=[
            "cleaned_note",
            "summary",
            "processing_status",
            "processing_error",
            "processing_completed_at",
        ]
    )
    return processed


def _apply_embedding(note: Note, text: str):
    note.embedding_status = Note.EmbeddingStatus.PENDING
    note.embedding_error = ""
    note.embedding_model = settings.EMBEDDING_MODEL
    note.embedding_started_at = timezone.now()
    note.embedding_completed_at = None
    note.save(
        update_fields=[
            "embedding_status",
            "embedding_error",
            "embedding_model",
            "embedding_started_at",
            "embedding_completed_at",
        ]
    )

    embedding, error = _generate_embedding_with_status(text, note=note)
    note.embedding_status = (
        Note.EmbeddingStatus.FAILED if error else Note.EmbeddingStatus.COMPLETED
    )
    note.embedding_error = error
    note.embedding_completed_at = timezone.now()
    note.save(
        update_fields=[
            "embedding_status",
            "embedding_error",
            "embedding_completed_at",
        ]
    )
    return embedding


def _processed_with_text_fallback(raw_input: str, processed: dict) -> dict:
    cleaned_note = str(processed.get("cleaned_note") or "").strip()
    summary = str(processed.get("summary") or "").strip()
    return {
        **processed,
        "cleaned_note": cleaned_note or raw_input,
        "summary": summary,
    }


def _link_people(note: Note, names: list[str]) -> list[str]:
    people = []
    for name in _unique_cleaned(names):
        person = _get_or_create_case_insensitive(Person, name)
        NoteEntity.objects.get_or_create(
            note=note,
            entity_type=NoteEntity.EntityType.PERSON,
            entity_id=person.id,
        )
        people.append(person.name)
    return people


def _link_topics(note: Note, names: list[str]) -> list[str]:
    topics = []
    for name in _unique_cleaned(names):
        topic_name = name.lower()
        topic = _get_or_create_case_insensitive(Topic, topic_name)
        NoteEntity.objects.get_or_create(
            note=note,
            entity_type=NoteEntity.EntityType.TOPIC,
            entity_id=topic.id,
        )
        topics.append(topic.name)
    return topics


def _store_follow_up_questions(note: Note, questions: list[str]) -> None:
    FollowUpQuestion.objects.bulk_create(
        [
            FollowUpQuestion(note=note, question=question)
            for question in _unique_cleaned(questions)
        ]
    )


def _get_or_create_chat_session(session_id: int | None) -> ChatSession:
    if session_id:
        session = ChatSession.objects.filter(id=session_id).first()
        if session:
            return session
    return ChatSession.objects.create()


def _recent_chat_history(session: ChatSession, limit: int = 10) -> list[dict]:
    messages = session.messages.order_by("-created_at", "-id")[:limit]
    return [
        {"role": message.role, "content": message.content}
        for message in reversed(list(messages))
    ]


def _rewrite_query_with_fallback(query: str, history: list[dict]) -> str:
    if not history:
        return query
    try:
        rewritten = _log_ai_call(
            "chat_query_rewrite",
            settings.AI_MODEL,
            lambda: rewrite_retrieval_query(query, history),
        ).strip()
    except Exception:
        return query
    return rewritten or query


def _semantic_search_with_logging(
    query: str,
    limit: int,
    chat_message: ChatMessage | None = None,
) -> list[Note]:
    return _log_ai_call(
        "semantic_search",
        settings.EMBEDDING_MODEL,
        lambda: semantic_search(query, limit=limit),
        chat_message=chat_message,
    )


def _get_or_create_case_insensitive(model, name: str):
    existing = model.objects.filter(name__iexact=name).first()
    if existing:
        return existing
    return model.objects.create(name=name)


def _build_chat_context(notes: list[Note]) -> str:
    sections = []
    current_size = 0
    for note in notes:
        section = _build_note_context(note)
        if not section:
            continue

        if current_size + len(section) > CHAT_CONTEXT_LIMIT:
            remaining = CHAT_CONTEXT_LIMIT - current_size
            if remaining <= 0:
                break
            sections.append(section[:remaining])
            break

        sections.append(section)
        current_size += len(section)

    return "\n\n".join(sections)


def _build_note_context(note: Note) -> str:
    result = _serialize_note_result(note)
    source_text = _note_source_text(note)
    parts = [
        f"Note ID: {note.id}",
        f"Summary: {result['summary']}",
        f"Source text: {source_text}",
    ]
    if result["people"]:
        parts.append(f"People: {', '.join(result['people'])}")
    if result["topics"]:
        parts.append(f"Topics: {', '.join(result['topics'])}")
    return "\n".join(part for part in parts if part.strip())


def _serialize_chat_source(note: Note) -> dict:
    source_text = _note_source_text(note)
    preview = _compact_source_label(source_text, limit=120)
    return {
        "note_id": note.id,
        "preview": preview,
        "summary": note.summary or _compact_source_label(source_text),
        "cleaned_note": note.cleaned_note,
        "source_text": source_text,
        **_serialize_note_status(note),
    }


def _serialize_note_result(note: Note) -> dict:
    people, topics = _note_people_topics(note)
    return {
        "id": note.id,
        "summary": note.summary,
        "cleaned_note": note.cleaned_note,
        "source_text": _note_source_text(note),
        "raw_input": note.raw_input,
        "people": people,
        "topics": topics,
        **_serialize_note_status(note),
    }


def _note_people_topics(note: Note) -> tuple[list[str], list[str]]:
    people_ids = note.entities.filter(
        entity_type=NoteEntity.EntityType.PERSON,
    ).values_list("entity_id", flat=True)
    topic_ids = note.entities.filter(
        entity_type=NoteEntity.EntityType.TOPIC,
    ).values_list("entity_id", flat=True)
    return (
        list(
            Person.objects.filter(id__in=people_ids)
            .order_by("name")
            .values_list("name", flat=True)
        ),
        list(
            Topic.objects.filter(id__in=topic_ids)
            .order_by("name")
            .values_list("name", flat=True)
        ),
    )


def _serialize_note_status(note: Note) -> dict:
    return {
        "processing_status": note.processing_status,
        "embedding_status": note.embedding_status,
        "processing_error": note.processing_error,
        "embedding_error": note.embedding_error,
        "ai_model": note.ai_model,
        "embedding_model": note.embedding_model,
        "prompt_version": note.prompt_version,
    }


def _unique_cleaned(values: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            cleaned.append(normalized)
            seen.add(key)
    return cleaned


def _unique_notes(notes: list[Note]) -> list[Note]:
    unique = []
    seen = set()
    for note in notes:
        if note.id in seen:
            continue
        unique.append(note)
        seen.add(note.id)
    return unique


def _note_source_text(note: Note) -> str:
    return (note.cleaned_note or note.raw_input or "").strip()


def _compact_source_label(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _log_ai_call(
    task_type: str,
    provider_model: str,
    call,
    note: Note | None = None,
    chat_message: ChatMessage | None = None,
):
    started = time.monotonic()
    try:
        result = call()
    except Exception as exc:
        AICallLog.objects.create(
            task_type=task_type,
            provider_model=provider_model or "",
            latency_ms=_elapsed_ms(started),
            success=False,
            error_message=str(exc),
            note=note,
            chat_message=chat_message,
        )
        raise

    AICallLog.objects.create(
        task_type=task_type,
        provider_model=provider_model or "",
        latency_ms=_elapsed_ms(started),
        success=True,
        note=note,
        chat_message=chat_message,
    )
    return result


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))
