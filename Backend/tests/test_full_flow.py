"""Task 6 — Complete backend flow test.

End-to-end: add account → add source → trigger scan → list signals → signal detail → evidence.

Uses the simulated website extractor + positioning normalizer to produce
a real signal through the ingestion pipeline, then verifies every API endpoint
in the chain returns correct data.

NOTE: This test commits real data to the DB and cleans up after itself.
It does NOT use the transactional db_session fixture since the ingestion
runner commits internally.
"""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.auth import WorkspaceContext, get_workspace_context
from app.db import get_db, SessionLocal
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.account import Account
from app.models.account_source import AccountSource
from app.models.signal import Signal
from app.models.raw_event import RawEvent
from app.ingestion.runner import (
    run_extraction, run_normalization,
    register_extractor, register_normalizer,
)
from app.ingestion.extractors.simulated_website import SimulatedWebsiteExtractor
from app.ingestion.normalizers.positioning import PositioningNormalizer


class TestFullBackendFlow:
    """Tests the complete lifecycle: account → source → scan → signals → evidence."""

    def test_full_pipeline_flow(self):
        """
        1. Create user + workspace + account + website source
        2. Run extraction (simulated website extractor)
        3. Run normalization (positioning normalizer)
        4. Verify signals appear via API
        5. Verify signal detail via API
        6. Verify evidence via API
        """
        # Ensure extractors/normalizers are registered
        # Note: event_type is "website_change" (extractor output), not "positioning_shift" (signal type)
        register_extractor("website", SimulatedWebsiteExtractor())
        register_normalizer("website_change", PositioningNormalizer())

        db = SessionLocal()
        created_ids = {}  # Track IDs for cleanup

        try:
            # --- Step 1: Create user, workspace, account, source ---
            user = User(
                id=uuid.uuid4(), email="flowtest@test.com", display_name="Flow Tester"
            )
            db.add(user)
            db.flush()
            created_ids["user_id"] = user.id

            ws = Workspace(id=uuid.uuid4(), name="Flow Test WS", created_by=user.id)
            db.add(ws)
            db.flush()
            created_ids["ws_id"] = ws.id

            db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role="owner"))
            db.flush()

            account = Account(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                name="Ramp AI (flow test)",
                domain="rampai-flowtest.com",
                industry="AI / ML",
                status="New",
            )
            db.add(account)
            db.flush()
            created_ids["account_id"] = account.id

            source = AccountSource(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                account_id=account.id,
                source_type="website",
                source_url="https://rampai.com",
                source_key="ramp-ai",
                is_active=True,
            )
            db.add(source)
            db.flush()
            created_ids["source_id"] = source.id

            # Remove conflicting external_ids from prior runs
            conflicting_ids = ["webdiff:web-diff-ramp-001", "webdiff:web-diff-ramp-003"]
            conflicting_raw = db.scalars(
                select(RawEvent).where(RawEvent.external_id.in_(conflicting_ids))
            ).all()
            for re in conflicting_raw:
                db.execute(delete(Signal).where(Signal.raw_event_id == re.id))
            db.execute(delete(RawEvent).where(RawEvent.external_id.in_(conflicting_ids)))
            db.commit()

            # --- Step 2: Run extraction ---
            extract_stats = run_extraction(
                db,
                source_type="website",
                account_id=account.id,
            )
            assert extract_stats["sources_checked"] == 1
            assert extract_stats["events_stored"] >= 1, (
                f"Expected at least 1 event stored, got {extract_stats}"
            )

            # --- Step 3: Run normalization ---
            norm_stats = run_normalization(db, event_type="website_change")
            assert norm_stats["signals_created"] >= 1, (
                f"Expected at least 1 signal created, got {norm_stats}"
            )

            # --- Step 4: List signals via API ---
            def override_db():
                # Reuse the same session so we see uncommitted-to-other-sessions data
                yield db

            def override_ctx():
                return WorkspaceContext(
                    user=user, workspace_id=ws.id, role="owner", db=db
                )

            app.dependency_overrides[get_db] = override_db
            app.dependency_overrides[get_workspace_context] = override_ctx

            with TestClient(app) as client:
                resp = client.get("/signals", params={"account_id": str(account.id)})
                assert resp.status_code == 200
                signals_data = resp.json()["data"]
                assert len(signals_data) >= 1, f"Expected signals, got {signals_data}"

                # Find a signal with evidence
                signal_with_evidence = None
                for s in signals_data:
                    if s.get("hasEvidence"):
                        signal_with_evidence = s
                        break

                assert signal_with_evidence is not None, (
                    f"Expected at least one signal with evidence. Signals: {signals_data}"
                )
                signal_id = signal_with_evidence["id"]

                # --- Step 5: Signal detail via API ---
                resp = client.get(f"/signals/{signal_id}")
                assert resp.status_code == 200
                detail = resp.json()["data"]
                assert detail["id"] == signal_id
                assert detail["type"] == "positioning_shift"
                assert detail["hasEvidence"] is True

                # --- Step 6: Evidence via API ---
                resp = client.get(f"/signals/{signal_id}/evidence")
                assert resp.status_code == 200
                evidence = resp.json()["data"]
                assert evidence["signalId"] == signal_id
                assert evidence["rawEventId"] is not None
                assert evidence["eventType"] == "website_change"  # raw event type, not signal type
                assert evidence["rawPayload"] is not None
                assert evidence["sourceType"] == "website"
                assert evidence["confidenceScore"] is not None
                assert evidence["confidenceScore"] > 0

            app.dependency_overrides.clear()

        finally:
            # Cleanup: remove all test data in reverse dependency order
            if "account_id" in created_ids:
                db.execute(
                    delete(Signal).where(Signal.account_id == created_ids["account_id"])
                )
                db.execute(
                    delete(RawEvent).where(RawEvent.account_id == created_ids["account_id"])
                )
                db.execute(
                    delete(AccountSource).where(
                        AccountSource.account_id == created_ids["account_id"]
                    )
                )
                db.execute(
                    delete(Account).where(Account.id == created_ids["account_id"])
                )
            if "ws_id" in created_ids:
                db.execute(
                    delete(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == created_ids["ws_id"]
                    )
                )
                db.execute(
                    delete(Workspace).where(Workspace.id == created_ids["ws_id"])
                )
            if "user_id" in created_ids:
                db.execute(delete(User).where(User.id == created_ids["user_id"]))
            db.commit()
            db.close()
