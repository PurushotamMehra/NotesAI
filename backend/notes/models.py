from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class Note(models.Model):
    class InputType(models.TextChoices):
        TEXT = "text", "Text"
        VOICE = "voice", "Voice"
        IMAGE = "image", "Image"
        LINK = "link", "Link"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        FALLBACK = "fallback", "Fallback"

    class EmbeddingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    raw_input = models.TextField()
    cleaned_note = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    input_type = models.CharField(max_length=20, choices=InputType.choices)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING,
    )
    processing_error = models.TextField(blank=True)
    embedding_error = models.TextField(blank=True)
    ai_model = models.CharField(max_length=255, blank=True)
    embedding_model = models.CharField(max_length=255, blank=True)
    prompt_version = models.CharField(max_length=50, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    embedding_started_at = models.DateTimeField(null=True, blank=True)
    embedding_completed_at = models.DateTimeField(null=True, blank=True)
    embedding = VectorField(
        dimensions=settings.EMBEDDING_DIMENSIONS,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.get_input_type_display()} note #{self.pk}"


class AICallLog(models.Model):
    task_type = models.CharField(max_length=50)
    provider_model = models.CharField(max_length=255, blank=True)
    latency_ms = models.PositiveIntegerField()
    success = models.BooleanField()
    error_message = models.TextField(blank=True)
    note = models.ForeignKey(
        Note,
        on_delete=models.SET_NULL,
        related_name="ai_call_logs",
        null=True,
        blank=True,
    )
    chat_message = models.ForeignKey(
        "ChatMessage",
        on_delete=models.SET_NULL,
        related_name="ai_call_logs",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["task_type", "created_at"]),
            models.Index(fields=["success", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_type} {'ok' if self.success else 'failed'}"


class Person(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Topic(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class NoteEntity(models.Model):
    class EntityType(models.TextChoices):
        PERSON = "person", "Person"
        TOPIC = "topic", "Topic"

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="entities")
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.PositiveBigIntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.entity_id} for note #{self.note_id}"


class FollowUpQuestion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"

    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name="follow_up_questions",
    )
    question = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    def __str__(self) -> str:
        return self.question


class ChatSession(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Chat session #{self.pk}"


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.role} message #{self.pk} in session #{self.session_id}"
