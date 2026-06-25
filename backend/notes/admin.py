from django.contrib import admin

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

admin.site.register(Note)
admin.site.register(Person)
admin.site.register(Topic)
admin.site.register(NoteEntity)
admin.site.register(FollowUpQuestion)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(AICallLog)
