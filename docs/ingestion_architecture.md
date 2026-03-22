# Ingestion Pipeline Architecture — Signal Radar

**Date:** 2026-03-20
**Author:** Claude Code (senior backend engineer role per CLAUDE.md)
**Status:** PROPOSED — awaiting approval before implementation

---

## 1. Problem Statement

Signal Radar currently runs on seed data. Every signal is hardcoded. There is no mechanism to discover, collect, or process real signals from external sources.

This document defines the MVP ingestion pipeline for 4 signal types across 50 accounts. The goal is to produce real signals that flow through the existing scoring engine and dashboard endpoint without modifying either.

---

## 2. Signal Types in Scope

| Signal Type | What It Detects | Primary Sources |
|---|---|---|
| `funding` | New rounds, disclosed amounts, investors | Crunchbase API, SEC EDGAR (Form D), financial news RSS |
| `hiring` | Job postings indicating GTM buildout | Company careers pages, LinkedIn Jobs (via proxied scrape or API) |
| `positioning_shift` | ICP change, messaging pivot, market repositioning | Company website diffs (homepage, pricing, about), press releases |
| `leadership_change` | New C-suite or VP-level hires announced | Press releases, LinkedIn profile changes, SEC 8-K |

---

## 3. Data Model: Three Layers

### Layer 1: Account Sources (`account_sources`)

Maps an account to its discoverable external identifiers. One account can have many sources.

```
account_sources
├── id              UUID PK
├── account_id      UUID FK → accounts.id, NOT NULL, ON DELETE CASCADE
├── source_type     VARCHAR(50) NOT NULL
│                   enum: "website", "linkedin_company", "crunchbase", "sec_edgar", "careers_page"
├── source_url      TEXT NOT NULL
├── source_key      VARCHAR(255) NULL
│                   (e.g., crunchbase slug "nova-payments", LinkedIn company ID "12345678")
├── is_active       BOOLEAN NOT NULL DEFAULT true
├── last_checked_at TIMESTAMPTZ NULL
├── last_error      TEXT NULL
├── created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
├── updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()

Index: (account_id, source_type) UNIQUE
Index: (source_type, is_active) — for batch job queries
```

**What gets persisted here:** The external identity of an account. Where to look for signals.

**What does NOT go here:** Signal data, scores, or anything derived.

### Layer 2: Raw Events (`raw_events`)

The unprocessed output from an external source. Immutable after insert. Never updated, never deleted (except by retention policy). This is the audit trail.

```
raw_events
├── id              UUID PK
├── account_source_id UUID FK → account_sources.id, NOT NULL
├── account_id      UUID FK → accounts.id, NOT NULL, ON DELETE CASCADE
│                   (denormalized for query speed — always matches account_source.account_id)
├── event_type      VARCHAR(50) NOT NULL
│                   enum: "funding_round", "job_posting", "website_change", "press_release",
│                         "sec_filing", "linkedin_update"
├── raw_payload     JSONB NOT NULL
│                   (the full API response, scraped HTML fragment, or structured extract)
├── source_url      TEXT NULL
│                   (the specific URL this event came from)
├── external_id     VARCHAR(255) NULL
│                   (dedup key — e.g., Crunchbase funding round UUID, job posting ID)
├── occurred_at     TIMESTAMPTZ NULL
│                   (when the event happened in the real world, if extractable)
├── fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
│                   (when we collected it)
├── is_processed    BOOLEAN NOT NULL DEFAULT false
├── created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

Index: (account_id, event_type, fetched_at DESC)
Index: (external_id) WHERE external_id IS NOT NULL — dedup
Index: (is_processed, event_type) — batch normalization queries
```

**What gets persisted here:** Exactly what the source returned. No interpretation. No scoring.

**What does NOT go here:** Signal type classification, scores, summaries, or any product-layer logic.

### Layer 3: Signals (`signals` — existing table)

The canonical product layer. Already exists. Already consumed by the scoring engine and dashboard endpoint.

```
signals (existing — no changes)
├── id              UUID PK
├── account_id      UUID FK → accounts.id
├── type            VARCHAR(50) NOT NULL  — "funding", "hiring", "positioning_shift", "leadership_change"
├── title           VARCHAR(255) NOT NULL
├── summary         TEXT NULL
├── occurred_at     TIMESTAMPTZ NOT NULL
├── created_at      TIMESTAMPTZ NOT NULL

New column needed:
├── raw_event_id    UUID FK → raw_events.id, NULL
│                   (NULL for seed data, populated for ingested signals)
│                   (enables traceability: signal → raw event → source)
```

