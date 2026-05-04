from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Note",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_input", models.TextField()),
                ("cleaned_note", models.TextField(blank=True)),
                ("summary", models.TextField(blank=True)),
                (
                    "input_type",
                    models.CharField(
                        choices=[
                            ("text", "Text"),
                            ("voice", "Voice"),
                            ("image", "Image"),
                            ("link", "Link"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Topic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="NoteEntity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entity_type",
                    models.CharField(choices=[("person", "Person"), ("topic", "Topic")], max_length=20),
                ),
                ("entity_id", models.PositiveBigIntegerField()),
                (
                    "note",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entities",
                        to="notes.note",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="noteentity",
            index=models.Index(fields=["entity_type", "entity_id"], name="notes_notee_entity__990bdd_idx"),
        ),
    ]
