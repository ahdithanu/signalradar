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

---

### Change: Added 6 columns to accounts table for frontend contract alignment

**Date:** 2026-03-19

**Area:** Data Model / Schema

**What changed:**
Added `funding_stage`, `status`, `why_now`, `suggested_outreach_angle`, `recommended_buyer_persona` (JSON), and `strategic_intelligence` (JSON) to the `accounts` table.

**Original plan:**
Architecture defined Account with 9 columns. New frontend audit revealed 6 additional fields required by the `Company` interface.

**Reason for change:**
Without these fields, the Index page cannot render.

**Impact:**
Account model now has 15 columns. JSON columns use SQLAlchemy `JSON` type. All new columns nullable except `status` (defaults to `"New"`).

**Risk:**
JSON columns not indexable. Acceptable for MVP — display-only fields.

**Follow up:**
Update `docs/backend_architecture.md`.

**Status:**
Accepted

---

### Change: Signals table uses inline type string instead of FK to signal_types

**Date:** 2026-03-19

**Area:** Data Model

**What changed:**
`signals.type` is `VARCHAR(50)` (e.g., `"funding"`) instead of a UUID FK to `signal_types` lookup table.

**Original plan:**
Architecture specified `signal_types` and `signal_sources` lookup tables.

**Reason for change:**
Frontend uses 4 inline string types. Lookup table adds complexity with no current benefit.

**Impact:**
Simpler model. Signal weights defined in `app/services/scoring.py`.

**Risk:**
Migration to lookup table needed if types become user-configurable.

**Follow up:**
Revisit when signal ingestion is implemented.

**Status:**
Accepted

---

### Change: Scoring computed dynamically instead of stored in signal_scores table

**Date:** 2026-03-19

**Area:** Scoring / Service Logic

**What changed:**
Score computed on-the-fly in `app/services/scoring.py`. No `signal_scores` table. Formula: `score = sum(weight * max(0.3, 1 - daysAgo/30))`.

**Original plan:**
Architecture specified pre-computed `signal_scores` table.

**Reason for change:**
8 companies, fewer than 20 signals — dynamic computation is instant. Scores decay automatically as signals age, which is correct.

**Risk:**
Will not scale. Pre-computation needed at volume.

**Follow up:**
Add `signal_scores` table when scale requires it.

**Status:**
Accepted

---

### Change: Added GET /accounts/dashboard endpoint

**Date:** 2026-03-19

**Area:** API

**What changed:**
New endpoint returns all accounts with computed scores, embedded signals, and all frontend-contract fields in camelCase.

**Original plan:**
Architecture specified only `GET /accounts` and `GET /accounts/{id}`.

**Reason for change:**
Frontend Index page needs all data in a single request with the exact `Company` interface shape.

**Impact:**
One new endpoint. No pagination — acceptable for 8 accounts.

**Risk:**
No pagination at scale.

**Follow up:**
Add pagination when needed.

**Status:**
Accepted

---

### Change: RawEvent uses status enum string instead of is_processed boolean

**Date:** 2026-03-20

**Area:** Data Model

**What changed:**
`raw_events.status` is `VARCHAR(20)` with values `pending`, `processed`, `skipped`, `failed`. An additional `status_detail` text column stores the reason. The architecture doc specified `is_processed BOOLEAN`.

**Original plan:**
`docs/ingestion_architecture.md` section 3, Layer 2 specified `is_processed BOOLEAN NOT NULL DEFAULT false`.

**Reason for change:**
A boolean cannot distinguish between "not yet processed", "processed into a signal", "evaluated but didn't qualify", and "normalization errored". The status field makes pipeline debugging observable without querying logs.

**Impact:**
`run_normalization` queries `WHERE status = 'pending'` instead of `WHERE is_processed = false`. No functional difference for the happy path. Adds observability for skipped and failed events.

**Risk:**
None. Strictly more information than a boolean.

**Follow up:**
Update `docs/ingestion_architecture.md` to reflect the status field.