**What gets persisted here:** The normalized, classified, product-ready signal.

**What does NOT go here:** Scores, score contributions, daysAgo, or any display-layer fields. Those are derived at query time by the scoring engine.

---

## 4. What Is Persisted vs Derived vs API-Shaped

| Data | Where | Persistence |
|---|---|---|
| Account identity | `accounts` | Persisted |
| External source URLs | `account_sources` | Persisted |
| Raw API/scrape output | `raw_events.raw_payload` | Persisted (immutable) |
| Signal type classification | `signals.type` | Persisted (after normalization) |
| Signal title and summary | `signals.title`, `signals.summary` | Persisted (after normalization) |
| Signal occurred_at | `signals.occurred_at` | Persisted |
| Traceability link | `signals.raw_event_id` | Persisted |
| Opportunity score | — | **Derived** at query time by `scoring.py` |
| Score contribution per signal | — | **Derived** at query time by `scoring.py` |
| daysAgo | — | **Derived** at query time |
| opportunityProbability | — | **Derived** at query time |
| whyNow enhancement | — | **Derived** at query time by `enhance_why_now()` |
| camelCase field names | — | **API-shaped** only in dashboard response schemas |
| signalFeedItems | — | **API-shaped** — frontend derives from companies array |

---

## 5. End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BATCH JOB (cron)                             │
│                                                                     │
│  1. SOURCE DISCOVERY                                                │
│     Read account_sources WHERE is_active = true                     │
│     Group by source_type                                            │
│                                                                     │
│  2. EXTRACTION                                                      │
│     For each source:                                                │
│       - Call external API or scrape URL                             │
│       - Check external_id for dedup                                 │
│       - Insert into raw_events (is_processed = false)               │
│       - Update account_sources.last_checked_at                      │
│                                                                     │
│  3. RAW STORAGE                                                     │
│     raw_events now contains new unprocessed rows                    │
│                                                                     │
│  4. NORMALIZATION                                                   │
│     Read raw_events WHERE is_processed = false                      │
│     For each raw event:                                             │
│       - Classify → signal type                                      │
│       - Extract title, summary, occurred_at                         │
│       - Check for duplicate signal (same account + type + title     │
│         within 7-day window)                                        │
│       - Insert into signals with raw_event_id                       │
│       - Set raw_events.is_processed = true                          │
│                                                                     │
│  5. SCORING (already exists — no changes)                           │
│     Dashboard endpoint calls compute_account_score()                │
│     on each request with the account's signals                      │
│                                                                     │
│  6. DASHBOARD SERVING (already exists — no changes)                 │
│     GET /accounts/dashboard returns scored, shaped data             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key principle:** Steps 1–4 are batch. Steps 5–6 are request-time. No coupling between them except the `signals` table.

---

## 6. Extraction Strategy Per Signal Type

### 6a. Funding

| Source | Method | Cost | Reliability |
|---|---|---|---|
| Crunchbase Basic API | REST, free tier (200 req/month) | Free | High for funded companies |
| SEC EDGAR FULL-TEXT | HTTPS fetch of Form D filings | Free | High for US companies |
| Financial news RSS | RSS parse (TechCrunch, etc.) | Free | Medium — noisy |

**MVP recommendation:** Start with Crunchbase Basic API. It returns structured funding round data with amounts, dates, and investors. Fall back to SEC EDGAR Form D for coverage gaps.

**Extraction output (raw_payload):**
```json
{
  "round_type": "Series A",
  "money_raised_usd": 18000000,
  "announced_on": "2026-01-28",
  "lead_investors": ["Sequoia Capital"],
  "source": "crunchbase"
}
```

**Normalization rule:**
- signal type: `"funding"`
- title: `"Raised ${amount} ${round_type}"`
- summary: `"Led by ${investors}. Entering scaling phase."`
- occurred_at: `announced_on`

### 6b. Hiring

| Source | Method | Cost | Reliability |
|---|---|---|---|
| Company careers page | HTTP scrape + parse | Free | Medium — HTML varies |
| LinkedIn Jobs (unofficial) | Proxied scrape | Free but fragile | Medium |
| Job board aggregators | APIs (Adzuna, Arbeitnow) | Free tiers | Medium |

**MVP recommendation:** Scrape company careers pages. For each account, store the careers page URL in `account_sources`. Parse for job titles containing GTM keywords: `Sales`, `Account Executive`, `SDR`, `BDR`, `Revenue`, `Growth`, `Head of Sales`, `VP Sales`.

