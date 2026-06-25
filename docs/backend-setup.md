# Backend Setup

This guide sets up the Django backend with PostgreSQL and pgvector for local development.

## Prerequisites

- Python 3.11 or newer
- PostgreSQL 16 with pgvector, or Docker Compose
- From the repository root, run backend commands in `backend/`

## Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`backend/.env` is ignored by git. Keep local secrets and machine-specific settings there.

The default `.env.example` values target the Docker Compose database:

```dotenv
POSTGRES_DB=second_brain
POSTGRES_USER=second_brain
POSTGRES_PASSWORD=second_brain
POSTGRES_HOST=localhost
POSTGRES_PORT=55432
```

AI keys can stay blank for local setup. The current note ingestion path falls back to storing raw notes when AI or embedding providers are not configured. The example embedding settings target Gemini `gemini-embedding-001` with 3072 dimensions.

## Option A: PostgreSQL With Docker Compose

From the repository root:

```bash
docker compose up -d postgres
```

If your machine has Docker Compose v1, use `docker-compose` instead:

```bash
docker-compose up -d postgres
```

The Compose service uses `pgvector/pgvector:pg16`, creates the `second_brain` database, and exposes PostgreSQL on `localhost:55432`.

Check readiness:

```bash
docker compose ps
docker compose exec postgres pg_isready -U second_brain -d second_brain
```

With Docker Compose v1:

```bash
docker-compose ps
docker-compose exec postgres pg_isready -U second_brain -d second_brain
```

Enable pgvector manually if you need to prepare the database before Django migrations:

```bash
docker compose exec postgres psql -U second_brain -d second_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

With Docker Compose v1:

```bash
docker-compose exec postgres psql -U second_brain -d second_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The Django migration `notes.0003_enable_pgvector` also enables the extension.

## Option B: Local PostgreSQL

Create the role and database:

```bash
createuser --createdb second_brain
createdb --owner=second_brain second_brain
```

Set a password if your local PostgreSQL requires password authentication:

```bash
psql postgres -c "ALTER USER second_brain WITH PASSWORD 'second_brain';"
```

Enable pgvector:

```bash
psql -d second_brain -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If your host, port, database, user, or password differ, update `backend/.env`.

For local PostgreSQL on the default port, use:

```dotenv
POSTGRES_PORT=5432
```

## Migrate And Run

From `backend/` with the virtual environment active:

```bash
python manage.py migrate
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`.

## Checks And Tests

Run Django system checks:

```bash
python manage.py check
```

Run backend tests:

```bash
python manage.py test
```

Tests require a reachable PostgreSQL database with pgvector available. Django creates a temporary test database using the configured PostgreSQL role, so that role must have permission to create databases. The Docker Compose role has that permission by default.

## Reset Local Database

For the Docker Compose database:

```bash
docker compose down -v
docker compose up -d postgres
cd backend
python manage.py migrate
```
