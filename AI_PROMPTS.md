# Signal Radar AI Orchestration

This file controls how Claude is used to build Signal Radar.

Be precise.
Be critical.
Avoid false confidence.

---

## Core Rules

- no response wrappers
- no premature abstraction
- log deviations in docs/backend_changelog.md
- do not expand scope beyond the current slice
- backend must be runnable before moving forward

---

## Backend Slice Prompts

### Account Slice (Phase 1)

Proceed to backend implementation.

Read:
- CLAUDE.md
- docs/frontend_audit.md
- docs/backend_architecture.md
- docs/backend_changelog.md

Implement only:

1. FastAPI scaffold
2. config
3. db setup
4. Account model
5. Account schemas
6. health endpoint (/health)
7. GET /accounts
8. GET /accounts/{id}
9. seed data
10. requirements.txt
11. .env.example

Constraints:
- do not implement signals
- do not implement watchlists
- do not implement scoring
- do not add auth
- no response wrappers
- no generic abstractions

Output:
1. full Backend file tree
2. run steps
3. endpoints implemented
4. seed data
5. deviations logged

---

### Signals Slice (Phase 2)

Proceed only after account slice is working.

Implement:

1. Signal model
2. Signal schemas
3. GET /signals
4. GET /accounts/{id}/signals
5. basic filtering (type, source, recency)
6. seed realistic signal data

Constraints:
- no scoring yet
- no watchlists
- no auth
- no abstraction layers

Output:
1. files changed
2. endpoints implemented
3. seed data
4. deviations

---

## Audit Prompts

### Backend Review

Review backend slice.

Focus on:
- model vs schema mismatch
- unnecessary abstraction
- deviation from docs/backend_architecture.md
- API simplicity

Output:
1. issues
2. exact fixes
3. go / no go decision

---

### Frontend Audit

A real frontend exists in Frontend/.

1. inspect all files
2. identify pages, components, hooks
3. find mock data and API placeholders
4. determine required backend endpoints

Update:
- docs/frontend_audit.md
- docs/integration_gaps.md

Do not modify code.

---

## Fix Prompts

### Simplify Endpoint

Remove unnecessary abstraction.

- no response wrappers
- return schema directly
- ensure clean 404 handling

---

### Schema Alignment

Ensure:
- model == schema fields
- seed data matches schema
- no unused fields

---

## Definition of Done (Critical)

A slice is NOT complete until:

1. backend runs locally
2. /health works
3. endpoints return real data
4. seed data is present
5. no schema mismatches
6. no unnecessary abstraction

---

## Operating Loop

1. Build slice
2. Run locally
3. Audit
4. Fix
5. Only then move forward
