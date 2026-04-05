# CLAUDE.md

## Project Overview

This project is called **Signal Radar**.

Signal Radar is a GTM signal intelligence platform that helps users:
1. identify meaningful signals across accounts or companies
2. prioritize opportunities
3. take action for outbound, prospecting, or account based workflows

This is not a toy project.
This is not a UI demo.
This is not a CRUD app.

This should feel like a real B2B intelligence product.

---

## Core Product Intent

Signal Radar enables users to:
1. view accounts or companies
2. inspect signals tied to those accounts
3. understand which accounts matter right now
4. filter and rank opportunities
5. track accounts via watchlists
6. receive actionable recommendations

Every feature must support **decision making and action**.

---

## Engineering Philosophy

### 1. Actionable Systems > Pretty Code
The system must work reliably under real usage conditions.
Avoid optimizing for aesthetics over correctness.

### 2. Simplicity Wins
Choose the simplest design that:
- works correctly
- can scale reasonably
- is easy to debug

### 3. Build Only What Exists
All backend work must be driven by the frontend.
Do not invent product features.

### 4. Explicit Over Implicit
Assumptions must be stated clearly.
Hidden behavior is a bug waiting to happen.

### 5. No Fake AI
Do not fabricate ML systems.
Use clear, explainable, rules based logic.

---

## Architecture Principles

### System Design Expectations

All design decisions must:
1. define clear data flow
2. define clear ownership of logic
3. avoid tight coupling
4. support observability and debugging

### Required Layers

Use a clean but pragmatic structure:

- config
- db
- models
- schemas
- routes
- services

Only introduce additional layers if they reduce complexity.

---

## Domain Modeling Expectations

Before building anything:

1. Identify real entities from the frontend
2. Define relationships explicitly
3. Validate that each entity is necessary

Likely entities (only if needed):

- User
- Account
- Contact
- Signal
- SignalType
- SignalSource
- SignalEvent
- SignalScore
- Watchlist
- SavedFilter
- ActionRecommendation

---

## Data Integrity Rules

Every table must:
1. have clear primary keys
2. use foreign keys where relationships exist
3. include created_at and updated_at where relevant
4. enforce constraints to prevent bad data

Indexes must exist for:
- account lookup
- signal filtering
- recency queries
- sorting by score

---

## API Design Standards

All APIs must:
1. map directly to frontend needs
2. support pagination where needed
3. support filtering and sorting
4. return consistent response structures
5. use proper HTTP status codes
6. handle error states explicitly

Avoid:
- ambiguous responses
- inconsistent naming
- hidden side effects

---

## Signal Scoring Philosophy

Signal Radar must prioritize data.

Use a simple scoring system based on:
- recency
- signal type
- source credibility
- frequency
- user priority

Scoring must:
1. be deterministic
2. be explainable
3. be easy to modify
4. be surfaced in API responses

---

## World Class Troubleshooting Standards

You are expected to debug like a senior engineer.

### Always Identify Root Cause

Never patch symptoms.

For every issue:
1. identify where the failure occurs
2. identify why it occurs
3. confirm with evidence
4. implement a fix at the correct layer

### Debugging Process

For any bug:

1. reproduce the issue
2. trace the full request flow:
   frontend → API → service → database
3. inspect inputs and outputs at each step
4. validate assumptions
5. isolate the failing component
6. implement minimal fix
7. verify end to end behavior

### Logging Expectations

Add logging where useful:
- request entry points
- key decision points
- error cases

Avoid excessive logging noise.

---

## Failure Mode Thinking

Before finalizing any feature, evaluate:

1. what happens with empty data
2. what happens with malformed input
3. what happens with missing relationships
4. what happens with large datasets
5. what happens under slow queries

Design for graceful failure.

---

## Performance and Scalability (MVP Level)

You are not building for millions of users yet.

But you must:
1. avoid obvious N+1 query patterns
2. use indexes for common queries
3. paginate large lists
4. avoid loading unnecessary data

---

## Frontend Integration Rules

1. Remove mock data once backend is ready
2. Centralize API calls
3. Use environment based URLs
4. Add loading, error, and empty states
5. Preserve UX unless required to change

---

## Testing Standards

Tests must cover:
1. critical endpoints
2. validation failures
3. filtering and sorting logic
4. scoring logic
5. watchlist behavior

Avoid fake or shallow tests.

---

## Deployment Readiness

The system must include:

1. Dockerfile
2. docker compose for local dev
3. environment variable management
4. migration support
5. seed data
6. health endpoint

---

## Non Goals

Do NOT:
1. add unnecessary microservices
2. introduce queues or streaming systems
3. build complex ML systems
4. over abstract
5. build unused features

---

## Required Workflow

Always follow this order:

1. audit frontend
2. identify mock data and gaps
3. define entities and relationships
4. define API contract
5. implement backend
6. wire frontend
7. add tests
8. add migrations and seed data
9. prepare deployment
10. perform gap analysis

Do not skip steps.

---

## Definition of Done

The system is done when:

1. frontend uses real backend data
2. accounts and signals load correctly
3. filtering and sorting work
4. scoring is implemented and visible
5. watchlists work if present
6. app runs locally with clear instructions
7. key flows are tested
8. deployment is possible
9. known gaps are documented

---

## Instructions for Claude Code

You are not a code generator.

You are:
- a senior backend engineer
- a system architect
- a debugging specialist

Before coding:
1. inspect the repo
2. understand the product
3. define the system

While coding:
1. write clean, minimal, correct code
2. validate assumptions
3. avoid overengineering

After coding:
1. test critical paths
2. identify weaknesses
3. document gaps honestly

Every response must include:
1. what changed
2. why it changed
3. what works
4. what might break
5. next highest leverage step

Be precise.
Be critical.
Avoid false confidence.

## Failure Scenario Checklist

### Happy Path
Feature works end to end.

### Empty State
No data does not break UI.

### Bad Input
Invalid inputs handled cleanly.

### Missing Relationships
System does not crash on missing links.

### Filtering and Sorting
All combinations behave correctly.

### Scoring
Outputs are logical and stable.

### State Transitions
Create update delete flows are correct.

### Frontend Resilience
Handles loading errors and failures.

### Backend Resilience
Errors handled without crashing.

### Database Integrity
Constraints and relationships hold.

### Performance
No obvious slow paths.

### Observability
Logs and health checks work.

### Deployment
App starts cleanly with correct config.

### Regression
Existing features still work.

---

## Post Feature Review Protocol

After any feature:

1. what changed
2. why it changed
3. what works
4. what might break
5. what was tested
6. known weaknesses
7. next highest leverage step

Do not claim completion without this review.