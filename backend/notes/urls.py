from django.urls import path

from .views import ChatView, NoteCreateView, NoteDetailView, NoteReprocessView, SearchView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="rag-chat"),
    path("notes/", NoteCreateView.as_view(), name="note-create"),
    path("notes/<int:note_id>/", NoteDetailView.as_view(), name="note-detail"),
    path(
        "notes/<int:note_id>/reprocess/",
        NoteReprocessView.as_view(),
        name="note-reprocess",
    ),
    path("search/", SearchView.as_view(), name="semantic-search"),
]
