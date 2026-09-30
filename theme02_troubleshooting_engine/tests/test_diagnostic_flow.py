"""Tests for DiagnosticFlow branching and state machine.
Verifies linear paths, conditional failure branching, skipping, resolution, and escalation.
"""
import pytest
from theme02_troubleshooting_engine.core.diagnostic_flow import build_flow_from_goal, DiagnosticFlow, DiagnosticStepNode
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
                actionName="Verify Internet Connection",
                description="It will test active device data transfer",
                category=actionCategory.auto,
                stepGroups=[
                    StepGroup(
                        steps=["Try loading a test webpage in Samsung Internet."]
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


def test_flow_construction():
    goal = _create_sample_goal()
    flow = build_flow_from_goal(goal, "Wi-Fi not working", "wifi")

    assert flow.flow_id.startswith("flow_")
    assert flow.entry_node_id == "step_1"
    assert flow.current_node_id == "step_1"
    assert len(flow.nodes) >= 3

    node1 = flow.get_current_node()
    assert node1 is not None
    assert "Wi-Fi" in node1.action_name
    assert node1.why_this_step is not None
    assert node1.expected_result is not None


def test_flow_linear_pass_to_resolution():
    goal = _create_sample_goal()
    flow = build_flow_from_goal(goal, "Wi-Fi issue", "wifi")

    # Step 1: pass -> goes to step 2
    n2, s2 = flow.transition("passed")
    assert s2 == "ACTIVE"
    assert n2 is not None

    # Step 2: pass -> goes to step 3
    n3, s3 = flow.transition("passed")
    assert s3 == "ACTIVE"
    assert n3 is not None

    # Step 3 (final): pass -> RESOLVED
    n_final, s_final = flow.transition("passed")
    assert s_final == "RESOLVED"
    assert n_final is None


def test_flow_failure_branching_to_remedial():
    goal = _create_sample_goal()
    flow = build_flow_from_goal(goal, "Wi-Fi issue", "wifi")

    # Step 1 is "Check Wi-Fi Status". If it fails, our builder injects remedial node "Enable Wi-Fi Adapter"
    node1 = flow.get_current_node()
    assert node1.on_fail_target is not None
    assert "remedial" in node1.on_fail_target

    remedial_node, status = flow.transition("failed")
    assert status == "ACTIVE"
    assert remedial_node is not None
    assert remedial_node.is_remedial is True
    assert "Enable Wi-Fi" in remedial_node.action_name


def test_flow_final_step_failure_escalation():
    goal = _create_sample_goal()
    flow = build_flow_from_goal(goal, "Wi-Fi issue", "wifi")

    # Advance to last step
    flow.current_node_id = "step_3"
    last_node = flow.get_current_node()
    assert last_node.is_terminal is True
    assert last_node.on_fail_target == "ESCALATED"

    next_node, status = flow.transition("failed")
    assert status == "ESCALATED"
    assert next_node is None


def test_flow_skipping():
    goal = _create_sample_goal()
    flow = build_flow_from_goal(goal, "Wi-Fi issue", "wifi")

    # Skip step 1 -> advances to next step
    next_node, status = flow.transition("skipped")
    assert status == "ACTIVE"
    assert next_node is not None
    assert next_node.step_id == "step_2"
