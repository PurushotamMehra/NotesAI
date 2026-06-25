import pgvector.django.vector
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0004_note_embedding"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "UPDATE notes_note "
                "SET embedding = NULL "
                "WHERE embedding IS NOT NULL AND vector_dims(embedding) <> 3072"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="note",
            name="embedding",
            field=pgvector.django.vector.VectorField(
                blank=True,
                dimensions=3072,
                null=True,
            ),
        ),
    ]
