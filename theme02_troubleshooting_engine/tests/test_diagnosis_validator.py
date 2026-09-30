"""Tests for semantic consistency and diagnosis validator.
Verifies cross-domain mismatch rejection, domain classification, and regression prevention.
"""
import pytest
from theme02_troubleshooting_engine.core.diagnosis_validator import (
    validate_diagnosis,
    classify_text_domain,
    DOMAIN_LEXICON
)
from theme02_troubleshooting_engine.core.schema import Goal, Action, StepGroup, Deeplink, actionCategory
from fastapi.testclient import TestClient
from theme02_troubleshooting_engine.api.app import app


def _make_dummy_goal(title: str, action_name: str) -> Goal:
    return Goal(
        goal=f"Follow these steps to perform this {title} Troubleshooting",
        title=title,
        score=0.95,
        actions=[
            Action(
                actionName=action_name,
                description="It will help configure optimal device settings",
                category=actionCategory.auto,
                stepGroups=[
                    StepGroup(
                        steps=["Navigate to settings and toggle option."],
                        actionableDeeplink=Deeplink(deeplink="bixby://masked/act/123", description="Open Settings")
                    )
                ]
            )
        ]
    )


def test_wifi_query_cannot_return_email_diagnosis():
    query = "My Galaxy S22 Wi-Fi keeps disconnecting and cannot load web pages"
    email_goal = _make_dummy_goal("Email server not responding", "Review Email Account Settings")

    is_valid, reason, domain = validate_diagnosis(query, email_goal)
    assert is_valid is False
    assert domain == "NETWORK"
    assert "rejected" in reason.lower() or "targets wi-fi" in reason.lower()


def test_email_query_can_return_email_diagnosis():
    query = "Cannot send or receive emails in Gmail application"
    email_goal = _make_dummy_goal("Email server not responding", "Review Email Account Settings")

    is_valid, reason, domain = validate_diagnosis(query, email_goal)
    assert is_valid is True
    assert domain == "EMAIL"


def test_display_query_cannot_return_battery_diagnosis():
    query = "Galaxy phone screen turns completely blank or black and touch is unresponsive"
    battery_goal = _make_dummy_goal("Battery fast drain", "Check Battery Performance")

    is_valid, reason, domain = validate_diagnosis(query, battery_goal)
    assert is_valid is False
    assert domain == "DISPLAY"


def test_battery_query_cannot_return_camera_diagnosis():
    query = "My phone battery dies fast and drains quickly within two hours"
    camera_goal = _make_dummy_goal("Camera video flicker", "Adjust Camera Settings")

    is_valid, reason, domain = validate_diagnosis(query, camera_goal)
    assert is_valid is False
    assert domain == "BATTERY"


def test_bluetooth_query_cannot_return_email_diagnosis():
    query = "Galaxy buds wireless headphones pairing fails and bluetooth disconnects"
    email_goal = _make_dummy_goal("Email server not responding", "Review Email Account Settings")

    is_valid, reason, domain = validate_diagnosis(query, email_goal)
    assert is_valid is False
    assert domain == "BLUETOOTH"


def test_generic_query_does_not_crash():
    query = "I have an issue with some options on my mobile device"
    any_goal = _make_dummy_goal("Device options", "Check Device Settings")

    is_valid, reason, domain = validate_diagnosis(query, any_goal)
    assert is_valid is True
    assert domain == "GENERIC"


def test_existing_valid_diagnoses_remain_valid():
    query = "Phone screen flickers continuously and display flashes"
    display_goal = _make_dummy_goal("Screen flicker glitch", "Adjust Motion Smoothness")

    is_valid, reason, domain = validate_diagnosis(query, display_goal)
    assert is_valid is True
    assert domain == "DISPLAY"


def test_compound_query_handled_safely():
    query = "Phone display flickers and Wi-Fi disconnects frequently"
    domain, conf, scores = classify_text_domain(query)
    # Both DISPLAY and NETWORK have positive scores
    assert scores["DISPLAY"] > 0
    assert scores["NETWORK"] > 0


def test_regression_wifi_disconnecting_session_api():
    """Exact regression test:
    Input: 'My Galaxy S22 Wi-Fi keeps disconnecting and cannot load web pages'
    Expected: NETWORK domain diagnosis (Wi-Fi connectivity), NOT 'Email server connection'.
    """
    client = TestClient(app)
    response = client.post("/v1/session/start", json={
        "query": "My Galaxy S22 Wi-Fi keeps disconnecting and cannot load web pages",
        "device_model": "Galaxy S22",
        "os_version": "One UI 6.1"
    })
    assert response.status_code == 200
    data = response.json()

    diag_title = data["diagnosis"]["title"]
    canonical_key = data["diagnosis"]["canonical_key"]

    # Must be Wi-Fi / Network, NEVER Email
    assert "email" not in diag_title.lower()
    assert "email" not in canonical_key.lower()
    assert ("wi-fi" in diag_title.lower() or "network" in diag_title.lower() or "wifi" in canonical_key.lower())

    # Step 1 should be Check Wi-Fi
    step1 = data["current_step"]
    assert step1 is not None
    assert ("wi-fi" in step1["action_name"].lower() or "network" in step1["action_name"].lower())
