# NotesAI

An AI-powered personal knowledge management app built with Flutter, Django REST API, PostgreSQL, pgvector, semantic search, and Retrieval-Augmented Generation over saved notes.

## Overview

NotesAI is a mobile-first AI memory app that helps users capture personal notes and turn them into searchable, structured knowledge. It combines a Flutter mobile interface with a Django REST backend, PostgreSQL storage, pgvector-based vector search, and external AI providers for note enrichment, embeddings, semantic retrieval, and chat over saved memories.

The project implements a practical Retrieval-Augmented Generation workflow: user notes are stored, cleaned, summarized, embedded, and later retrieved through semantic search so the AI chat layer can answer questions using the user’s own saved context. Instead of relying only on a model’s general knowledge, NotesAI grounds responses in retrieved note sources, making it closer to a personal second brain or private AI knowledge base.

The goal of the project is to explore how AI can improve personal knowledge management through memory retrieval, vector embeddings, contextual chat, source-backed answers, and structured note understanding while keeping the architecture understandable and developer-friendly.


## Key Features

- Capture text notes from a mobile app and send them to a backend REST API.
- Store original note text, cleaned note text, summaries, processing status, and embedding status.
- Extract people, topics, and follow-up questions from notes through an external chat-completions style AI provider.
- Generate embeddings through Gemini or OpenAI-compatible embedding endpoints.
- Run semantic search against pgvector embeddings in PostgreSQL.
- Ask questions over saved notes with retrieved source snippets and chat session history.
- Continue working locally even without AI keys: note ingestion falls back to storing the raw note when AI processing is unavailable.
- Track AI calls, latency, success/failure, and related note or chat message metadata.

## How It Works

The Flutter app in `mobile/` provides screens for adding memories, viewing notes, searching memories, and chatting with saved notes. It uses the `http` package to call the backend and reads the API base URL from the `API_BASE_URL` Dart define, defaulting to `http://10.0.2.2:8000` for Android emulator development.

The Django backend in `backend/` exposes API routes under `/api/` for notes, search, reprocessing, and chat. Notes are stored in PostgreSQL with structured metadata and a pgvector embedding column. When note processing runs, the backend calls configured external AI services for note cleanup, summaries, entities, follow-up questions, embeddings, retrieval query rewriting, and chat answers.

Semantic search generates an embedding for the query, compares it against stored note embeddings with pgvector distance ordering, and returns the closest matching notes. Chat builds on the same retrieval path, adds recent session history for query rewriting, and returns an answer with source note previews.

## Setup

### Prerequisites

- Python 3.11 or newer
- Flutter with a compatible Dart SDK
- Docker Compose, or a local PostgreSQL 16 database with pgvector
- Android emulator/device or another Flutter target for running the mobile app

### Environment Variables

Create a local backend environment file from the example:

```bash
cd backend
cp .env.example .env
```

`backend/.env` is ignored by Git. The example values target the Docker Compose PostgreSQL service on `localhost:55432`.

Important variables:

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`
- `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`

AI keys may be left blank for basic local development, but semantic search and chat answers require embeddings and AI provider configuration.

### Database With Docker

From the repository root:

```bash
docker compose up -d postgres
```

The Compose service uses `pgvector/pgvector:pg16`, creates the `second_brain` database, and exposes PostgreSQL on `localhost:55432`. The migration `notes.0003_enable_pgvector` enables the `vector` extension.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`.

### Mobile App

```bash
cd mobile
flutter pub get
flutter run
```

For an Android emulator, the default API URL is usually correct. For a physical device, pass a reachable backend URL:

```bash
flutter run --dart-define API_BASE_URL=http://YOUR_LAN_IP:8000
```

The repo also includes a helper script that starts the database, runs Django, applies migrations, and launches Flutter:

```bash
scripts/run_android_dev.sh emulator
scripts/run_android_dev.sh device
```

## Development Commands

Run the backend:

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

Run migrations:

```bash
cd backend
python manage.py migrate
```

Run backend checks and tests:

```bash
cd backend
python manage.py check
python manage.py test notes
```

Run the mobile app:

```bash
cd mobile
flutter run
```

Analyze and test Flutter code:

```bash
cd mobile
flutter analyze
flutter test
```

## Project Structure

```text
NotesAI/
  backend/                 Django project, REST API, models, migrations, AI services
    notes/                 Notes app with API views, serializers, tests, and services
    second_brain_backend/  Django settings and URL configuration
  mobile/                  Flutter mobile app
    lib/screens/           Add, list, search, and chat screens
    lib/services/          API client
    lib/widgets/           Reusable UI components
  docs/                    Additional setup documentation
  scripts/                 Local development helpers
  docker-compose.yml       PostgreSQL + pgvector development database
```

## Current Status

The project currently has a working Django API, PostgreSQL/pgvector schema, AI processing service layer, semantic search endpoint, chat endpoint, Flutter UI screens, and automated tests for the backend and mobile app.

Areas that could be improved next include authentication, richer capture types beyond text, background workers for production-style async processing, stronger mobile state management, deployment configuration, and more complete provider-specific documentation.

## Privacy And Data Handling

This app is designed around personal notes, so local secrets should stay in `backend/.env` and should not be committed. When AI or embedding providers are configured, note content and chat queries may be sent to those external APIs for processing. Review provider policies and avoid storing sensitive personal data unless your environment and provider choices are appropriate for it.

## License

No license file has been added yet.
