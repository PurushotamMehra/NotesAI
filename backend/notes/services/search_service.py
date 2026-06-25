from pgvector.django import L2Distance

from ..models import Note
from .embedding_service import generate_embedding


def semantic_search(query: str, limit: int = 5):
    query_embedding = generate_embedding(query)
    return list(
        Note.objects.filter(embedding__isnull=False)
        .annotate(distance=L2Distance("embedding", query_embedding))
        .order_by("distance", "-created_at")[:limit]
    )