**Extraction output (raw_payload):**
```json
{
  "job_title": "Head of Growth",
  "department": "Marketing",
  "location": "Remote",
  "posted_date": "2026-02-25",
  "url": "https://rampai.com/careers/head-of-growth",
  "source": "careers_page"
}
```

**Normalization rule:**
- signal type: `"hiring"`
- title: `"Hiring ${job_title}"`
- summary: Rules-based interpretation from job title keywords
- occurred_at: `posted_date` or `fetched_at` if no date found

### 6c. Positioning Shift

| Source | Method | Cost | Reliability |
|---|---|---|---|
| Company website diff | HTTP fetch + text diff against last snapshot | Free | High — direct evidence |
| Press releases | RSS or news API | Free | Medium |
| Product/pricing page changes | HTTP fetch + diff | Free | High |

**MVP recommendation:** Periodic snapshot of each account's homepage, pricing page, and about page. Store text content in `raw_payload`. Compare against previous snapshot. Flag changes above a diff threshold.

**Extraction output (raw_payload):**
```json
{
  "page_url": "https://rampai.com",
  "page_type": "homepage",
  "previous_snapshot_id": "uuid-of-previous",
  "diff_summary": "Added 'enterprise' section. Removed 'self-serve' pricing tier.",
  "diff_percentage": 0.23,
  "current_text_hash": "sha256:abc123",
  "source": "website_diff"
}
```

