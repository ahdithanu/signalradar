# Frontend Audit — Signal Radar

**Date:** 2026-03-19
**Audited by:** Claude Code (senior backend engineer role per CLAUDE.md)
**Status:** COMPLETE — Real frontend exists. Fully mocked. Zero API calls.

---

## 1. Tech Stack

| Layer | Choice |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Routing | react-router-dom v6 |
| State/Data | @tanstack/react-query (installed, **not used**) |
| Styling | Tailwind CSS 3 + shadcn/ui components |
| Charts | Recharts |
| Export | jspdf + jspdf-autotable (PDF), manual CSV |
| Package manager | bun (bun.lock present) + npm (package-lock.json present) |

---

## 2. Pages

| Route | File | Description |
|---|---|---|
| `/` | `src/pages/Index.tsx` | Main dashboard — signal feed ticker, top 3 opportunities, full company table with filters |
| `/analytics` | `src/pages/Analytics.tsx` | Charts — signals over time, pipeline funnel, industry performance, summary stats |
| `/settings` | `src/pages/Settings.tsx` | User preferences — time period, notifications, display toggles. Persisted to localStorage |
| `*` | `src/pages/NotFound.tsx` | 404 page |

---

## 3. Application Components

| Component | File | Purpose |
|---|---|---|
| AppHeader | `src/components/AppHeader.tsx` | Top nav with logo, nav links (Dashboard, Analytics, Settings), dark mode toggle |
| DashboardTable | `src/components/DashboardTable.tsx` | Main company table with search, sort by score, filters (industry, signal type, funding stage, employees, min score, date range), row selection, CSV/PDF export, status change |
| CompanyDrawer | `src/components/CompanyDrawer.tsx` | Right-side drawer for company detail — overview, score, signal breakdown with score contributions, why now, outreach strategy, buyer personas, notes, strategic intelligence |
| SignalFeed | `src/components/SignalFeed.tsx` | Horizontal auto-scrolling ticker of recent signals |
| TopOpportunities | `src/components/TopOpportunities.tsx` | Top 3 companies by opportunityScore as cards |
| ScoreBadge | `src/components/ScoreBadge.tsx` | Color-coded score display (green >=80, blue >=60, gray <60) |
| ProbabilityMeter | `src/components/ProbabilityMeter.tsx` | Progress bar + percentage for opportunity probability |
| SignalBadge | `src/components/SignalBadge.tsx` | Icon + label badge for signal type (funding, hiring, growth, product_launch) |
| StatusSelect | `src/components/StatusSelect.tsx` | Dropdown to change company status (New, Reviewing, Ready for Outreach, Dismissed) |
| NavLink | `src/components/NavLink.tsx` | Wrapper around react-router NavLink with active class support |

**UI library components (shadcn/ui):** 40+ files in `src/components/ui/`. Standard shadcn/ui installation. Most are unused by application code — only `calendar`, `popover`, `button`, `textarea`, `switch`, `label`, `tooltip`, `toast/toaster/sonner` are actively referenced.

---

## 4. Hooks

| Hook | File | Purpose |
|---|---|---|
| use-mobile | `src/hooks/use-mobile.tsx` | Returns boolean for viewport < 768px. **Not used by any component.** |
| use-toast | `src/hooks/use-toast.ts` | Toast notification hook. Used by DashboardTable, CompanyDrawer, Settings. |

---

## 5. Data Layer

### Mock Data File: `src/data/mockData.ts`

This is the **only data source** for the entire frontend. There are zero API calls anywhere.

**Types defined:**

