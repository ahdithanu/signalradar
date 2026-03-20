# Frontend Audit — Signal Radar

**Date:** 2026-03-19
**Audited by:** Claude Code (senior backend engineer role per CLAUDE.md)
**Status:** COMPLETE — No frontend exists. Architecture is assumption-driven.

---

## 1. Repo Structure Summary

```
SignalRadar/
├── Backend/                        (empty directory — zero files)
├── CLAUDE.md                       (engineering spec and philosophy)
└── docs/
    ├── backend_architecture.md     (prompt template — not a real artifact)
    ├── backend_builder.md          (prompt template — not a real artifact)
    ├── backend_changelog.md        (governance template — real structure, no entries)
    ├── frontend_audit.md           (this file)
    ├── integration_gaps.md         (prompt template — not a real artifact)
    └── qa_report.md                (prompt template — not a real artifact)
```

**Total source files:** 0
**Total real documentation artifacts:** 2 (CLAUDE.md, backend_changelog.md governance template)
**Total prompt templates (not real artifacts):** 4 (backend_architecture.md, backend_builder.md, integration_gaps.md, qa_report.md)

---

## 2. Frontend Location

**The frontend does not exist.**

Search scope: entire `/Users/ahdithebomb/Documents/` filesystem.

| Check | Result |
|---|---|
| `package.json` files (outside node_modules) | 0 found |
| `.tsx` files | 0 found |
| `.jsx` files | 0 found |
| `.vue` files | 0 found |
| `.svelte` files | 0 found |
| `vite.config.*` | 0 found |
| `next.config.*` | 0 found |
| `tsconfig.json` | 0 found |
| `src/`, `app/`, `pages/`, `components/` dirs | 0 found |
| `index.html` | 0 found |
| `.css`, `.scss` files | 0 found |

`Documents/` contains only: personal files, PDFs, media, and the `SignalRadar/` folder.
`SignalRadar/Backend/` is confirmed empty by direct `find` execution.

---

## 3. Evidence

Direct terminal output from `find /Users/ahdithebomb/Documents/SignalRadar -not -path '*/.git/*' | sort`:

```
/Users/ahdithebomb/Documents/SignalRadar
/Users/ahdithebomb/Documents/SignalRadar/.git
/Users/ahdithebomb/Documents/SignalRadar/Backend
/Users/ahdithebomb/Documents/SignalRadar/CLAUDE.md
/Users/ahdithebomb/Documents/SignalRadar/docs
/Users/ahdithebomb/Documents/SignalRadar/docs/backend_architecture.md
/Users/ahdithebomb/Documents/SignalRadar/docs/backend_builder.md
/Users/ahdithebomb/Documents/SignalRadar/docs/backend_changelog.md
/Users/ahdithebomb/Documents/SignalRadar/docs/frontend_audit.md
/Users/ahdithebomb/Documents/SignalRadar/docs/integration_gaps.md
/Users/ahdithebomb/Documents/SignalRadar/docs/qa_report.md
```

No `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`, `.html`, `.css` files exist anywhere in the repo.

---

## 4. Pages and Components Found

None. No frontend code exists.

**Expected pages based on CLAUDE.md product intent:**

| Page | Inferred From |
|---|---|
| Accounts List | "view accounts or companies", "filter and rank opportunities" |
| Account Detail | "inspect signals tied to those accounts" |
| Signal Feed | "identify meaningful signals across accounts" |
| Watchlist | "track accounts via watchlists" |
| Recommendations | "receive actionable recommendations" |

These are inferences from the product spec. They are **not confirmed by any frontend code.**

---

## 5. Mock Data, Placeholder Handlers, Fake API Usage

None. No frontend code exists to contain any of these.

---

## 6. Entities Implied by the Frontend

No entities can be confirmed from a frontend. All entity definitions below are **assumption-driven**, derived solely from CLAUDE.md.

| Entity | Source | MVP? |
|---|---|---|
| Account | CLAUDE.md entity list + core product intent | Yes |
| Signal | CLAUDE.md entity list + core product intent | Yes |
| SignalType | CLAUDE.md entity list | Yes |
| SignalSource | CLAUDE.md entity list | Yes |
| SignalEvent | CLAUDE.md entity list | Yes |
| SignalScore | CLAUDE.md scoring section | Yes |
| Watchlist | CLAUDE.md entity list + "track accounts" intent | Yes |
| WatchlistItem | Implied by Watchlist → Account relationship | Yes |
| Contact | CLAUDE.md entity list | No — no product behavior defined |
| SavedFilter | CLAUDE.md entity list | No — no frontend UI to derive from |
| ActionRecommendation | CLAUDE.md entity list + "actionable recommendations" | Partial — stub only |
| User | CLAUDE.md entity list | No — auth method undefined, deferred |

---

## 7. Backend Capabilities Required by the Frontend

No frontend exists to drive this. The following are inferred from CLAUDE.md:

| Capability | Priority |
|---|---|
| List accounts with pagination, filter, sort by score | High |
| Account detail with embedded signal score | High |
| List signals per account | High |
| Global signal feed with filters | High |
| Watchlist CRUD | High |
| Add / remove account from watchlist | High |
| Health check endpoint | High |
| Seed data for local development | High |
| Signal scoring (recency + type + source + frequency) | High |
| Recommendations list | Low — no frontend to validate shape |
| User auth | None — deferred |

---

## 8. Ambiguities and Blockers

| # | Issue | Impact | Resolution |
|---|---|---|---|
| 1 | No frontend to validate against | Every entity, endpoint, and schema is an assumption | Accept risk, document clearly, adjust when frontend is built |
| 2 | Signal ingestion method unknown | Cannot build ingest routes without knowing source (manual, CSV, webhook, scraper) | Use seed data for MVP; no ingest endpoint yet |
| 3 | Score weights undefined | CLAUDE.md names factors but gives no weights | Use explicit additive constants in code; document them; make them easy to change |
| 4 | Watchlist ownership model | Per-user vs global — affects schema | Default to global for MVP; user_id column added later when auth is implemented |
| 5 | Auth method undefined | Affects User entity, session management, API protection | Defer entirely; all endpoints unauthenticated for MVP |
| 6 | Contact entity has no product behavior | No UI or workflow defined for contacts | Exclude from MVP entirely |
| 7 | SavedFilter shape unknown | No filter UI to derive from | Exclude from MVP |
| 8 | ActionRecommendation generation logic | CLAUDE.md says "receive actionable recommendations" but defines no rules | Stub the table and endpoint; populate via seed data; no generation logic yet |
| 9 | Pagination defaults | Unknown what page sizes the frontend will expect | Default to limit=50, offset=0; easy to change |

---

## 9. Conclusion

The backend must be built assumption-driven against the CLAUDE.md spec.
The architecture document must clearly mark all assumptions.
When a frontend is introduced, every assumption must be validated against it and deviations logged in `docs/backend_changelog.md`.