**Status:**
Accepted

---

### Change: Added content_hash column to raw_events for secondary dedup

**Date:** 2026-03-20

**Area:** Data Model

**What changed:**
`raw_events.content_hash` is `VARCHAR(64)` indexed, computed as SHA-256 of `account_id:event_type:canonical_json(payload)`. Used as a fallback dedup mechanism when `external_id` is not available.

**Original plan:**
Architecture doc mentioned content hash stored in `external_id`. Implementing as a separate column avoids overloading `external_id` with two meanings.

**Reason for change:**
`external_id` should contain the source system's identifier (e.g., Crunchbase UUID). Content hash is a different concept — a computed dedup key based on payload content. Mixing them in one column creates ambiguity.

**Impact:**
Two dedup paths: `external_id` for source-native IDs, `content_hash` for payload-based dedup. Both indexed.

**Risk:**
None. Cleaner separation of concerns.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Added raw_event_id nullable FK to signals table

**Date:** 2026-03-20

**Area:** Data Model

**What changed:**
`signals.raw_event_id` is `UUID FK → raw_events.id ON DELETE SET NULL`, nullable, indexed. NULL for seed data, populated for ingested signals.

**Original plan:**
Specified in `docs/ingestion_architecture.md` section 3, Layer 3.

**Reason for change:**
Following the architecture as designed. Enables traceability: signal → raw_event → account_source.

**Impact:**
Existing seed signals have `raw_event_id = NULL`. Dashboard endpoint is unaffected — it does not read this column.

**Risk:**
Database must be dropped and recreated (or ALTER TABLE) since we use `create_all` not Alembic.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Added ingestion package with funding pipeline

**Date:** 2026-03-20

**Area:** Service Logic

**What changed:**
New package `app/ingestion/` with extractors, normalizers, and runner. New package `app/jobs/` with CLI entry point. Implements the funding pipeline only: CrunchbaseExtractor → FundingNormalizer.

**Original plan:**
Matches `docs/ingestion_architecture.md` sections 7 and 12, steps 1–6.

**Reason for change:**
First implementation of the ingestion pipeline per approved architecture.

**Impact:**
No impact on existing endpoints. New tables (`account_sources`, `raw_events`) created on startup via `create_all`. CLI available as `python -m app.jobs.ingest --type funding`.

**Risk:**
Crunchbase API requires `CRUNCHBASE_API_KEY` env var. Without it, extraction logs a warning and returns zero events. Pipeline is safe to run without the key.

**Follow up:**
Seed account_sources for 50 accounts. Test end-to-end with real Crunchbase API key.

**Status:**
Accepted

---

### Change: Added SimulatedCrunchbaseExtractor and --simulate CLI flag

**Date:** 2026-03-20

**Area:** Service Logic

**What changed:**
`app/ingestion/extractors/simulated.py` provides a `SimulatedCrunchbaseExtractor` that returns deterministic funding events for all 8 seed accounts without calling any external API. The CLI accepts `--simulate` to use this extractor instead of the real `CrunchbaseExtractor`.

**Original plan:**
Not in the architecture doc. Architecture assumed real Crunchbase API access.

**Reason for change:**
End-to-end pipeline testing requires data flowing through all layers. Without a Crunchbase API key, the real extractor returns zero events. The simulated extractor unblocks local development and demonstrates the full pipeline flow.

**Impact:**
No impact on production path. `--simulate` is opt-in. Real extractor is default. Simulated data uses the same `ExtractedEvent` format so normalization, dedup, and scoring are exercised identically.

**Risk:**
None. Simulation flag is clearly labeled in logs and CLI help.

**Follow up:**
Remove or keep as a permanent testing fixture.

**Status:**
Accepted

---

### Change: Seeded account_sources for 8 accounts on startup

**Date:** 2026-03-20

**Area:** Data Model / Service Logic

**What changed:**
`app/services/seed.py` now exports `seed_account_sources(db)` which inserts 8 `account_sources` rows (one per account, source_type="crunchbase") with fixed UUIDs and deterministic source_keys derived from company names. `app/main.py` calls this on startup after seeding accounts.

