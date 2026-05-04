from django.db import models


class Note(models.Model):
    class InputType(models.TextChoices):
        TEXT = "text", "Text"
        VOICE = "voice", "Voice"
        IMAGE = "image", "Image"
        LINK = "link", "Link"

    raw_input = models.TextField()
    cleaned_note = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    input_type = models.CharField(max_length=20, choices=InputType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.get_input_type_display()} note #{self.pk}"


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
