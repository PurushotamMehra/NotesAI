import requests
from django.conf import settings


def generate_embedding(text: str) -> list[float]:
    if not settings.EMBEDDING_API_KEY or not settings.EMBEDDING_BASE_URL:
        raise RuntimeError("EMBEDDING_API_KEY and EMBEDDING_BASE_URL must be configured.")

    if _is_gemini_embedding_provider():
        embedding = _generate_gemini_embedding(text)
    else:
        embedding = _generate_openai_compatible_embedding(text)

    if len(embedding) != settings.EMBEDDING_DIMENSIONS:
        raise ValueError("Embedding dimension does not match EMBEDDING_DIMENSIONS.")
    return embedding


def _is_gemini_embedding_provider() -> bool:
    base_url = settings.EMBEDDING_BASE_URL.lower()
    model = settings.EMBEDDING_MODEL.lower()
    return "generativelanguage.googleapis.com" in base_url or "gemini" in model


def _generate_gemini_embedding(text: str) -> list[float]:
    response = requests.post(
        _gemini_embedding_url(),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.EMBEDDING_API_KEY,
        },
        json={
            "model": f"models/{_gemini_model_name()}",
            "content": {"parts": [{"text": text}]},
            "output_dimensionality": settings.EMBEDDING_DIMENSIONS,
        },
        timeout=30,
    )
    response.raise_for_status()

    return _extract_gemini_embedding(response.json())


def _gemini_embedding_url() -> str:
    base_url = settings.EMBEDDING_BASE_URL.rstrip("/")
    if ":embedContent" in base_url:
        return base_url
    return f"{base_url}/models/{_gemini_model_name()}:embedContent"


def _gemini_model_name() -> str:
    return settings.EMBEDDING_MODEL.removeprefix("models/")


def _generate_openai_compatible_embedding(text: str) -> list[float]:
    payload = {"input": text}
    if settings.EMBEDDING_MODEL:
        payload["model"] = settings.EMBEDDING_MODEL

    response = requests.post(
        settings.EMBEDDING_BASE_URL,
        headers={
            "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    return _extract_openai_compatible_embedding(response.json())


def _extract_openai_compatible_embedding(response_data: dict) -> list[float]:
    embedding = response_data.get("embedding")
    if embedding is None and response_data.get("data"):
        embedding = response_data["data"][0].get("embedding")

    if not isinstance(embedding, list):
        raise ValueError("Embedding response did not contain a vector.")

    return [float(value) for value in embedding]


def _extract_gemini_embedding(response_data: dict) -> list[float]:
    embedding = response_data.get("embedding", {}).get("values")
    if embedding is None and response_data.get("embeddings"):
        embedding = response_data["embeddings"][0].get("values")

    if not isinstance(embedding, list):
        raise ValueError("Gemini embedding response did not contain a vector.")

    return [float(value) for value in embedding]