**Original plan:**
Architecture doc section 9 specified Option A (manual seed). This implements that option.

**Reason for change:**
Accounts need `account_sources` rows for the extraction query to return results.

**Impact:**
8 new rows in `account_sources` on startup. Idempotent — checks by primary key before insert.

**Risk:**
None.

**Follow up:**
Expand to 50 accounts when real company list is available.

**Status:**
Accepted

---

### Change: Added SkipEvent exception for normalizer-to-runner communication

**Date:** 2026-03-20

**Area:** Service Logic

**What changed:**
`app/ingestion/normalizers/base.py` now exports `SkipEvent(Exception)`. Normalizers raise `SkipEvent("reason")` when a raw event should not become a signal. The runner catches `SkipEvent` separately from generic `Exception` and writes the message to `raw_events.status_detail` with status `skipped`.

**Original plan:**
Architecture doc did not specify a skip communication mechanism. The original implementation returned `None` with a generic "Did not qualify" message.

**Reason for change:**
Returning `None` from a normalizer cannot communicate *why* an event was skipped. `SkipEvent` gives pipeline operators a clear, per-event reason without requiring a return-type refactor.

**Impact:**
`FundingNormalizer` now raises `SkipEvent` for empty payloads and invalid payload types. Runner distinguishes intentional skips (SkipEvent, logged at INFO) from unexpected failures (Exception, logged at ERROR).

**Risk:**
None.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Added in-batch dedup for raw events and signals

**Date:** 2026-03-20

**Area:** Service Logic

**What changed:**
`run_extraction()` now tracks `seen_external_ids` and `seen_content_hashes` within a single pipeline run. `run_normalization()` now tracks `seen_signals` (account_id, type, title) within a single batch. Both catch duplicates that the DB-level dedup misses because the first item hasn't been committed yet.

**Original plan:**
Architecture doc specified dedup via DB unique constraints on `external_id` and `content_hash`. In-batch dedup was not specified.

**Reason for change:**
Edge-case testing revealed that two events with the same `external_id` in a single extraction batch (e.g., Crunchbase API returning a duplicate) would pass DB dedup (first not yet committed) and crash on `IntegrityError` at commit. Same issue for content-hash dedup and signal-level dedup.

**Impact:**
Pipeline is now safe against any combination of duplicate events within a single run. `IntegrityError` is caught as a safety net at commit time with rollback per-source.

**Risk:**
In-memory sets grow with batch size. For 8 accounts this is negligible. At scale (thousands of events per run), memory usage is still trivial (set of strings).

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Added positioning_shift ingestion pipeline with website source type

**Date:** 2026-03-20

**Area:** Service Logic / Data Model

**What changed:**
New pipeline for `positioning_shift` signals: `SimulatedWebsiteExtractor` (simulated website diff events), `PositioningNormalizer` (converts website_change raw events into positioning_shift signals with skip rules), `source_type="website"` account_sources (8 rows seeded). CLI supports `--type positioning`. No real website diff extractor yet — both `--simulate` and default modes use SimulatedWebsiteExtractor.

**Original plan:**
`docs/ingestion_architecture.md` section 12 specified Step 10: `WebsiteDiffExtractor` + `PositioningNormalizer`. The implementation matches the architecture's intent but uses simulated data since there is no real website snapshot/diff infrastructure.

**Reason for change:**
Second ingestion lane after funding. Positioning_shift has 22.0 weight (3rd highest) and directly affects `enhance_why_now()` output. Produces differentiated GTM intelligence.

**Impact:**
8 new `account_sources` rows (source_type=website). 13 raw_events per run (8 meaningful + 5 noise). 8 positioning_shift signals created. Rankings change: Ramp AI +3 positions to #1, Cobalt Health +3 to #3. `whyNow` enhanced for all 8 accounts.

