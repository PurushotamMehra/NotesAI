from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from .models import AICallLog, ChatMessage, ChatSession, FollowUpQuestion, Note, NoteEntity, Person, Topic
from .services.ai_processor import PROMPT_TEMPLATE, process_note
from .services.chat_service import FALLBACK_ANSWER, generate_answer, rewrite_retrieval_query
from .services.embedding_service import generate_embedding


@override_settings(PROCESS_NOTES_ASYNC=False)
class NoteIngestionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    def test_post_note_stores_ai_structured_output(
        self,
        mock_process_note,
        mock_generate_embedding,
    ):
        mock_process_note.return_value = {
            "cleaned_note": "Met Sara today. She suggested improving onboarding for my reading app.",
            "summary": "Sara suggested improving onboarding for the reading app.",
            "people": ["Sara"],
            "topics": ["onboarding", "product", "app"],
            "events": [],
            "follow_up_questions": ["What onboarding changes should be prioritized?"],
        }
        mock_generate_embedding.return_value = _vector(0.9, 0.1)

        response = self.client.post(
            "/api/notes/",
            {
                "raw_input": "Met Sara today. She suggested improving onboarding for my reading app.",
                "input_type": "text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["people"], ["Sara"])
        self.assertIn("onboarding", response.data["topics"])
        self.assertTrue(response.data["cleaned_note"])
        self.assertEqual(response.data["processing_status"], "completed")
        self.assertEqual(response.data["embedding_status"], "completed")

        note = Note.objects.get()
        self.assertEqual(note.cleaned_note, response.data["cleaned_note"])
        self.assertEqual(note.summary, response.data["summary"])
        self.assertIsNotNone(note.embedding)
        self.assertEqual(note.processing_status, Note.ProcessingStatus.COMPLETED)
        self.assertEqual(note.embedding_status, Note.EmbeddingStatus.COMPLETED)
        self.assertEqual(AICallLog.objects.filter(success=True).count(), 2)

        sara = Person.objects.get(name="Sara")
        onboarding = Topic.objects.get(name="onboarding")
        self.assertTrue(
            NoteEntity.objects.filter(
                note=note,
                entity_type=NoteEntity.EntityType.PERSON,
                entity_id=sara.id,
            ).exists()
        )
        self.assertTrue(
            NoteEntity.objects.filter(
                note=note,
                entity_type=NoteEntity.EntityType.TOPIC,
                entity_id=onboarding.id,
            ).exists()
        )
        self.assertEqual(FollowUpQuestion.objects.get(note=note).status, "pending")

    @patch("notes.views.process_note")
    def test_ai_failure_still_stores_raw_note(self, mock_process_note):
        mock_process_note.side_effect = RuntimeError("AI unavailable")

        response = self.client.post(
            "/api/notes/",
            {"raw_input": "A raw fallback note.", "input_type": "text"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cleaned_note"], "A raw fallback note.")
        self.assertEqual(response.data["summary"], "")
        self.assertEqual(response.data["processing_status"], "fallback")
        self.assertIn(response.data["embedding_status"], {"completed", "failed"})
        self.assertEqual(Note.objects.get().raw_input, "A raw fallback note.")
        self.assertIn("AI unavailable", Note.objects.get().processing_error)

    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    @override_settings(PROCESS_NOTES_ASYNC=True)
    def test_post_note_returns_before_ai_processing_when_async_enabled(
        self,
        mock_process_note,
        mock_generate_embedding,
    ):
        response = self.client.post(
            "/api/notes/",
            {
                "raw_input": "Save quickly before AI runs.",
                "input_type": "text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["raw_input"], "Save quickly before AI runs.")
        self.assertEqual(response.data["processing_status"], "pending")
        self.assertEqual(response.data["embedding_status"], "pending")
        mock_process_note.assert_not_called()
        mock_generate_embedding.assert_not_called()

    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    def test_empty_processed_note_falls_back_to_raw_input(
        self,
        mock_process_note,
        mock_generate_embedding,
    ):
        mock_process_note.return_value = {
            "cleaned_note": "",
            "summary": "",
            "people": [],
            "topics": [],
            "events": [],
            "follow_up_questions": [],
        }
        mock_generate_embedding.return_value = _vector(0.5, 0.5)

        response = self.client.post(
            "/api/notes/",
            {
                "raw_input": "Rahul is preparing for a Python developer interview.",
                "input_type": "text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["cleaned_note"],
            "Rahul is preparing for a Python developer interview.",
        )
        mock_generate_embedding.assert_called_once_with(
            "Rahul is preparing for a Python developer interview."
        )

    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    def test_embedding_failure_marks_note_failed(
        self,
        mock_process_note,
        mock_generate_embedding,
    ):
        mock_process_note.return_value = {
            "cleaned_note": "Met Sara.",
            "summary": "Met Sara.",
            "people": [],
            "topics": [],
            "events": [],
            "follow_up_questions": [],
        }
        mock_generate_embedding.side_effect = RuntimeError("embedding down")

        response = self.client.post(
            "/api/notes/",
            {"raw_input": "Met Sara.", "input_type": "text"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        note = Note.objects.get()
        self.assertIsNone(note.embedding)
        self.assertEqual(note.embedding_status, Note.EmbeddingStatus.FAILED)
        self.assertIn("embedding down", note.embedding_error)
        self.assertEqual(response.data["embedding_status"], "failed")

    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    def test_reprocess_endpoint_updates_statuses_and_entities(
        self,
        mock_process_note,
        mock_generate_embedding,
    ):
        note = Note.objects.create(
            raw_input="Raw Sara note.",
            cleaned_note="Raw Sara note.",
            summary="",
            input_type=Note.InputType.TEXT,
            processing_status=Note.ProcessingStatus.FALLBACK,
            embedding_status=Note.EmbeddingStatus.FAILED,
            processing_error="old",
            embedding_error="old",
        )
        mock_process_note.return_value = {
            "cleaned_note": "Sara discussed onboarding.",
            "summary": "Sara discussed onboarding.",
            "people": ["Sara"],
            "topics": ["Onboarding"],
            "events": [],
            "follow_up_questions": ["Follow up?"],
        }
        mock_generate_embedding.return_value = _vector(0.8, 0.2)

        response = self.client.post(f"/api/notes/{note.id}/reprocess/", format="json")

        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.processing_status, Note.ProcessingStatus.COMPLETED)
        self.assertEqual(note.embedding_status, Note.EmbeddingStatus.COMPLETED)
        self.assertEqual(note.processing_error, "")
        self.assertEqual(note.embedding_error, "")
        self.assertEqual(response.data["people"], ["Sara"])
        self.assertEqual(FollowUpQuestion.objects.filter(note=note).count(), 1)

    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    def test_patch_note_regenerates_memory_and_replaces_related_rows(
        self,
        mock_process_note,
        mock_generate_embedding,
    ):
        note = Note.objects.create(
            raw_input="Old note.",
            cleaned_note="Old note.",
            summary="Old",
            input_type=Note.InputType.TEXT,
        )
        old_topic = Topic.objects.create(name="old")
        NoteEntity.objects.create(
            note=note,
            entity_type=NoteEntity.EntityType.TOPIC,
            entity_id=old_topic.id,
        )
        FollowUpQuestion.objects.create(note=note, question="Old question?")
        mock_process_note.return_value = {
            "cleaned_note": "New note about Python.",
            "summary": "Python note.",
            "people": [],
            "topics": ["Python"],
            "events": [],
            "follow_up_questions": ["New question?"],
        }
        mock_generate_embedding.return_value = _vector(0.3, 0.7)

        response = self.client.patch(
            f"/api/notes/{note.id}/",
            {"raw_input": "New note about Python.", "input_type": "text"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.raw_input, "New note about Python.")
        self.assertEqual(note.embedding_status, Note.EmbeddingStatus.COMPLETED)
        self.assertEqual(response.data["topics"], ["python"])
        self.assertEqual(FollowUpQuestion.objects.get(note=note).question, "New question?")

    def test_delete_note_removes_related_entities_and_followups(self):
        note = Note.objects.create(
            raw_input="Delete me.",
            cleaned_note="Delete me.",
            summary="Delete",
            input_type=Note.InputType.TEXT,
        )
        topic = Topic.objects.create(name="delete")
        NoteEntity.objects.create(
            note=note,
            entity_type=NoteEntity.EntityType.TOPIC,
            entity_id=topic.id,
        )
        FollowUpQuestion.objects.create(note=note, question="Delete?")

        response = self.client.delete(f"/api/notes/{note.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Note.objects.filter(id=note.id).exists())
        self.assertEqual(NoteEntity.objects.count(), 0)
        self.assertEqual(FollowUpQuestion.objects.count(), 0)

    def test_get_notes_lists_saved_notes(self):
        note = Note.objects.create(
            raw_input="Met Sara.",
            cleaned_note="Sara suggested improving onboarding.",
            summary="Sara mentioned onboarding.",
            input_type=Note.InputType.TEXT,
        )

        response = self.client.get("/api/notes/")

        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertEqual(result["note_id"], note.id)
        self.assertEqual(result["preview"], note.cleaned_note)
        self.assertEqual(result["summary"], note.summary)
        self.assertEqual(result["cleaned_note"], note.cleaned_note)
        self.assertEqual(result["source_text"], note.cleaned_note)
        self.assertIn("processing_status", result)

    @patch("notes.services.search_service.generate_embedding")
    def test_semantic_search_retrieves_onboarding_note(self, mock_generate_embedding):
        onboarding_note = Note.objects.create(
            raw_input="Sara had feedback about first-run setup.",
            cleaned_note="Sara recommended improving first-run setup for the reading app.",
            summary="Sara suggested improving onboarding.",
            input_type=Note.InputType.TEXT,
            embedding=_vector(1.0, 0.0),
        )
        other_note = Note.objects.create(
            raw_input="Buy coffee.",
            cleaned_note="Buy coffee tomorrow.",
            summary="Coffee reminder.",
            input_type=Note.InputType.TEXT,
            embedding=_vector(0.0, 1.0),
        )
        sara = Person.objects.create(name="Sara")
        onboarding = Topic.objects.create(name="onboarding")
        Topic.objects.create(name="errand")
        NoteEntity.objects.create(
            note=onboarding_note,
            entity_type=NoteEntity.EntityType.PERSON,
            entity_id=sara.id,
        )
        NoteEntity.objects.create(
            note=onboarding_note,
            entity_type=NoteEntity.EntityType.TOPIC,
            entity_id=onboarding.id,
        )
        NoteEntity.objects.create(
            note=other_note,
            entity_type=NoteEntity.EntityType.TOPIC,
            entity_id=Topic.objects.get(name="errand").id,
        )
        mock_generate_embedding.return_value = _vector(1.0, 0.0)

        response = self.client.post(
            "/api/search/",
            {"query": "How to improve onboarding?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], onboarding_note.id)
        self.assertIn("onboarding", response.data["results"][0]["topics"])
        self.assertEqual(response.data["results"][0]["people"], ["Sara"])
        self.assertIn("embedding_status", response.data["results"][0])

    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    def test_chat_answers_from_retrieved_notes(
        self,
        mock_semantic_search,
        mock_generate_answer,
    ):
        note = Note.objects.create(
            raw_input="Met Sara today.",
            cleaned_note="Sara suggested improving onboarding for my reading app.",
            summary="Sara suggested improving onboarding.",
            input_type=Note.InputType.TEXT,
            embedding=_vector(1.0, 0.0),
        )
        mock_semantic_search.return_value = [note]
        mock_generate_answer.return_value = (
            "Sara suggested improving onboarding for the reading app."
        )

        response = self.client.post(
            "/api/chat/",
            {"query": "What did Sara suggest about onboarding?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("onboarding", response.data["answer"])
        self.assertEqual(response.data["sources"][0]["note_id"], note.id)
        self.assertEqual(response.data["sources"][0]["preview"], note.cleaned_note)
        self.assertEqual(response.data["sources"][0]["summary"], note.summary)
        self.assertIn("processing_status", response.data["sources"][0])
        mock_semantic_search.assert_called_once_with(
            "What did Sara suggest about onboarding?",
            limit=6,
        )
        context = mock_generate_answer.call_args.args[1][0]
        self.assertIn("Sara suggested improving onboarding", context)

    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    def test_chat_uses_raw_input_when_cleaned_note_is_empty(
        self,
        mock_semantic_search,
        mock_generate_answer,
    ):
        note = Note.objects.create(
            raw_input="Rahul is preparing for a Python developer interview.",
            cleaned_note="",
            summary="",
            input_type=Note.InputType.TEXT,
            embedding=_vector(1.0, 0.0),
        )
        mock_semantic_search.return_value = [note]
        mock_generate_answer.return_value = (
            "Rahul is preparing for a Python developer interview."
        )

        response = self.client.post(
            "/api/chat/",
            {"query": "Who is preparing for a developer interview?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        context = mock_generate_answer.call_args.args[1][0]
        self.assertIn("Source text: Rahul is preparing", context)
        self.assertEqual(response.data["sources"][0]["note_id"], note.id)
        self.assertEqual(
            response.data["sources"][0]["preview"],
            "Rahul is preparing for a Python developer interview.",
        )
        self.assertEqual(response.data["sources"][0]["cleaned_note"], "")
        self.assertEqual(
            response.data["sources"][0]["source_text"],
            "Rahul is preparing for a Python developer interview.",
        )

    @patch("notes.views.semantic_search")
    def test_chat_returns_fallback_when_no_notes_match(self, mock_semantic_search):
        mock_semantic_search.return_value = []

        response = self.client.post(
            "/api/chat/",
            {"query": "What did I say about blockchain?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["answer"], FALLBACK_ANSWER)
        self.assertIn("session_id", response.data)
        self.assertEqual(response.data["sources"], [])
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 2)

    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    def test_chat_creates_new_session_and_stores_messages(
        self,
        mock_semantic_search,
        mock_generate_answer,
    ):
        note = Note.objects.create(
            raw_input="Jhon wants to interview for a Java developer position on Sunday.",
            cleaned_note="Jhon wants to interview for a Java developer position on Sunday.",
            summary="Jhon has a Java developer interview on Sunday.",
            input_type=Note.InputType.TEXT,
            embedding=_vector(1.0, 0.0),
        )
        mock_semantic_search.return_value = [note]
        mock_generate_answer.return_value = "Jhon is trying for a Java developer role."

        response = self.client.post(
            "/api/chat/",
            {"query": "What role is Jhon trying for?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        session_id = response.data["session_id"]
        self.assertTrue(ChatSession.objects.filter(id=session_id).exists())
        self.assertEqual(
            list(ChatMessage.objects.values_list("role", flat=True)),
            ["user", "assistant"],
        )

    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    def test_chat_continues_existing_session(
        self,
        mock_semantic_search,
        mock_generate_answer,
    ):
        session = ChatSession.objects.create()
        note = Note.objects.create(
            raw_input="Jhon wants to interview for a Java developer position on Sunday.",
            cleaned_note="Jhon wants to interview for a Java developer position on Sunday.",
            summary="Jhon has a Java developer interview on Sunday.",
            input_type=Note.InputType.TEXT,
            embedding=_vector(1.0, 0.0),
        )
        mock_semantic_search.return_value = [note]
        mock_generate_answer.return_value = "The note says it is on Sunday."

        response = self.client.post(
            "/api/chat/",
            {"query": "When is it?", "session_id": session.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_id"], session.id)
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertEqual(session.messages.count(), 2)

    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    @patch("notes.views.rewrite_retrieval_query")
    def test_follow_up_question_uses_previous_context_for_retrieval(
        self,
        mock_rewrite_query,
        mock_semantic_search,
        mock_generate_answer,
    ):
        session = ChatSession.objects.create()
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content="What role is Jhon trying for?",
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=(
                "Jhon is trying for a Java developer role. "
                "The note says the interview is on Sunday."
            ),
        )
        note = Note.objects.create(
            raw_input="Jhon wants to interview for a Java developer position on Sunday.",
            cleaned_note="Jhon wants to interview for a Java developer position on Sunday.",
            summary="Jhon has a Java developer interview on Sunday.",
            input_type=Note.InputType.TEXT,
            embedding=_vector(1.0, 0.0),
        )
        mock_rewrite_query.return_value = "When is Jhon's Java developer interview?"
        mock_semantic_search.return_value = [note]
        mock_generate_answer.return_value = "The note says it is on Sunday."

        response = self.client.post(
            "/api/chat/",
            {"query": "When is it?", "session_id": session.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        mock_rewrite_query.assert_called_once()
        mock_semantic_search.assert_called_once_with(
            "When is Jhon's Java developer interview?",
            limit=6,
        )
        mock_generate_answer.assert_called_once()
        self.assertEqual(
            ChatMessage.objects.order_by("-id").first().metadata["retrieval_query"],
            "When is Jhon's Java developer interview?",
        )

    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    def test_chat_sources_are_separate_deduplicated_and_limited(
        self,
        mock_semantic_search,
        mock_generate_answer,
    ):
        notes = [
            Note.objects.create(
                raw_input=f"Source note {index}",
                cleaned_note=f"Source note {index}",
                summary=f"Summary {index}",
                input_type=Note.InputType.TEXT,
                embedding=_vector(1.0, 0.0),
            )
            for index in range(4)
        ]
        mock_semantic_search.return_value = [notes[0], notes[1], notes[0], notes[2], notes[3]]
        mock_generate_answer.return_value = "A short answer."

        response = self.client.post(
            "/api/chat/",
            {"query": "Question?"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["answer"], "A short answer.")
        self.assertEqual(
            [source["note_id"] for source in response.data["sources"]],
            [notes[0].id, notes[1].id, notes[2].id],
        )
        self.assertTrue(all("preview" in source for source in response.data["sources"]))

    @patch("notes.views.rewrite_retrieval_query")
    @patch("notes.views.generate_answer")
    @patch("notes.views.semantic_search")
    @patch("notes.management.commands.test_rag_flow.semantic_search")
    @patch("notes.views.generate_embedding")
    @patch("notes.views.process_note")
    def test_test_rag_flow_command_prints_handoff_state(
        self,
        mock_process_note,
        mock_generate_embedding,
        mock_command_search,
        mock_view_search,
        mock_generate_answer,
        mock_rewrite_query,
    ):
        mock_process_note.return_value = {
            "cleaned_note": (
                "Jhon wants to interview for a Java developer position on Sunday."
            ),
            "summary": "Jhon has a Java developer interview on Sunday.",
            "people": ["Jhon"],
            "topics": ["java", "interview"],
            "events": [],
            "follow_up_questions": [],
        }
        mock_generate_embedding.return_value = _vector(1.0, 0.0)
        mock_command_search.side_effect = lambda query, limit: [Note.objects.get()]
        mock_view_search.side_effect = lambda query, limit: [Note.objects.get()]
        mock_rewrite_query.return_value = "When is Jhon's Java developer interview?"
        mock_generate_answer.side_effect = [
            "Jhon is trying for a Java developer role.",
            "The note says it is on Sunday.",
        ]
        out = StringIO()

        call_command("test_rag_flow", stdout=out)

        output = out.getvalue()
        self.assertIn("created note id:", output)
        self.assertIn("raw/content text field: Jhon wants to interview", output)
        self.assertIn("embedding exists: yes", output)
        self.assertIn("semantic search result count: 1", output)
        self.assertIn("exact source text passed into the chat prompt:", output)
        self.assertIn("exact sources returned by the API serializer:", output)
        self.assertIn("first chat response:", output)
        self.assertIn("Java developer role", output)
        self.assertIn("follow-up chat response:", output)
        self.assertIn("Sunday", output)
        self.assertNotIn("test-key", output)


class AIProcessorTests(SimpleTestCase):
    @override_settings(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://ai.example.test/v1/chat/completions",
        AI_MODEL="",
    )
    @patch("notes.services.ai_processor.requests.post")
    def test_process_note_sends_required_prompt(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "cleaned_note": "Met Sara.",
                    "summary": "Met Sara.",
                    "people": ["Sara"],
                    "topics": ["onboarding"],
                    "events": [],
                    "follow_up_questions": [],
                }

        mock_post.return_value = FakeResponse()

        process_note("Met Sara.")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(
            payload["messages"][0]["content"],
            PROMPT_TEMPLATE.format(user_input="Met Sara."),
        )

    @override_settings(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://api.deepseek.com",
        AI_MODEL="deepseek-chat",
    )
    @patch("notes.services.ai_processor.requests.post")
    def test_process_note_appends_chat_completions_to_base_url(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"cleaned_note":"Met Sara.","summary":"Met Sara.",'
                                    '"people":["Sara"],"topics":[],"events":[],'
                                    '"follow_up_questions":[]}'
                                )
                            }
                        }
                    ]
                }

        mock_post.return_value = FakeResponse()

        process_note("Met Sara.")

        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.deepseek.com/chat/completions",
        )


class ChatServiceTests(SimpleTestCase):
    @override_settings(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://api.deepseek.com",
        AI_MODEL="deepseek-chat",
    )
    @patch("notes.services.chat_service.requests.post")
    def test_generate_answer_appends_chat_completions_to_base_url(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": "Rahul is preparing."}},
                    ]
                }

        mock_post.return_value = FakeResponse()

        answer = generate_answer("Who?", ["Rahul is preparing."])

        self.assertEqual(answer, "Rahul is preparing.")
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.deepseek.com/chat/completions",
        )
        prompt = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("Keep the answer short by default", prompt)

    @override_settings(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://api.deepseek.com",
        AI_MODEL="deepseek-chat",
    )
    @patch("notes.services.chat_service.requests.post")
    def test_rewrite_retrieval_query_uses_recent_history(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "When is Jhon's Java developer interview?"
                            }
                        },
                    ]
                }

        mock_post.return_value = FakeResponse()

        rewritten = rewrite_retrieval_query(
            "When is it?",
            [
                {"role": "user", "content": "What role is Jhon trying for?"},
                {
                    "role": "assistant",
                    "content": "Jhon is trying for a Java developer role.",
                },
            ],
        )

        self.assertEqual(rewritten, "When is Jhon's Java developer interview?")
        prompt = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("What role is Jhon trying for?", prompt)
        self.assertIn("When is it?", prompt)


class EmbeddingServiceTests(SimpleTestCase):
    @override_settings(
        EMBEDDING_API_KEY="test-key",
        EMBEDDING_BASE_URL="https://api.example.test/v1/embeddings",
        EMBEDDING_MODEL="text-embedding-3-large",
        EMBEDDING_DIMENSIONS=3,
    )
    @patch("notes.services.embedding_service.requests.post")
    def test_generate_embedding_keeps_openai_compatible_support(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

        mock_post.return_value = FakeResponse()

        embedding = generate_embedding("Met Sara.")

        self.assertEqual(embedding, [0.1, 0.2, 0.3])
        request = mock_post.call_args.kwargs
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.example.test/v1/embeddings",
        )
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(request["json"]["input"], "Met Sara.")
        self.assertEqual(request["json"]["model"], "text-embedding-3-large")

    @override_settings(
        EMBEDDING_API_KEY="test-key",
        EMBEDDING_BASE_URL="https://generativelanguage.googleapis.com/v1beta",
        EMBEDDING_MODEL="gemini-embedding-001",
        EMBEDDING_DIMENSIONS=3,
    )
    @patch("notes.services.embedding_service.requests.post")
    def test_generate_embedding_parses_gemini_response(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"embedding": {"values": [0.1, "0.2", 0.3]}}

        mock_post.return_value = FakeResponse()

        embedding = generate_embedding("Met Sara.")

        self.assertEqual(embedding, [0.1, 0.2, 0.3])
        request = mock_post.call_args.kwargs
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-embedding-001:embedContent",
        )
        self.assertEqual(request["headers"]["x-goog-api-key"], "test-key")
        self.assertNotIn("Authorization", request["headers"])
        self.assertEqual(request["json"]["model"], "models/gemini-embedding-001")
        self.assertEqual(request["json"]["output_dimensionality"], 3)
        self.assertNotIn("test-key", str(request["json"]))

    @override_settings(
        EMBEDDING_API_KEY="test-key",
        EMBEDDING_BASE_URL="https://embeddings.example.test/v1beta",
        EMBEDDING_MODEL="gemini-embedding-001",
        EMBEDDING_DIMENSIONS=3,
    )
    @patch("notes.services.embedding_service.requests.post")
    def test_generate_embedding_detects_gemini_model_name(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"embeddings": [{"values": [1, 2, 3]}]}

        mock_post.return_value = FakeResponse()

        embedding = generate_embedding("Met Sara.")

        self.assertEqual(embedding, [1.0, 2.0, 3.0])
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://embeddings.example.test/v1beta/models/"
            "gemini-embedding-001:embedContent",
        )


def _vector(first: float, second: float) -> list[float]:
    values = [0.0] * settings.EMBEDDING_DIMENSIONS
    values[0] = first
    values[1] = second
    return values
