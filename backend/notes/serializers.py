from rest_framework import serializers

from .models import Note


class NoteSerializer(serializers.Serializer):
    raw_input = serializers.CharField(allow_blank=False)
    input_type = serializers.ChoiceField(choices=Note.InputType.choices)


class NoteUpdateSerializer(serializers.Serializer):
    raw_input = serializers.CharField(allow_blank=False, required=False)
    input_type = serializers.ChoiceField(choices=Note.InputType.choices, required=False)


class SearchSerializer(serializers.Serializer):
    query = serializers.CharField(allow_blank=False)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)


class ChatSerializer(serializers.Serializer):
    query = serializers.CharField(allow_blank=False)
    session_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