**Normalization rule:**
- signal type: `"positioning_shift"`
- title: Derived from diff content (rules-based keyword extraction)
- summary: `"${page_type} changed significantly: ${diff_summary}"`
- occurred_at: `fetched_at` (website changes don't have inherent dates)
- **Threshold:** Only normalize if `diff_percentage > 0.10` AND keywords match (`enterprise`, `pricing`, `ICP`, `target`, `market`, `platform`)

### 6d. Leadership Change

| Source | Method | Cost | Reliability |
|---|---|---|---|
| Press releases | News API or RSS | Free | High for major hires |
| LinkedIn profile changes | Scrape (fragile) | Free | Medium |
| SEC 8-K filings | EDGAR HTTPS | Free | High for public companies |

**MVP recommendation:** Use a free news API (e.g., NewsAPI.org, 100 req/day free) to search for `"[company name]" AND ("appointed" OR "hired" OR "named" OR "joins as" OR "new CEO" OR "new CTO" OR "new VP")`. Parse results for executive title keywords.

**Extraction output (raw_payload):**
```json
{
  "headline": "Cobalt Health Names Jane Doe as VP of Sales",
  "published_at": "2026-03-01",
  "source_name": "BusinessWire",
  "url": "https://businesswire.com/...",
  "matched_keywords": ["VP of Sales", "named"],
  "source": "news_api"
}
```

**Normalization rule:**
- signal type: `"leadership_change"`
- title: `"${person_name} joined as ${title}"` or headline if parsing fails
- summary: `"New ${seniority_level} hire signals ${interpretation}"`
- occurred_at: `published_at`

---

## 7. Backend Folder Structure

```
Backend/app/
├── config.py
├── db.py
├── main.py
├── models/
│   ├── __init__.py
│   ├── account.py          (existing)
│   ├── signal.py           (existing — add raw_event_id column)
│   ├── account_source.py   (new)
│   └── raw_event.py        (new)
├── schemas/
│   ├── __init__.py
│   ├── account.py          (existing)
│   └── dashboard.py        (existing)
├── routes/
│   ├── __init__.py
│   ├── health.py           (existing)
│   └── accounts.py         (existing — no changes)
├── services/
│   ├── __init__.py
│   ├── scoring.py          (existing — no changes)
│   └── seed.py             (existing — no changes)
├── ingestion/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py         (BaseExtractor protocol/ABC)
│   │   ├── crunchbase.py   (funding extraction)
│   │   ├── careers.py      (hiring — careers page scraping)
│   │   ├── website_diff.py (positioning_shift — page snapshot + diff)
│   │   └── news.py         (leadership_change — news API search)
│   ├── normalizers/
│   │   ├── __init__.py
│   │   ├── base.py         (BaseNormalizer protocol/ABC)
│   │   ├── funding.py      (raw funding event → signal)
│   │   ├── hiring.py       (raw job posting → signal)
│   │   ├── positioning.py  (raw website diff → signal)
│   │   └── leadership.py   (raw news article → signal)
│   └── runner.py           (orchestrates extract → store → normalize cycle)
└── jobs/
    ├── __init__.py
    └── ingest.py           (CLI entry point for cron: python -m app.jobs.ingest)
```

**Design decisions:**

1. `ingestion/extractors/` — one file per source type. Each implements a common interface: `extract(account_source) → list[raw_event_data]`.
2. `ingestion/normalizers/` — one file per signal type. Each implements: `normalize(raw_event) → Signal | None`. Returns `None` if the event doesn't qualify.
3. `ingestion/runner.py` — the orchestration layer. Reads active sources, calls extractors, stores raw events, calls normalizers. Has no business logic itself.
4. `jobs/ingest.py` — the cron entry point. Calls `runner.run()` with config (which signal types, how many accounts, dry-run mode).

**What is NOT in this structure:**
- No queue system
- No async workers
- No scheduler daemon
- No API endpoints for ingestion (batch only)

---

## 8. MVP Batch Job Strategy

### Schedule

| Job | Frequency | Accounts Per Run | Time Budget |
|---|---|---|---|
| Funding extraction | Daily at 06:00 UTC | All 50 | ~2 min (API calls) |
| Hiring extraction | Daily at 07:00 UTC | All 50 | ~5 min (page scrapes) |
| Website diff | Every 3 days at 08:00 UTC | All 50 | ~5 min (page fetches) |
| News search (leadership) | Daily at 09:00 UTC | All 50 | ~2 min (API calls) |
| Normalization | Daily at 10:00 UTC | All unprocessed | ~1 min |

### Execution

```bash
# Cron entries (or systemd timers, or Render cron jobs)
0 6 * * *  cd /app && python -m app.jobs.ingest --type funding
0 7 * * *  cd /app && python -m app.jobs.ingest --type hiring
0 8 */3 * *  cd /app && python -m app.jobs.ingest --type positioning
0 9 * * *  cd /app && python -m app.jobs.ingest --type leadership
0 10 * * *  cd /app && python -m app.jobs.ingest --normalize-only
```

### CLI Interface

```
python -m app.jobs.ingest
  --type [funding|hiring|positioning|leadership|all]
  --normalize-only          # skip extraction, only normalize pending raw events
  --dry-run                 # log what would be created, don't write to DB
  --account-id UUID         # run for a single account
  --limit N                 # process first N accounts only
```

### Error Handling

- Each account source is processed independently. One failure does not block others.
- On extractor failure: log error, set `account_sources.last_error`, skip to next source.
- On normalizer failure: log error, leave `raw_events.is_processed = false`, skip to next event.
- Retry policy: failed sources are retried on next scheduled run. No exponential backoff needed at this scale.

---

## 9. Account Source Bootstrap

For 50 accounts, we need initial `account_sources` rows. Two approaches:

### Option A: Manual seed (recommended for MVP)

Extend `seed.py` to insert `account_sources` for each account. For each account, auto-derive:
- `website` → homepage URL → source_type `"website"`, also derive `"careers_page"` URL pattern
- `domain` → Crunchbase slug guess → source_type `"crunchbase"`
- `name` → news search query → source_type `"news_api"`

### Option B: Discovery endpoint (future)

`POST /accounts/{id}/discover-sources` — fetches known URLs and creates `account_sources` automatically.

**MVP: Use Option A.** 50 accounts with manually curated source URLs is manageable and produces higher quality results than automated discovery.

---

## 10. Deduplication Strategy

Signals must not be duplicated when the same event is fetched on multiple runs.

| Layer | Dedup Mechanism |
|---|---|
| Raw events | `external_id` unique index. If Crunchbase returns the same funding round UUID, skip insert. |
| Raw events (no external ID) | Content hash of `raw_payload` + `account_id` + `event_type`. Store as `external_id`. |
| Signals | Before inserting a normalized signal, check for existing signal with same `account_id` + `type` + matching title substring within a 7-day `occurred_at` window. |

---

## 11. Top Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Crunchbase free tier rate limit (200/month) insufficient for 50 daily accounts | High | Medium | Batch by checking `last_checked_at` — only re-check accounts not checked in last 7 days. 50 accounts / 7 = ~8 calls/day = ~240/month. Tight but workable. |
| 2 | Careers page HTML varies wildly across companies | High | Medium | Use simple heuristic parsing (search for job-title-like patterns). Accept lower recall initially. Flag unparseable pages for manual review. |
| 3 | Website diff produces false positive positioning_shift signals | High | Medium | Require keyword match + diff threshold. Start conservative (high threshold). Tune after observing false positive rate. |
| 4 | News API free tier (100 req/day) insufficient | Medium | Low | Batch queries: search for multiple company names in one query where API supports it. 50 accounts = 50 queries/day, well within limit. |
| 5 | Normalization produces low-quality titles/summaries | Medium | Medium | Start with rigid template-based titles. No LLM. Review first 50 normalized signals manually before going live. |
| 6 | Leadership changes detected from news are actually old re-posts | Medium | Low | Require `published_at` within last 90 days. Cross-reference with existing signals for same person/title. |
| 7 | External API downtime blocks entire batch run | Low | Medium | Each source processed independently. Partial runs are fine. `last_error` column enables monitoring. |

---

## 12. First Implementation Sequence

Ordered by dependency and value. Each step produces a concrete, testable artifact.

| Step | Deliverable | Depends On | Estimated Effort |
|---|---|---|---|
| 1 | `AccountSource` and `RawEvent` models + migration | Nothing | 1 hour |
| 2 | Add `raw_event_id` nullable FK to `Signal` model | Step 1 | 15 min |
| 3 | `BaseExtractor` protocol + `CrunchbaseExtractor` | Step 1 | 2 hours |
| 4 | `BaseNormalizer` protocol + `FundingNormalizer` | Step 2 | 1 hour |
| 5 | `runner.py` — orchestration for extract + normalize | Steps 3, 4 | 1.5 hours |
| 6 | `jobs/ingest.py` — CLI entry point | Step 5 | 30 min |
| 7 | Seed 50 accounts with `account_sources` | Step 1 | 1 hour |
| 8 | Run funding pipeline end-to-end for 50 accounts | Steps 6, 7 | Test + debug |
| 9 | `CareersExtractor` + `HiringNormalizer` | Step 5 | 2 hours |
| 10 | `WebsiteDiffExtractor` + `PositioningNormalizer` | Step 5 | 2 hours |
| 11 | `NewsExtractor` + `LeadershipNormalizer` | Step 5 | 1.5 hours |
| 12 | Full 4-type pipeline test with 50 accounts | Steps 8–11 | Test + debug |

**Total estimated effort:** ~13 hours of implementation + testing.

**Critical path:** Steps 1 → 3 → 5 → 6 → 8. Once funding works end-to-end, the remaining extractors/normalizers are parallelizable.

---

## 13. What This Does NOT Include

1. **No real-time ingestion.** Batch only.
2. **No LLM-based normalization.** Rules and templates only.
3. **No webhook receivers.** Pull-based extraction only.
4. **No user-facing ingestion controls.** No API endpoints for triggering or configuring ingestion.
5. **No Alembic migrations yet.** Will use `create_all` for now (documented deviation).
6. **No monitoring dashboard.** Use logs + `last_error` column for observability.
7. **No account discovery.** 50 accounts are manually seeded with known sources.

---

## 14. ARR Potential Levers

This architecture directly supports revenue-driving features:

| Feature | How Ingestion Enables It |
|---|---|
| "Fresh signals" badge on dashboard | `signals.created_at` from ingestion vs seed shows real recency |
| Signal source attribution | `raw_event_id → account_source → source_type` enables "Source: Crunchbase" display |
| Audit trail for compliance | `raw_events.raw_payload` proves signal provenance |
| Custom source configuration | `account_sources` per account enables per-customer source setup |
| Signal coverage scoring | Count of active sources per account = coverage metric for upsell |
| Historical trend analysis | `raw_events` accumulation over time enables "signals over time" charts |
| Competitive intelligence | Website diff detection = positioning shift = differentiated product feature |

---

## 15. Decision: Smallest First Implementation

**Recommendation:** Implement funding pipeline end-to-end (Steps 1–8) as the first deliverable.

**Why funding first:**
1. Crunchbase API returns structured data — lowest normalization complexity
2. Funding signals have the highest scoring weight (30.0) — biggest product impact
3. One API call per account — simplest extraction logic
4. Funding data has natural `external_id` (round UUID) — cleanest dedup
5. Produces immediately visible change on the dashboard — proves the pipeline works

**Success criteria for Step 8:**
- 50 accounts have `account_sources` rows with Crunchbase identifiers
- `python -m app.jobs.ingest --type funding` runs without error
- New `raw_events` rows appear with funding round payloads
- New `signals` rows appear with type=`"funding"`, linked via `raw_event_id`
- `GET /accounts/dashboard` returns updated scores reflecting ingested signals
- Seed signals and ingested signals coexist without conflict
