# Backend Architecture — Signal Radar

**Date:** 2026-03-19
**Author:** Claude Code (senior backend engineer role per CLAUDE.md)
**Status:** APPROVED FOR IMPLEMENTATION

---

## 1. Current Reality Assessment

| Item | State |
|---|---|
| Frontend | Does not exist |
| Backend | Does not exist |
| Database | Not configured |
| Architecture driver | CLAUDE.md spec + product intent |
| Risk level | HIGH — all entity shapes are assumptions |

**This architecture is assumption-driven.** Every decision is inferred from CLAUDE.md because no frontend exists to validate against. When a frontend is introduced, all schemas and endpoints must be re-validated and deviations logged in `docs/backend_changelog.md`.

---

## 2. Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Standard for data-adjacent B2B backends; aligns with CLAUDE.md's pragmatism |
| Framework | FastAPI | Async, auto-docs, Pydantic validation built in, production-grade |
| ORM | SQLAlchemy 2.x | Industry standard, clean model definitions, works well with Alembic |
| Migrations | Alembic | Native SQLAlchemy migrations, straightforward |
| Database | PostgreSQL 15+ | CLAUDE.md specifies Postgres-class reliability; indexes, constraints, FK support |
| Validation | Pydantic v2 | Bundled with FastAPI, strict typing, schema generation |
| Server | Uvicorn | ASGI, production-ready |
| Containerization | Docker + Docker Compose | Required by CLAUDE.md deployment readiness section |

---

## 3. Core Entities (MVP Scope)

### Included in MVP

| Entity | Table | Purpose |
|---|---|---|
| Account | `accounts` | A company or target organization being tracked |
| Signal | `signals` | An intelligence event tied to an account |
| SignalType | `signal_types` | Lookup — category of signal (funding, hiring, news, etc.) |
| SignalSource | `signal_sources` | Lookup — where the signal originated |
| SignalScore | `signal_scores` | Computed score per account, stored and refreshable |
| Watchlist | `watchlists` | A named list of accounts |
| WatchlistItem | `watchlist_items` | Join table: watchlist ↔ account |
| ActionRecommendation | `action_recommendations` | Stub — seeded only, no generation logic yet |

### Deferred (not in MVP)

| Entity | Reason |
|---|---|
| User | Auth method undefined; all endpoints unauthenticated for MVP |
| Contact | No product behavior defined in spec or frontend |
| SavedFilter | No filter UI to derive the shape from |

---

## 4. Entity Relationships

```
accounts
  ├── signals (one account → many signals)
  ├── signal_scores (one account → one score, recomputed)
  ├── watchlist_items (many-to-many via watchlist_items)
  └── action_recommendations (one account → many recommendations)

signals
  ├── account_id FK → accounts.id
  ├── signal_type_id FK → signal_types.id
  └── signal_source_id FK → signal_sources.id

watchlists
  └── watchlist_items (one watchlist → many items)

watchlist_items
  ├── watchlist_id FK → watchlists.id
  └── account_id FK → accounts.id
```

---

## 5. Database Schema

### `accounts`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| name | VARCHAR(255) | NOT NULL |
| domain | VARCHAR(255) | UNIQUE, nullable |
| industry | VARCHAR(100) | nullable |
| employee_count | INTEGER | nullable |
| location | VARCHAR(255) | nullable |
| description | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

Indexes: `name`, `industry`, `domain`

---

### `signal_types`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(100) | NOT NULL, UNIQUE |
| weight | NUMERIC(4,2) | NOT NULL — scoring multiplier |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

Seed values: `funding` (3.0), `hiring` (2.0), `leadership_change` (2.5), `product_launch` (2.0), `news_mention` (1.0), `partnership` (1.5)

---

### `signal_sources`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(100) | NOT NULL, UNIQUE |
| credibility_score | NUMERIC(4,2) | NOT NULL — 0.0 to 1.0 |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

Seed values: `linkedin` (0.9), `crunchbase` (0.95), `news_api` (0.8), `manual` (0.7), `twitter` (0.6)

---

