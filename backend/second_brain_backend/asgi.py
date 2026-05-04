"""ASGI config for the Second Brain AI backend."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "second_brain_backend.settings")

application = get_asgi_application()
