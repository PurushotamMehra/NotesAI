# Second Brain AI

Second Brain AI is a mobile-first personal AI memory system for capturing notes, structuring them with AI, extracting people and topics, and eventually chatting with stored memories through RAG.

## Stack

- Frontend: Flutter
- Backend: Django and Django REST Framework
- Database: PostgreSQL
- Vector search: pgvector
- AI: External LLM and embeddings APIs

## Folder Structure

```text
second-brain/
  mobile/        Flutter app
  backend/       Django project and API
  docs/          Documentation
  AGENTS.md      Agent operating instructions
  README.md      Project overview
  .gitignore     Ignore rules
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The backend expects PostgreSQL. Configure database values in `backend/.env`.

For a local pgvector database with Docker:

```bash
docker run --name second-brain-postgres-dev \
  -e POSTGRES_DB=second_brain \
  -e POSTGRES_USER=second_brain \
  -e POSTGRES_PASSWORD=second_brain \
  -p 55432:5432 \
  -d pgvector/pgvector:pg16
```

## Mobile Setup

```bash
cd mobile
flutter pub get
flutter run
```

The Flutter app is intentionally minimal and currently contains placeholder screens for note input, notes list, and chat.