### `signals`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id, NOT NULL, ON DELETE CASCADE |
| signal_type_id | UUID | FK → signal_types.id, NOT NULL |
| signal_source_id | UUID | FK → signal_sources.id, NOT NULL |
| title | VARCHAR(255) | NOT NULL |
| summary | TEXT | nullable |
| occurred_at | TIMESTAMPTZ | NOT NULL |
| raw_url | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

Indexes: `account_id`, `signal_type_id`, `occurred_at DESC`, composite `(account_id, occurred_at DESC)`

---

### `signal_scores`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id, UNIQUE, NOT NULL, ON DELETE CASCADE |
| score | NUMERIC(8,2) | NOT NULL |
| signal_count | INTEGER | NOT NULL, default 0 |
| last_signal_at | TIMESTAMPTZ | nullable |
| computed_at | TIMESTAMPTZ | NOT NULL, default now() |

Index: `score DESC` (for sorted account list)

---

### `watchlists`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

---

### `watchlist_items`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| watchlist_id | UUID | FK → watchlists.id, NOT NULL, ON DELETE CASCADE |
| account_id | UUID | FK → accounts.id, NOT NULL, ON DELETE CASCADE |
| added_at | TIMESTAMPTZ | NOT NULL, default now() |

Unique constraint: `(watchlist_id, account_id)` — no duplicate account per watchlist

---

### `action_recommendations`

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id, NOT NULL, ON DELETE CASCADE |
| title | VARCHAR(255) | NOT NULL |
| reason | TEXT | nullable |
| priority | VARCHAR(20) | NOT NULL — enum: `high`, `medium`, `low` |
| status | VARCHAR(20) | NOT NULL, default `pending` — enum: `pending`, `dismissed`, `acted` |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

Index: `account_id`, `priority`, `status`

---

## 6. API Contract

All responses follow this envelope:

**List response:**
```json
{
  "data": [...],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

**Detail response:**
```json
{
  "data": { ... }
}
```

**Error response:**
```json
{
  "error": "message",
  "detail": "..."
}
```

---

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check — returns `{"status": "ok"}` |

---

### Accounts

| Method | Path | Description |
|---|---|---|
| GET | `/accounts` | List accounts, paginated, filterable, sortable |
| GET | `/accounts/{id}` | Account detail with embedded score |

**GET /accounts query params:**
- `limit` (int, default 50)
- `offset` (int, default 0)
- `sort_by` (enum: `score`, `name`, `created_at`; default `score`)
- `order` (enum: `asc`, `desc`; default `desc`)
- `industry` (string, optional filter)
- `search` (string, optional — matches name or domain)

**Account list item response shape:**
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "domain": "acme.com",
  "industry": "SaaS",
  "employee_count": 250,
  "location": "New York, NY",
  "score": 87.5,
  "signal_count": 12,
  "last_signal_at": "2026-03-15T10:00:00Z",
  "created_at": "2026-01-01T00:00:00Z"
}
```

**Account detail adds:**
```json
{
  "description": "...",
  "recent_signals": [...],
  "score_breakdown": {
    "score": 87.5,
    "signal_count": 12,
    "last_signal_at": "...",
    "computed_at": "..."
  }
}
```

---

### Signals

| Method | Path | Description |
|---|---|---|
| GET | `/signals` | Global signal feed, paginated, filterable |
| GET | `/signals/{id}` | Signal detail |
| GET | `/accounts/{id}/signals` | Signals for a specific account |

**GET /signals query params:**
- `limit`, `offset`
- `account_id` (UUID, optional)
- `signal_type_id` (UUID, optional)
- `signal_source_id` (UUID, optional)
- `since` (ISO datetime, optional — filters `occurred_at >= since`)
- `sort_by` (enum: `occurred_at`, `created_at`; default `occurred_at`)
- `order` (default `desc`)

---

### Watchlists

| Method | Path | Description |
|---|---|---|
| GET | `/watchlists` | List all watchlists |
| POST | `/watchlists` | Create a watchlist |
| GET | `/watchlists/{id}` | Watchlist detail with accounts |
| POST | `/watchlists/{id}/accounts` | Add account to watchlist |
| DELETE | `/watchlists/{id}/accounts/{account_id}` | Remove account from watchlist |

---

### Recommendations

| Method | Path | Description |
|---|---|---|
| GET | `/recommendations` | List recommendations, filterable by account |

