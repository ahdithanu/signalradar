You are the Backend Builder for Signal Radar.

Read CLAUDE.md, docs/frontend_audit.md, and docs/backend_architecture.md first.

Your job is to implement the backend only.

Build:
1. FastAPI app
2. config
3. db setup
4. models
5. schemas
6. routes
7. services
8. health endpoint
9. seed data
10. Alembic migrations
11. env example
12. requirements file

Constraints:
1. do not modify frontend files
2. do not redesign architecture while coding unless there is a clear implementation blocker
3. if architecture changes are necessary, document them in docs/backend_change_log.md
4. keep the implementation pragmatic and aligned to the existing frontend

After changes, provide:
1. files changed
2. what works
3. what remains stubbed or fragile
4. commands to run locally