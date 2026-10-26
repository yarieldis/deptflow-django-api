# deptflow-django-api

Web API for the department workflow application, built with Django.

## Overview

Backend services for the **DeptFlow** department workflow application. It manages institutions, departments, the people working in them, and the (versioned) documents those people use, exposed as a multi-tenant REST API.

## Project status

**Planning complete — implementation pending.** The migration from the .NET implementation to Django is fully designed and captured in the `django-tech-stack` OpenSpec change; code is not written yet.

- `openspec/changes/django-tech-stack/` — proposal, design, and task checklist for the Django build
- `docs/django-migration-plan.md` — narrative migration plan
- `openspec/changes/<name>/specs/` — the technology-agnostic behavior specs that remain the contract

## Tech stack

- [Django](https://www.djangoproject.com/) (Python 3.12+)
- [Django Ninja](https://django-ninja.dev/) — typed API + auto-generated OpenAPI
- [dj-rest-auth](https://dj-rest-auth.readthedocs.io/) + [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/) — auth endpoints + JWT
- [Django ORM](https://docs.djangoproject.com/en/stable/topics/db/) — SQLite (dev/test) and PostgreSQL (prod)
- [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) + [django-celery-email](https://pypi.org/project/django-celery-email/) — async email
- [Django Storage API](https://docs.djangoproject.com/en/stable/topics/files/) — filesystem storage (django-storages for S3/Azure later)

## Architecture

- **Pragmatic models + service layer**: domain invariants live on models as guarded methods (e.g. `Document.submit()/approve()/reject()/publish()/unpublish()/archive()`); service functions (one per use case) own orchestration, tenant stamping, authorization, and transactions.
- **Multi-tenant**: shared schema with an `institution_id`; enforced with **explicit** `TenantQuerySet.for_tenant()` scoping in the service layer. Tenant established per request via the `X-Institution-Id` header (`TenantMiddleware` + `contextvars`).
- **Documents**: department-scoped access derived from active membership; files referenced by an opaque `storage_key` behind Django's Storage API; document-level approval and publish workflow (`Draft → PendingApproval → Approved → Published`, with `Archived` terminal) and `Major.Minor` publish-count versioning.
- **Person ≠ login**: `Person` links to the auth user only through a nullable `user` FK.
- **Provider-agnostic persistence**: UUIDv7 primary keys, unique codes normalized on write; SQLite + PostgreSQL behind one migration set.

## Domain model

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

## Migrations

Django migrations, one set for both providers:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Prerequisites

- Python 3.12+ (managed via [uv](https://docs.astral.sh/uv/))
- Redis (only required when running the Celery worker; dev/test use eager mode)

## Getting started

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Apply migrations (creates the local SQLite dev database):

   ```bash
   uv run python manage.py migrate
   ```

3. Run the API:

   ```bash
   uv run python manage.py runserver
   ```

   The API is available at `http://localhost:8000/api/`. The OpenAPI document is served at `http://localhost:8000/api/openapi.json` with Swagger UI at `http://localhost:8000/api/docs`.

4. (Optional) Run the Celery worker for async email:

   ```bash
   uv run celery -A config worker -l info
   ```

## Endpoints

### Identity

Served by dj-rest-auth (mapped to the original Identity contract):

- `POST /register`
- `POST /login`
- `POST /refresh`
- `POST /confirmEmail`
- `POST /resendConfirmationEmail`
- `POST /forgotPassword`
- `POST /resetPassword`
- `GET /manage/info`
- `POST /manage/info`
- `POST /manage/2fa`
- `POST /logout`

### Documents

| Method | Route | Auth required | Description |
| --- | --- | --- | --- |
| `POST` | `/documents` | Yes | Create a document with its first file (multipart form) |
| `GET` | `/documents` | Yes | List documents visible to the caller (department-scoped) |
| `GET` | `/documents/{id}` | Yes | Get a document with its versions |
| `POST` | `/documents/{id}/versions` | Yes | Add a new file version while the document is a draft (multipart form) |
| `POST` | `/documents/{id}/submit` | Yes | Submit the document for approval |
| `POST` | `/documents/{id}/approve` | Yes | Approve the pending document (requires an approver role; cannot be the uploader) |
| `POST` | `/documents/{id}/reject` | Yes | Reject the pending document (requires a comment; may require a new upload) |
| `POST` | `/documents/{id}/publish` | Yes | Publish an approved document (requires a publisher role; bumps the document version) |
| `POST` | `/documents/{id}/unpublish` | Yes | Unpublish a published document (requires a publisher role and a reason) |
| `POST` | `/documents/{id}/archive` | Yes | Archive a document that has been published at least once |

### People, roles, and memberships

| Method | Route | Auth required | Description |
| --- | --- | --- | --- |
| `POST` | `/people` | Yes | Create a person |
| `PUT` | `/people/{id}` | Yes | Update a person |
| `GET` | `/people` | Yes | List people in the current tenant |
| `GET` | `/people/{id}/memberships` | Yes | List a person's membership history |
| `POST` | `/memberships` | Yes | Assign a person to a department with a role |
| `GET` | `/roles` | Yes | List roles in the current tenant |

### Institutions and departments

| Method | Route | Auth required | Description |
| --- | --- | --- | --- |
| `POST` | `/institutions` | Yes | Create an institution (tenant) |
| `GET` | `/institutions` | Yes | List the current tenant's institution |
| `POST` | `/departments` | Yes | Create a department |
| `GET` | `/departments` | Yes | List departments in the current tenant |

## Configuration

Environment variables (see `config/settings.py`):

- `SECRET_KEY` — Django secret key
- `DEBUG` — debug mode (default off in prod)
- `ALLOWED_HOSTS` — hosts allowed to access the API
- `DATABASE_URL` — database connection (SQLite default in dev, PostgreSQL in prod)
- `REDIS_URL` — Celery broker URL
- `STORAGE_BACKEND` / storage settings — filesystem default
- `EMAIL_*` — SMTP settings; email is dispatched asynchronously via django-celery-email
- `CELERY_TASK_ALWAYS_EAGER` — run email synchronously in dev/test (default true)

## Testing

```bash
uv run pytest
```

Tests (pytest + pytest-django) cover hierarchy cycle detection, membership active/ended logic, tenant isolation, unique-constraint rejections, department-scoped document access, filesystem storage, the document service layer, and the full approval/publish workflow against SQLite; PostgreSQL is exercised in CI.

## Project structure

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

## Notes

- The default dev database is a local SQLite file (`db.sqlite3`), which is gitignored; apply migrations to create/update it.
- Multi-tenancy is established per request via the `X-Institution-Id` header; most endpoints additionally require the caller to hold an active membership in the relevant department.
- The behavior contract (endpoints, state machine, access rules) is defined by the OpenSpec specs under `openspec/changes/`, which are technology-agnostic and carried over unchanged from the .NET implementation.