```typescript
type SignalType = "funding" | "hiring" | "growth" | "product_launch"
type Status = "New" | "Reviewing" | "Ready for Outreach" | "Dismissed"

interface Signal {
  type: SignalType
  description: string
  date: string          // ISO date string
  daysAgo: number       // precomputed
  scoreContribution: number
  interpretation: string
}

interface StrategicIntelligence {
  strategicTheme: string
  managementTone: string
  commercialPressureScore: "low" | "medium" | "high"
  narrativeShift: string
  suggestedGTMRelevance: string
}

interface Company {
  id: string
  name: string
  website: string       // not "domain" — different naming
  industry: string
  employeeCount: number
  fundingStage: string
  opportunityScore: number
  opportunityProbability: number  // 0.0–1.0
  signals: Signal[]               // embedded, not referenced by FK
  whyNow: string
  recommendedBuyerPersona: string[]
  suggestedOutreachAngle: string
  status: Status
  strategicIntelligence: StrategicIntelligence
}
```

**Mock companies:** 8 companies (Nova Payments, Ramp AI, Vector Labs, Cobalt Health, Prism Analytics, Meridian Logistics, Athena Security, Flux Commerce)

**Derived data:** `signalFeedItems` — flattened signal list sorted by `daysAgo`, used by the ticker.

### What imports mockData:

| File | What it imports |
|---|---|
| `pages/Index.tsx` | `companies`, `Status` |
| `pages/Analytics.tsx` | `companies` |
| `components/DashboardTable.tsx` | `companies`, `Company`, `SignalType`, `Status` |
| `components/CompanyDrawer.tsx` | `companies`, `Status` |
| `components/SignalFeed.tsx` | `signalFeedItems` |
| `components/TopOpportunities.tsx` | `companies`, `Company` |
| `components/SignalBadge.tsx` | `SignalType` |
| `components/StatusSelect.tsx` | `Status` |

**Every component reads from the hardcoded array. No component makes any API call.**

---

## 6. API Calls and Fetch Usage

**None.** Zero instances of `fetch()`, `axios`, or any HTTP client in application code.

React Query (`@tanstack/react-query`) is installed and the `QueryClientProvider` wraps the app, but no `useQuery` or `useMutation` calls exist anywhere.

---

## 7. Environment Variables

**None.** Zero references to `import.meta.env` or `VITE_*` in application code.

The Vite dev server runs on port 8080 (hardcoded in `vite.config.ts`).

---

## 8. State Management

All state is local React state (`useState`) or derived via `useMemo`. No global store. No context providers beyond React Query (unused) and TooltipProvider.

Status changes are managed as `Record<string, Status>` in `Index.tsx` and passed down as props. Not persisted to backend or localStorage (lost on refresh).

Settings/preferences are persisted to `localStorage` under key `user_preferences`.

Notes in CompanyDrawer are stored in component-local `useState` — lost on close.

---

## 9. Frontend Features That Require Backend Support

| Feature | Current Implementation | Backend Requirement |
|---|---|---|
| Company list | Hardcoded array | GET /accounts (or /companies) with pagination, filter, sort |
| Company detail | `companies.find(c => c.id === id)` | GET /accounts/{id} with embedded signals and score |
| Signal feed | Derived from companies array | GET /signals (global feed, sorted by recency) |
| Signal breakdown per company | `company.signals` embedded array | GET /accounts/{id}/signals |
| Opportunity score | `company.opportunityScore` hardcoded number | Computed score from signal_scores table |
| Opportunity probability | `company.opportunityProbability` hardcoded | **Not in backend architecture — new field or derived** |
| Score contribution per signal | `signal.scoreContribution` hardcoded | Computable from scoring formula but not currently in API |
| Status management | Local state, not persisted | Need a status field on accounts or a separate tracking entity |
| Filtering by industry | Client-side filter on hardcoded array | GET /accounts?industry=X |
| Filtering by signal type | Client-side | GET /accounts?signal_type=X or GET /signals?signal_type_id=X |
| Filtering by funding stage | Client-side | **fundingStage not in backend Account model** |
| Filtering by employee range | Client-side | GET /accounts with employee_count range params |
| Filtering by min score | Client-side | GET /accounts?min_score=X |
| Filtering by date range | Client-side on signal dates | GET /signals?since=X or date range params |
| Sort by score | Client-side | GET /accounts?sort_by=score |
| Search by name | Client-side `.includes()` | GET /accounts?search=X |
| Analytics charts | Derived from companies array | Aggregation endpoints or client-side from list data |
| CSV/PDF export | Client-side from in-memory data | No backend needed if data is already loaded |
| Company notes | Component-local state, lost on close | **Not in backend architecture** |
| Strategic intelligence | Hardcoded per company | **Not in backend architecture** |
| Why Now summary | Hardcoded per company | **Not in backend architecture** |
| Buyer personas | Hardcoded per company | **Not in backend architecture** |
| Outreach angle | Hardcoded per company | **Not in backend architecture** |
| Dark mode | localStorage toggle | No backend needed |
| User preferences | localStorage | No backend needed for MVP |

