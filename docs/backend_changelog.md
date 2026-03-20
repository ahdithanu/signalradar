# Backend Change Log

## Purpose

This document tracks any change made during backend implementation that deviates from the approved plan in `docs/backend_architecture.md`.

The goal is control, not documentation theater.

This file exists so architecture does not silently drift during implementation.

If the backend implementation changes:
1. entity design
2. schema design
3. API contracts
4. scoring logic
5. key data relationships
6. implementation assumptions

then the change must be logged here before or at the moment it is introduced.

## Rules

1. Do not log routine implementation work that follows the architecture exactly
2. Do log any meaningful deviation from the architecture plan
3. Every entry must explain what changed, why it changed, impact, risk, and follow up
4. Be specific
5. Do not hide behind vague wording
6. Do not claim alignment if the plan changed

## Entry Template

### Change: [Short title]

**Date:** [YYYY MM DD]

**Area:** [Schema / API / Scoring / Data Model / Service Logic / Other]

**What changed:**  
[Describe the exact change]

**Original plan:**  
[Describe what `docs/backend_architecture.md` originally specified]

**Reason for change:**  
[Explain the implementation blocker, frontend evidence, or simplification reason]

**Impact:**  
[Explain how this affects backend behavior, frontend integration, database design, or future development]

**Risk:**  
[Explain downside, tradeoff, or future constraint introduced]

**Follow up:**  
[State what should be revisited later, if anything]

**Status:**  
[Accepted / Needs Review / Temporary]

---

## Change Entries

### Change: Initial log creation

**Date:** [YYYY MM DD]

**Area:** Governance

**What changed:**  
Created `docs/backend_change_log.md` to record architectural deviations during backend implementation.

**Original plan:**  
The orchestration plan required backend changes to be documented if implementation diverged from `docs/backend_architecture.md`.

**Reason for change:**  
A formal file was needed so architecture drift can be tracked explicitly during parallel agent execution.

**Impact:**  
Future backend deviations can now be reviewed with context instead of being buried inside code changes.

**Risk:**  
None, as long as the file is updated consistently.

**Follow up:**  
Use this file only for material deviations, not routine implementation work.

**Status:**
Accepted

---

### Change: Dropped generic response envelope classes from schemas

**Date:** 2026-03-19

**Area:** Schema / API

**What changed:**
`docs/backend_architecture.md` specified `ListResponse[T]` and `DetailResponse[T]` as typed Pydantic envelope classes. The implementation instead returns plain dicts with the same `{ data, total, limit, offset }` shape for list responses and `{ data }` for detail responses.

**Original plan:**
Generic Pydantic models `ListResponse(BaseModel, Generic[T])` and `DetailResponse(BaseModel, Generic[T])` as reusable response wrappers in `app/schemas/account.py`.

**Reason for change:**
Generic Pydantic v2 classes require careful handling of `model_dump()` serialization of UUID and datetime fields embedded inside generic containers. The plain dict approach produces identical JSON output with less complexity and zero risk of serialization edge cases at this stage.

**Impact:**
Response shape is identical. FastAPI auto-docs will show `object` instead of a typed schema for these routes. This is acceptable for MVP — typed response models can be added when the frontend contract is validated.

**Risk:**
OpenAPI docs are less precise. No runtime or integration risk.

**Follow up:**
Reintroduce typed response models once the frontend is built and the response shape is validated.

**Status:**
Accepted

---

### Change: Tables created via SQLAlchemy metadata on startup instead of Alembic

**Date:** 2026-03-19

**Area:** Database / Migrations

**What changed:**
`app/main.py` startup event calls `Base.metadata.create_all(bind=engine)` directly. Alembic is not yet wired in this slice.

**Original plan:**
`docs/backend_architecture.md` specified Alembic as the migration tool with a `001_initial_schema.py` migration file.

**Reason for change:**
Alembic setup is scoped to the next phase. `create_all` is sufficient to make this slice runnable locally without requiring migration commands on first run.

**Impact:**
Local dev works without running `alembic upgrade head`. Production deployments must not use `create_all` — Alembic migrations must be in place before production use.

**Risk:**
Schema drift if `create_all` and Alembic are both used. Risk is zero for now since Alembic has not been initialized yet.

**Follow up:**
Remove `create_all` call from startup once Alembic is wired and tested. Alembic setup is the next implementation phase.

**Status:**
Temporary — accepted for MVP slice 1 only

---

### Change: Bumped dependency versions for Python 3.13 compatibility

**Date:** 2026-03-19

**Area:** Other

**What changed:**
All pinned versions in `requirements.txt` were bumped. Key changes: fastapi 0.111.0 → 0.115.12, pydantic 2.7.1 → 2.11.3, psycopg2-binary 2.9.9 → 2.9.10, sqlalchemy 2.0.30 → 2.0.41, uvicorn 0.29.0 → 0.34.3.

**Original plan:**
`docs/backend_architecture.md` specified Python 3.11+. The original pins were compatible with 3.11/3.12 but not 3.13.

**Reason for change:**
The development environment runs Python 3.13.5. pydantic-core 2.7.x fails to build on 3.13 (PyO3 max supported version 3.12). psycopg2-binary 2.9.9 also fails to build on 3.13.

**Impact:**
All packages are now latest stable. No API changes in FastAPI between 0.111 and 0.115. Pydantic v2 API is stable across 2.7→2.11. No code changes required.

**Risk:**
None. All packages are backward compatible within their major versions.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Migrated startup event to lifespan context manager

**Date:** 2026-03-19

**Area:** Service Logic

**What changed:**
`app/main.py` replaced `@app.on_event("startup")` with an `asynccontextmanager` lifespan function passed to `FastAPI(lifespan=lifespan)`.

**Original plan:**
`docs/backend_architecture.md` did not specify the startup mechanism. The original implementation used `on_event("startup")`.

**Reason for change:**
`on_event` is deprecated in FastAPI 0.111+ and emits a warning. The lifespan pattern is the documented replacement.

**Impact:**
Identical behavior. Startup logic (create_all + seed) runs before the app accepts requests. No shutdown logic needed yet.

**Risk:**
None.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Config env_file resolved from file path instead of CWD

**Date:** 2026-03-19

**Area:** Other

**What changed:**
`app/config.py` now computes `_backend_dir = Path(__file__).resolve().parent.parent` and passes `env_file=_backend_dir / ".env"` to pydantic-settings. Previously used `env_file=".env"` which resolved from CWD.

**Original plan:**
Not specified in architecture doc.

**Reason for change:**
Running `uvicorn` from the repo root (with `--app-dir Backend`) would fail to find `.env` because the relative path resolved from `SignalRadar/` not `SignalRadar/Backend/`.

**Impact:**
`.env` is always loaded from `Backend/.env` regardless of CWD. The app can now be started from any directory.

**Risk:**
None.

**Follow up:**
None.

**Status:**
Accepted