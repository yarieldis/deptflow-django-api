# AGENTS.md - DeptFlow Web API (Django)

This file provides guidance to AI agents when working with the **deptflow-django-api** repository. (It mirrors `CLAUDE.md`.)

## Repository Overview

**Purpose**: Backend services for the **DeptFlow** department workflow application. It manages institutions, departments, the people working in them, and the (versioned) documents those people use, exposed as a multi-tenant REST API.

**Status**: Implemented — the Django backend is complete with behavior parity to the OpenSpec specs.

**Technology Stack**:
- Python 3.12+ / Django (latest stable)
- Django Ninja (API + auto-generated OpenAPI)
- dj-rest-auth + djangorestframework-simplejwt (auth endpoints + JWT)
- Celery + Redis (async email via a custom MAILERS-aware backend, `core.mail`)
- Django ORM — SQLite (dev/test), PostgreSQL (prod)
- Django Storage API (filesystem default; django-storages for S3/Azure later)

## Architecture

One Django project plus four apps, pragmatic models + service layer:

```
config/        → settings, urls, asgi, wsgi, celery
core/          → tenant scoping (TenantMiddleware, TenantQuerySet), base model, storage
institutions/  → Institution, Department
people/        → Role, Person, PersonDepartment
documents/     → Document, DocumentVersion, DocumentType + workflow services
```

### Key design decisions

- **Pragmatic models + service layer**: domain invariants live on models as guarded methods (e.g. `Document.submit()/approve()/reject()/publish()/unpublish()/archive()`); service functions (one per use case) own orchestration, tenant stamping, authorization, and transactions.
- **Person ≠ login**: `Person` is linked to the auth user only through a nullable `user` FK (people without logins are representable).
- **Multi-tenancy**: shared schema; tenant-owned entities carry `institution_id`, enforced with **explicit** `TenantQuerySet.for_tenant()` scoping in the service layer (no global filter manager). Tenant set per request via `X-Institution-Id` header + `TenantMiddleware` + `contextvars`.
- **Department-scoped document access**: derived from active membership in the document's owning department; no per-document ACL tables.
- **Always-versioned documents**: `Document` (metadata + workflow status) + `DocumentVersion` (immutable file facts).
- **Document workflow (document-level)**: `Draft → PendingApproval → Approved → Published` with `Archived` terminal; `Major.Minor` publish-count versioning; role permissions `can_approve_documents` / `can_publish_documents`; self-approval prevention.
- **Backend-agnostic storage**: files referenced by an opaque `storage_key` behind Django's Storage API.
- **Provider-agnostic persistence**: UUIDv7 primary keys, portable unique codes normalized on write; SQLite + Postgres only (no SQL Server).

## Domain Model

| Entity | Purpose |
| --- | --- |
| Institution | Top-level organization (multi-tenant boundary; optional parent hierarchy) |
| Department | Owned by an institution; optional nesting; optional head person |
| Role | Configurable per-institution organizational role, with optional document-approval and document-publish permissions |
| Person | Organizational record, optionally linked to a login account (`user`) |
| PersonDepartment | Membership: person in a department with role, primary flag, and date range |
| Document | Department-owned document metadata with a document-level workflow status (`Draft`/`PendingApproval`/`Approved`/`Published`/`Archived`) and a `Major.Minor` publish version |
| DocumentVersion | Immutable file upload (storage key, name, type, size, change note) with upload provenance |
| DocumentType | Per-institution document categorization |

## Project Structure

```
deptflow-django-api/
├── config/               # Django project (settings, urls, asgi, wsgi, celery)
├── core/                 # shared: tenant scoping, base model, storage
├── institutions/         # Institution and Department
├── people/               # Role, Person, PersonDepartment
├── documents/            # Document, DocumentVersion, DocumentType, workflow services
├── docs/                 # planning docs (django-migration-plan.md)
├── openspec/             # OpenSpec specs and change proposals
└── pyproject.toml        # uv-managed dependencies
```

## Migrations

Django migrations — one set for SQLite + PostgreSQL:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Quick Start

```bash
uv sync                                  # install dependencies
uv run python manage.py migrate          # apply migrations (SQLite dev db)
uv run python manage.py runserver        # run the API
```

The API runs at `http://localhost:8000/api/`; OpenAPI is at `/api/openapi.json` (Swagger UI at `/api/docs`). Run `uv run celery -A config worker -l info` for async email (eager mode is used in dev/test, so no broker is required locally).

## Configuration

Environment variables (see `config/settings.py`):

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` (comma-separated)
- `DATABASE_URL` — SQLite `db.sqlite3` default in dev, PostgreSQL in prod
- `REDIS_URL` — Celery broker (default `redis://localhost:6379/0`)
- `MAIL_DELIVERY` — Celery email delivery mailer: `console` (dev) or `smtp` (prod)
- `DEFAULT_FROM_EMAIL` + `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_TIMEOUT` — SMTP mailer options
- `CELERY_TASK_ALWAYS_EAGER` — sync email in dev/test (default true)

## OpenSpec Workflow

This repository uses [OpenSpec](https://openspec.dev/) (spec-driven schema). Planning artifacts live under `openspec/changes/<change-name>/`:

- `proposal.md` — what & why
- `specs/<capability-path>/spec.md` — behavior contract (WHAT)
- `design.md` — technical approach (HOW)
- `tasks.md` — implementation checklist

The active change is `django-tech-stack` (the Django migration; declares `skip_specs: true` since behavior is unchanged). The prior .NET changes (`deptflow-domain-model`, `business-layer`, `document-approval-workflow`, `document-publish-workflow`) are historical records whose specs remain the behavioral source of truth. Use `openspec status --change "<name>"` and `openspec instructions <artifact-id> --change "<name>" --json` to drive the workflow. Never hand-create a change directory — use `openspec new change "<name>"`.

## Testing

Test with pytest + pytest-django: `uv run pytest`. Covers unit tests (hierarchy cycle detection, membership active/ended logic) and integration tests (tenant isolation, unique-constraint rejections, department-scoped document access, filesystem storage, the document service layer, and the full approval/publish workflow) against SQLite; PostgreSQL is the production database.

## Version Control Guidelines

- **NEVER** commit changes without user approval. Ask systematically for approval before committing.
- Commit messages should be clear and follow convention:
  - ai-tooling: AI agents, automation commands, workflows, or other AI-enabled developer tooling
  - feat: New feature
  - fix: Bug fix
  - docs: Documentation
  - style: Formatting
  - refactor: Code restructuring
  - test: Adding tests
  - chore: Maintenance tasks
- **NEVER** mention AI/Claude authorship in commit messages (no "Generated with Claude Code", "AI-assisted", etc.)

## Important Notes

- The default dev database is a local SQLite file (`db.sqlite3`), which is gitignored; apply migrations to create/update it.
- Multi-tenancy is established per request via the `X-Institution-Id` header; most endpoints additionally require the caller to hold an active membership in the relevant department.
- The behavior contract lives in the OpenSpec specs (technology-agnostic); the Django implementation must match them, not the old .NET code.
