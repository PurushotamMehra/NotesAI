"""WSGI config for the Second Brain AI backend."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "second_brain_backend.settings")

application = get_wsgi_application()
