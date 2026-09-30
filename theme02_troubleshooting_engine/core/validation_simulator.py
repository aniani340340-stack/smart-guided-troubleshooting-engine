"""Deterministic Validation Simulator for Samsung Galaxy Troubleshooting.
Evaluates supported validation conditions using simulated device state.
Does NOT execute real device operations. Completely safe simulation environment.
"""
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel

from theme02_troubleshooting_engine.core.schema import ValidationDeepLink, Condition, ResultTypes


# Default simulated device telemetry state
DEFAULT_SIMULATED_STATE: Dict[str, Any] = {
    "wifi_enabled": True,
    "internet_connected": False,
    "screen_responsive": True,
    "battery_level": 72,
    "battery_charging": False,
    "bluetooth_enabled": True,
    "double_tap_to_wake": False,
    "auto_rotate": False,
    "safe_mode": False,
    "airplane_mode": False,
    "show_charging_information": True,
    "allow_find_phone": True,
    "motion_smoothness": "standard",
    "power_saving_mode": False,
    "storage_cache_cleared": False,
    "email_sync_active": False,
    "smart_switch_transferring": False,
    "assistant_menu_enabled": True,
    "split_screen_active": False,
    "cast_screen_active": False,
}

# Mapping between catalog validation keys and simulated state keys
KEY_MAPPINGS: Dict[str, str] = {
    "double tap to turn on screen": "double_tap_to_wake",
    "show charging information": "show_charging_information",
    "allow this phone to be found": "allow_find_phone",
    "wifi": "wifi_enabled",
    "wi-fi": "wifi_enabled",
    "internet": "internet_connected",
    "bluetooth": "bluetooth_enabled",
    "auto rotate": "auto_rotate",
    "safe mode": "safe_mode",
    "airplane mode": "airplane_mode",
    "battery level": "battery_level",
    "motion smoothness": "motion_smoothness",
    "power saving": "power_saving_mode",
    "cache": "storage_cache_cleared",
    "email sync": "email_sync_active",
    "assistant menu": "assistant_menu_enabled",
    "smart switch": "smart_switch_transferring",
}


class ValidationResult(BaseModel):
    is_valid: bool
    key: str
    target_state_key: str
    condition: Optional[str] = None
    expected_value: Any = None
    actual_value: Any = None
    message: str
    simulated_telemetry: Dict[str, Any]


class ValidationSimulator:
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self.state: Dict[str, Any] = dict(DEFAULT_SIMULATED_STATE)
        if initial_state:
            self.state.update(initial_state)

    def get_state(self) -> Dict[str, Any]:
        """Returns a copy of the current simulated device state."""
        return dict(self.state)

    def update_state(self, updates: Dict[str, Any]):
        """Updates simulated device state deterministically."""
        self.state.update(updates)

    def resolve_state_key(self, key_name: str) -> str:
        """Maps validation key name to internal state key."""
        clean_key = key_name.lower().strip()
        for pattern, state_key in KEY_MAPPINGS.items():
            if pattern in clean_key:
                return state_key
        # Fallback to sanitized string
        sanitized = clean_key.replace(" ", "_").replace("-", "_")
        return sanitized

    def evaluate_validation(
        self,
        validation: ValidationDeepLink,
        state_overrides: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Evaluates a ValidationDeepLink against current or overridden simulated device state.
        Deterministic: No random results.
        """
        current_state = dict(self.state)
        if state_overrides:
            current_state.update(state_overrides)

        state_key = self.resolve_state_key(validation.key)
        
        # If key is not in state, default to False or 0 depending on expected value
        expected_raw = validation.value
        condition = validation.condition.value if validation.condition else "equal"
        result_type = validation.resultType.value if validation.resultType else "str"

        actual_val = current_state.get(state_key)

        # Handle boolean types
        if result_type == "boolean":
            expected_bool = str(expected_raw).lower() in {"true", "1", "yes"} if expected_raw is not None else True
            actual_bool = bool(actual_val)
            is_valid = (actual_bool == expected_bool)
            msg = f"Simulated check: '{validation.key}' state is {actual_bool} (expected {expected_bool})."
            return ValidationResult(
                is_valid=is_valid,
                key=validation.key,
                target_state_key=state_key,
                condition=condition,
                expected_value=expected_bool,
                actual_value=actual_bool,
                message=msg,
                simulated_telemetry=current_state
            )

        # Handle numeric types (integer / float)
        if result_type in {"integer", "float"}:
            try:
                exp_num = float(expected_raw) if expected_raw is not None else 0.0
                act_num = float(actual_val) if actual_val is not None else 0.0
                
                if condition == "greater":
                    is_valid = (act_num > exp_num)
                elif condition == "less":
                    is_valid = (act_num < exp_num)
                else:
                    is_valid = (act_num == exp_num)
                    
                msg = f"Simulated telemetry: '{validation.key}' is {act_num} (condition: {condition} {exp_num})."
                return ValidationResult(
                    is_valid=is_valid,
                    key=validation.key,
                    target_state_key=state_key,
                    condition=condition,
                    expected_value=exp_num,
                    actual_value=act_num,
                    message=msg,
                    simulated_telemetry=current_state
                )
            except (ValueError, TypeError):
                pass

        # String / Default fallback comparison
        exp_str = str(expected_raw).lower() if expected_raw is not None else ""
        act_str = str(actual_val).lower() if actual_val is not None else ""
        is_valid = (exp_str == act_str)
        msg = f"Simulated check: '{validation.key}' matched '{act_str}' (expected '{exp_str}')."

        return ValidationResult(
            is_valid=is_valid,
            key=validation.key,
            target_state_key=state_key,
            condition=condition,
            expected_value=exp_str,
            actual_value=act_str,
            message=msg,
            simulated_telemetry=current_state
        )