---

## 10. Frontend Entity Shape vs Backend Entity Shape

### Company (frontend) vs Account (backend)

| Frontend Field | Backend Column | Match? |
|---|---|---|
| `id` (string) | `id` (UUID) | Compatible — UUID serializes to string |
| `name` | `name` | Match |
| `website` | `domain` | **Name mismatch** — frontend says `website`, backend says `domain` |
| `industry` | `industry` | Match |
| `employeeCount` | `employee_count` | **Case mismatch** — camelCase vs snake_case |
| `fundingStage` | — | **Missing from backend** |
| `opportunityScore` | signal_scores.score | Different location — backend stores in separate table |
| `opportunityProbability` | — | **Missing from backend entirely** |
| `signals` | — | Embedded in frontend; separate table + endpoint in backend |
| `whyNow` | — | **Missing from backend** |
| `recommendedBuyerPersona` | — | **Missing from backend** |
| `suggestedOutreachAngle` | — | **Missing from backend** |
| `status` | — | **Missing from backend** |
| `strategicIntelligence` | — | **Missing from backend** |
| — | `location` | Backend has it, frontend doesn't display it prominently |
| — | `description` | Backend has it, frontend doesn't use it |

### Signal (frontend) vs Signal (backend)

| Frontend Field | Backend Column | Match? |
|---|---|---|
| `type` (string literal) | `signal_type_id` (UUID FK) | **Structure mismatch** — frontend uses inline string, backend uses FK to lookup table |
| `description` | `title` | **Name mismatch** |
| `date` | `occurred_at` | **Name mismatch** + format difference |
| `daysAgo` | — | **Derived field** — not stored, must be computed client-side |
| `scoreContribution` | — | **Missing from backend** — must be computed from scoring formula |
| `interpretation` | `summary` | **Name mismatch** |
| — | `signal_source_id` | Backend has it, frontend doesn't reference it |
| — | `raw_url` | Backend has it, frontend doesn't display it |

### Signal Types

| Frontend | Backend seed |
|---|---|
| `funding` | `funding` |
| `hiring` | `hiring` |
| `growth` | **Missing from backend** — not in signal_types seed |
| `product_launch` | `product_launch` |
| — | `leadership_change` (backend only) |
| — | `news_mention` (backend only) |
| — | `partnership` (backend only) |

---

## 11. Conclusion

The frontend is a complete, functional UI built entirely on hardcoded mock data. It has:
- 4 pages
- 10 application components
- 1 mock data file serving as the entire data layer
- Zero API calls
- Zero environment variables
- Rich filtering, sorting, export, and detail drawer UX

The frontend entity shape (`Company`) diverges significantly from the backend entity shape (`Account`). Major gaps include: `fundingStage`, `opportunityProbability`, `status`, `whyNow`, `recommendedBuyerPersona`, `suggestedOutreachAngle`, and `strategicIntelligence` — none of which exist in the backend.

Integration will require either extending the backend schema or deciding which frontend features are MVP and which are deferred.
