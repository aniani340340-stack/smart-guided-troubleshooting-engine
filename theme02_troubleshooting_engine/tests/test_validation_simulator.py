"""Tests for the deterministic ValidationSimulator.
Verifies telemetry evaluation, key mapping, condition handling, and state overrides.
"""
import pytest
from theme02_troubleshooting_engine.core.validation_simulator import ValidationSimulator, DEFAULT_SIMULATED_STATE
from theme02_troubleshooting_engine.core.schema import ValidationDeepLink, Condition, ResultTypes


def test_initial_state():
    sim = ValidationSimulator()
    state = sim.get_state()
    assert "wifi_enabled" in state
    assert "battery_level" in state
    assert state["wifi_enabled"] is True


def test_boolean_validation_equal():
    sim = ValidationSimulator(initial_state={"double_tap_to_wake": True})

    val_dl = ValidationDeepLink(
        deeplink="bixby://masked/val/test1",
        key="Double tap to turn on screen",
        resultType=ResultTypes.boolean,
        condition=Condition.equal,
        value="True"
    )

    res = sim.evaluate_validation(val_dl)
    assert res.is_valid is True
    assert res.target_state_key == "double_tap_to_wake"
    assert res.actual_value is True

    # Test failure when state does not match
    sim.update_state({"double_tap_to_wake": False})
    res_fail = sim.evaluate_validation(val_dl)
    assert res_fail.is_valid is False
    assert res_fail.actual_value is False


def test_numeric_validation_greater_and_less():
    sim = ValidationSimulator(initial_state={"battery_level": 75})

    val_dl_greater = ValidationDeepLink(
        deeplink="bixby://masked/val/batt",
        key="Battery level",
        resultType=ResultTypes.intNum,
        condition=Condition.greater,
        value="50"
    )

    res1 = sim.evaluate_validation(val_dl_greater)
    assert res1.is_valid is True

    val_dl_less = ValidationDeepLink(
        deeplink="bixby://masked/val/batt",
        key="Battery level",
        resultType=ResultTypes.intNum,
        condition=Condition.less,
        value="50"
    )
    res2 = sim.evaluate_validation(val_dl_less)
    assert res2.is_valid is False


def test_state_overrides():
    sim = ValidationSimulator()

    val_dl = ValidationDeepLink(
        deeplink="bixby://masked/val/wifi",
        key="Wi-Fi",
        resultType=ResultTypes.boolean,
        condition=Condition.equal,
        value="True"
    )

    # Force override to False without mutating base state
    res_override = sim.evaluate_validation(val_dl, state_overrides={"wifi_enabled": False})
    assert res_override.is_valid is False
    # Base state remains True
    assert sim.get_state()["wifi_enabled"] is True


def test_deterministic_repeatability():
    sim = ValidationSimulator()
    val_dl = ValidationDeepLink(
        deeplink="bixby://masked/val/sim",
        key="Motion smoothness",
        resultType=ResultTypes.string,
        condition=Condition.equal,
        value="standard"
    )

    # 10 successive runs must produce identical results
    results = [sim.evaluate_validation(val_dl).is_valid for _ in range(10)]
    assert all(r is True for r in results)