**GET /recommendations query params:**
- `limit`, `offset`
- `account_id` (UUID, optional)
- `priority` (enum: `high`, `medium`, `low`, optional)
- `status` (enum: `pending`, `dismissed`, `acted`, optional; default `pending`)

---

## 7. MVP Scoring Logic

**Design principle:** Deterministic, explainable, additive, easy to modify. No ML. No hidden weights.

**Score formula (per account):**

```
score = SUM over all signals of:
  signal_type.weight
  * signal_source.credibility_score
  * recency_multiplier(signal.occurred_at)
```

**Recency multiplier:**

| Age of signal | Multiplier |
|---|---|
| 0–7 days | 1.0 |
| 8–30 days | 0.7 |
| 31–90 days | 0.4 |
| > 90 days | 0.1 |

**Frequency bonus:** +0.5 per additional signal beyond the first, capped at +5.0

**Score is:**
- Computed on demand when seeding and can be triggered via a service call
- Stored in `signal_scores` table
- Refreshed whenever new signals are added (called by seed and future ingest)
- Returned embedded in account responses
- Never computed inline in the query path — always read from `signal_scores`

**Score is NOT:**
- A percentage or normalized value
- Bounded — it grows with signal volume
- Hidden — the formula is documented here and will be surfaced in API responses

---

## 8. Directory Structure

```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, router registration, CORS
│   ├── config.py            # Settings via pydantic-settings + .env
│   ├── db.py                # SQLAlchemy engine, session factory, Base
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── signal.py        # Signal, SignalType, SignalSource
│   │   ├── signal_score.py
│   │   ├── watchlist.py     # Watchlist, WatchlistItem
│   │   └── recommendation.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── signal.py
│   │   ├── watchlist.py
│   │   └── recommendation.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── accounts.py
│   │   ├── signals.py
│   │   ├── watchlists.py
│   │   └── recommendations.py
│   └── services/
│       ├── __init__.py
│       ├── scoring.py       # Score computation logic
│       └── seed.py          # Seed data loader
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   └── test_accounts.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 9. Implementation Order

| Step | Deliverable | Rationale |
|---|---|---|
| 1 | Config, DB, Base model setup | Everything depends on this |
| 2 | Signal lookup tables (SignalType, SignalSource) | Needed before Signal model |
| 3 | Account model + migration | First domain entity |
| 4 | Signal model + migration | Core intelligence entity |
| 5 | SignalScore model + scoring service | Score must work before it appears in responses |
| 6 | Account routes (list + detail) | First usable API surface |
| 7 | Signal routes (global feed + per-account) | Second API surface |
| 8 | Seed data | Makes local dev usable |
| 9 | Watchlist model + routes | Watchlist CRUD |
| 10 | Recommendation stub + route | Low-value but spec requires it |
| 11 | Health endpoint | Simple but required |
| 12 | Tests (health, accounts, signals) | Cover critical paths |
| 13 | Dockerfile + docker-compose | Deployment readiness |

---

## 10. Risks and Assumptions

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Frontend, when built, requires different account shape | High | Medium | Schema is minimal — easy to extend |
| 2 | Frontend expects different pagination envelope | Medium | Low | Envelope is standard; easy to adjust |
| 3 | Score formula produces unexpectedly large values | Low | Medium | Cap or normalize when frontend visualizes it |
| 4 | Signal volume makes score recomputation slow | Low (MVP) | High (later) | Score is pre-computed and stored; not inline |
| 5 | Watchlist needs user scoping before auth is implemented | Medium | Medium | Adding `user_id` FK is a single migration |
| 6 | Recommendation generation logic needed sooner than expected | Low | Medium | Stub is ready; rules can be added to scoring service |
| 7 | UUID primary keys cause JOIN performance issues | Low | Low | Acceptable at MVP scale |
| 8 | `occurred_at` timezone handling inconsistent across sources | Medium | Medium | Always store in UTC; enforce in schema |

---

## 11. What Is Explicitly Out of Scope for MVP

1. User authentication and authorization
2. Contact entity
3. SavedFilter entity
4. Signal ingestion (no ingest endpoint — seed data only)
5. Real-time or streaming updates
6. Email or webhook notifications
7. ML-based scoring
8. Multi-tenancy
