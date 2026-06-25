from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0002_followupquestion"),
    ]

    operations = [
        VectorExtension(),
    ]