**Risk:**
No real website extractor — simulated data only. In production, website diff detection would require HTTP fetching, text extraction, diffing, and keyword analysis. The normalizer's skip rules assume `change_significance` and `extracted_keywords` are pre-computed by the extractor.

**Follow up:**
Implement real `WebsiteDiffExtractor` when external HTTP access is available. Consider using a headless browser for JavaScript-rendered pages.

**Status:**
Accepted

---

### Change: Website sources use same source_key convention as crunchbase sources

**Date:** 2026-03-20

**Area:** Data Model

**What changed:**
`account_sources` rows with `source_type="website"` use the same `source_key` values as crunchbase sources (e.g., "nova-payments", "ramp-ai"). The `source_key` serves as the lookup key for the simulated extractor's data map.

**Original plan:**
Architecture doc did not specify source_key conventions for website sources.

**Reason for change:**
Consistent slug-based source_key enables the simulated extractor to map sources to test data identically to how the simulated crunchbase extractor works.

**Impact:**
No unique constraint issues because `(account_id, source_type)` is the unique constraint on `account_sources`, and source_type differs ("website" vs "crunchbase").

**Risk:**
None.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Positioning normalizer uses categorized GTM keyword matching with salesperson outbound test

**Date:** 2026-03-20

**Area:** Service Logic

**What changed:**
`PositioningNormalizer` upgraded from flat keyword matching to a categorized system. Each GTM keyword maps to a shift category (`icp_upmarket`, `gtm_sales_led`, `new_vertical`, `new_market`, `compliance`). The dominant shift type drives differentiated title and interpretation generation. Two matching bugs were found and fixed: (1) longest-match-first sorting prevents "sales team" from stealing matches from "EMEA sales team"; (2) matching direction changed to `gtm_kw in kw_lower` only — no reverse substring. Added explicit "salesperson outbound test" quality gate: compliance-only changes are skipped.

**Original plan:**
N/A — original normalizer used flat keyword matching without category awareness.

**Reason for change:**
Signal.summary maps to DashboardSignal.interpretation on the frontend. Original summaries were descriptive changelogs ("Page content changed from X to Y") — no salesperson would change outreach based on that. New interpretations answer "so what?" with actionable outbound angles.

**Impact:**
All 8 signals now have correctly classified shift types with differentiated titles and interpretations. Each interpretation includes a concrete outbound angle.

**Risk:**
None — simulated data only.

**Follow up:**
None.

**Status:**
Accepted

---

### Change: Multi-tenant architecture with Supabase JWT auth and workspace scoping

**Date:** 2026-03-20

**Area:** Architecture / Data Model / Auth

**What changed:**
1. Added `users`, `workspaces`, `workspace_members` tables
2. Added `workspace_id` FK (NOT NULL, indexed) to accounts, signals, raw_events, account_sources
3. Replaced global `unique=True` on `accounts.domain` with composite `UniqueConstraint("workspace_id", "domain")`
4. Created `app/auth.py` — validates Supabase JWT (HS256, aud=authenticated), upserts User, resolves workspace
5. All routes accept `WorkspaceContext` dependency — every query filters by `workspace_id`
6. `get_account()` changed from `db.get()` to scoped select (prevents cross-workspace leak)
7. `auth_enabled=False` (default) returns dev context without JWT
8. New endpoints: GET/POST /workspaces, GET /signals, GET /signals/{id}, GET /signals/{id}/evidence
9. Evidence endpoint returns full raw_event payload with confidence score
10. Ingestion runner passes workspace_id to RawEvent and Signal
11. Dockerfile + docker-compose.yml added

**Decisions:**
- No Redis/RQ workers (CLAUDE.md: "do not introduce queues or streaming systems")
- No separate microservices (CLAUDE.md: "do not add unnecessary microservices")
- workspace_id denormalized on signals/raw_events for query simplicity
- Confidence score is rules-based (CLAUDE.md: "no fake AI")

**Risk:**
No Alembic migrations — still using create_all. JWT secret must be secured.

**Status:**
Accepted