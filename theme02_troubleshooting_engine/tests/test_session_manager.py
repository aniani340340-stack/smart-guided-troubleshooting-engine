"""Tests for the thread-safe SessionManager.
Verifies session lifecycle, state transitions, concurrent thread safety, and error handling.
"""
import pytest
import threading
import time
from typing import List

from theme02_troubleshooting_engine.core.session_manager import SessionManager, TroubleshootingSession
from theme02_troubleshooting_engine.core.schema import Goal, Action, StepGroup, Deeplink, actionCategory


def _create_sample_goal() -> Goal:
    return Goal(
        goal="Follow these steps to perform this Wi-Fi Network Troubleshooting",
        title="Wi-Fi network connection",
        score=0.95,
        actions=[
            Action(
                actionName="Check Wi-Fi Status",
                description="It will check your active wireless network",
                category=actionCategory.auto,
                stepGroups=[
                    StepGroup(
                        steps=["Open Settings.", "Tap Connections.", "Verify Wi-Fi is toggled on."],
                        actionableDeeplink=Deeplink(
                            deeplink="bixby://masked/act/wifi123",
                            description="Open Wi-Fi Settings"
                        )
                    )
                ]
            ),
            Action(
                actionName="Restart Phone",
                description="It will restart the mobile device safely",
                category=actionCategory.critical,
                stepGroups=[
                    StepGroup(
                        steps=["Press and hold Power and Volume Down.", "Select Restart."]
                    )
                ]
            )
        ]
    )


def test_session_creation_and_retrieval():
    mgr = SessionManager()
    mgr.clear_all()

    goal = _create_sample_goal()
    diagnosis = {"title": "Wi-Fi network connection", "canonical_key": "wifi"}
    device = {"device_model": "Galaxy S22", "os_version": "One UI 6.1"}

    session = mgr.create_session(
        query="My Galaxy S22 Wi-Fi keeps disconnecting",
        diagnosis=diagnosis,
        goal=goal,
        device_context=device
    )

    assert session.session_id is not None
    assert session.status == "ACTIVE"
    assert session.query == "My Galaxy S22 Wi-Fi keeps disconnecting"
    assert session.device_context["device_model"] == "Galaxy S22"
    assert session.diagnosis["canonical_key"] == "wifi"

    fetched = mgr.get_session(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id


def test_session_feedback_passed_resolution():
    mgr = SessionManager()
    mgr.clear_all()

    goal = _create_sample_goal()
    session = mgr.create_session(
        query="Wi-Fi issue",
        diagnosis={"title": "Wi-Fi Connection", "canonical_key": "wifi"},
        goal=goal
    )

    # Step 1: Pass
    updated = mgr.record_feedback(session.session_id, "passed")
    assert len(updated.completed_steps) == 1

    # Step 2: Pass -> Should resolve
    updated2 = mgr.record_feedback(session.session_id, "passed")
    assert updated2.status == "RESOLVED"
    assert updated2.resolution_summary is not None
    assert updated2.resolution_summary["resolved"] is True


def test_session_escalation():
    mgr = SessionManager()
    mgr.clear_all()

    goal = _create_sample_goal()
    session = mgr.create_session(
        query="Wi-Fi issue",
        diagnosis={"title": "Wi-Fi Connection", "canonical_key": "wifi"},
        goal=goal
    )

    escalated = mgr.escalate_session(session.session_id, reason="User hardware damaged")
    assert escalated.status == "ESCALATED"
    assert escalated.escalation_summary["escalated"] is True
    assert "Samsung Support" in escalated.escalation_summary["recommended_action"]


def test_invalid_session_id():
    mgr = SessionManager()
    with pytest.raises(KeyError):
        mgr.record_feedback("non-existent-session-id-12345", "passed")


def test_concurrent_session_access():
    mgr = SessionManager()
    mgr.clear_all()

    goal = _create_sample_goal()
    created_ids: List[str] = []
    lock = threading.Lock()

    def worker(idx: int):
        s = mgr.create_session(
            query=f"Query {idx}",
            diagnosis={"title": f"Issue {idx}", "canonical_key": f"key_{idx}"},
            goal=goal
        )
        with lock:
            created_ids.append(s.session_id)
        # Advance session
        mgr.record_feedback(s.session_id, "passed")
        mgr.record_feedback(s.session_id, "passed")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(created_ids) == 15
    for sid in created_ids:
        sess = mgr.get_session(sid)
        assert sess is not None
        assert sess.status == "RESOLVED"
