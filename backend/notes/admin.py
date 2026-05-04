from django.contrib import admin

from .models import Note, NoteEntity, Person, Topic

admin.site.register(Note)
admin.site.register(Person)
admin.site.register(Topic)
admin.site.register(NoteEntity)
