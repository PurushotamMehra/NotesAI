@/home/uttam/.codex/RTK.md

# Second Brain AI Agent Instructions

## Project Overview

Second Brain AI is a mobile-first personal AI memory system. Users capture notes through text, voice, images, or links. The backend will structure and enrich those notes, extract people and topics, store searchable memory records, and eventually support chat over stored notes with retrieval-augmented generation.

The product should remain minimal, fast, non-intrusive, private-first, structured, and flexible.

## Coding Standards

- Keep changes minimal and focused on the requested task.
- Prefer incremental changes over large rewrites.
- Do not refactor unrelated code.
- Do not break working features to introduce new structure.
- Match the existing style in the file or module being edited.
- Add dependencies only when they are required by the current task.
- Keep configuration explicit and easy to understand.

## Folder Responsibilities

- `mobile/`: Flutter mobile application. UI, client-side state, API client code, and mobile-specific assets live here.
- `backend/`: Django and Django REST Framework API. Data models, API serializers, views, AI pipeline orchestration, and database access live here.
- `docs/`: Product and engineering documentation. Internal AI-only context files may live here, but ignored files must not be committed.

## Backend Rules

- Keep backend logic inside Django apps.
- Keep API behavior explicit through serializers, views, and URL routes.
- Do not mix frontend concerns into Django code.
- Treat database schema changes as API and data-contract changes.
- Keep model changes small and migration-friendly.
- Prepare for PostgreSQL and pgvector without introducing unused AI or vector logic early.

## Frontend Rules

- Keep Flutter screens and widgets modular.
- Do not add heavy UI frameworks or complex state management until needed.
- Keep API contracts aligned with backend serializers and endpoints.
- Do not duplicate backend business rules in Flutter except for lightweight validation.

## API Contract Awareness

- Backend response shapes are contracts with the mobile app.
- If a serializer, endpoint, field name, or status code changes, update the mobile client and documentation together.
- Prefer additive API changes when possible.
- Avoid silent breaking changes.

## Current Scope Guardrails

- Do not implement AI processing yet.
- Do not implement embeddings yet.
- Do not implement chat/RAG execution yet.
- Do not implement authentication yet.
- Do not add async workers yet.
