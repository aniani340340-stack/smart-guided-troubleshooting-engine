"""Diagnostic Flow and Branching Engine for Smart Guided Troubleshooting.
Represents multi-step diagnostic paths with explicit conditional branching on pass, fail, or skip.
"""
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from theme02_troubleshooting_engine.core.schema import Goal, Action, StepGroup, Deeplink, ValidationDeepLink, actionCategory


class DiagnosticStepNode(BaseModel):
    step_id: str
    action_name: str
    instruction: str
    why_this_step: str
    expected_result: str
    category: str = "auto"  # auto, manual, critical
    actionable_deeplink: Optional[Deeplink] = None
    validation_deeplink: Optional[ValidationDeepLink] = None
    on_pass_target: Optional[str] = None  # step_id or "RESOLVED"
    on_fail_target: Optional[str] = None  # step_id or "ESCALATED"
    on_skip_target: Optional[str] = None  # step_id or "NEXT"
    is_terminal: bool = False
    is_remedial: bool = False


class DiagnosticFlow(BaseModel):
    flow_id: str
    title: str
    canonical_key: str
    nodes: Dict[str, DiagnosticStepNode] = {}
    entry_node_id: str
    current_node_id: str
    path_taken: List[str] = []
    total_main_steps: int = 1

    def get_current_node(self) -> Optional[DiagnosticStepNode]:
        return self.nodes.get(self.current_node_id)

    def transition(self, result: str) -> Tuple[Optional[DiagnosticStepNode], str]:
        """Transitions to the next node based on feedback ('passed', 'failed', 'skipped').
        Returns: (next_node, outcome_status: 'ACTIVE' | 'RESOLVED' | 'ESCALATED')
        """
        curr = self.get_current_node()
        if not curr:
            return None, "ESCALATED"

        self.path_taken.append(self.current_node_id)
        target_id: Optional[str] = None

        if result == "passed":
            target_id = curr.on_pass_target
        elif result == "failed":
            target_id = curr.on_fail_target
        elif result == "skipped":
            target_id = curr.on_skip_target or curr.on_pass_target
        else:
            target_id = curr.on_pass_target

        if not target_id or target_id == "RESOLVED":
            return None, "RESOLVED"
        if target_id == "ESCALATED":
            return None, "ESCALATED"

        if target_id in self.nodes:
            self.current_node_id = target_id
            return self.nodes[target_id], "ACTIVE"

        return None, "RESOLVED"


def _generate_explanations(action_name: str, step_text: str) -> Tuple[str, str]:
    """Generates concise, human-friendly Galaxy diagnostic rationales."""
    name_l = action_name.lower()
    step_l = step_text.lower()

    if "wifi" in name_l or "wi-fi" in name_l or "connection" in name_l or "network" in name_l:
        why = "Verifies your device has an active IP connection to communicate with services."
        expected = "The device should connect to Wi-Fi and load network traffic successfully."
    elif "power" in name_l or "charge" in name_l or "battery" in name_l:
        why = "Ensures sufficient power delivery and rules out depleted battery faults."
        expected = "Charging indicator appears on display or battery reaches adequate charge."
    elif "restart" in name_l or "reboot" in name_l:
        why = "Clears transient background system deadlocks and memory corruption safely."
        expected = "The phone reboots normally to the lock screen with core services active."
    elif "safe mode" in name_l:
        why = "Isolates third-party application conflicts by booting only verified system apps."
        expected = "'Safe Mode' displays in bottom corner and misbehaving apps are disabled."
    elif "cache" in name_l or "storage" in name_l:
        why = "Flushes stale application state and temporary cached assets causing freezes."
        expected = "App cache is wiped without deleting your personal account files."
    elif "touch" in name_l or "responsiveness" in name_l or "screen" in name_l:
        why = "Validates display digitizer responsiveness and hardware touch latency."
        expected = "Taps and navigation gestures register immediately across all screen areas."
    elif "smart switch" in name_l or "transfer" in name_l:
        why = "Establishes secure peer-to-peer data sync between your devices."
        expected = "QR code scans successfully and device handshake is completed."
    elif "inspect" in name_l or "physical" in name_l or "damage" in name_l:
        why = "Checks the physical chassis, ports, and Liquid Damage Indicator (LDI) for hazards."
        expected = "Hardware is physically intact with no corrosion or cracked glass."
    else:
        why = f"Executes {action_name} to restore normal Galaxy operational parameters."
        expected = "Settings are configured appropriately and device responds normally."

    return why, expected


def build_flow_from_goal(goal: Goal, query: str, canonical_key: str) -> DiagnosticFlow:
    """Builds an interconnected DiagnosticFlow with conditional branching from a validated Goal."""
    nodes: Dict[str, DiagnosticStepNode] = {}
    main_step_ids: List[str] = []

    # Flatten actions into primary diagnostic steps
    step_counter = 1
    for action in goal.actions:
        action_name = action.actionName
        category = action.category.value if action.category else "auto"
        for sg in action.stepGroups:
            step_text = " ".join(sg.steps) if sg.steps else f"Perform {action_name}"
            step_id = f"step_{step_counter}"
            main_step_ids.append(step_id)

            why_text, exp_text = _generate_explanations(action_name, step_text)

            node = DiagnosticStepNode(
                step_id=step_id,
                action_name=action_name,
                instruction=step_text,
                why_this_step=why_text,
                expected_result=exp_text,
                category=category,
                actionable_deeplink=sg.actionableDeeplink,
                validation_deeplink=sg.validationDeeplink,
                is_terminal=False,
                is_remedial=False
            )
            nodes[step_id] = node
            step_counter += 1

    if not nodes:
        # Fallback single node
        nodes["step_1"] = DiagnosticStepNode(
            step_id="step_1",
            action_name="Basic Device Inspection",
            instruction="Inspect phone display and restart the device.",
            why_this_step="Resolves transient system glitches.",
            expected_result="Phone restarts and screen turns on.",
            category="auto",
            on_pass_target="RESOLVED",
            on_fail_target="ESCALATED",
            on_skip_target="RESOLVED"
        )
        main_step_ids = ["step_1"]

    # Link nodes with branching logic
    total_steps = len(main_step_ids)
    for idx, sid in enumerate(main_step_ids):
        node = nodes[sid]
        is_last = (idx == total_steps - 1)
        next_sid = main_step_ids[idx + 1] if not is_last else "RESOLVED"

        # Check if we should inject an intelligent remedial branch on failure
        # For example, if a check or auto step fails, branch to a targeted fix or restart
        remedial_node_id: Optional[str] = None
        action_lower = node.action_name.lower()
        if not is_last and node.category == "auto" and any(k in action_lower for k in ["wifi", "wi-fi", "network"]):
            # Wi-Fi check failed -> Branch to Enable Wi-Fi
            remedial_id = f"remedial_{sid}_toggle"
            nodes[remedial_id] = DiagnosticStepNode(
                step_id=remedial_id,
                action_name="Enable Wi-Fi Adapter",
                instruction="Navigate to Settings > Connections > Wi-Fi and toggle Wi-Fi ON.",
                why_this_step="Wi-Fi was reported disabled or disconnected during initial verification.",
                expected_result="Wi-Fi turns on and connects to known access point.",
                category="auto",
                actionable_deeplink=node.actionable_deeplink,
                on_pass_target=next_sid,
                on_fail_target=next_sid,
                on_skip_target=next_sid,
                is_remedial=True
            )
            remedial_node_id = remedial_id
        elif not is_last and "cache" in node.action_name.lower():
            # Clearing cache failed -> Branch to Storage Reset
            remedial_id = f"remedial_{sid}_data"
            nodes[remedial_id] = DiagnosticStepNode(
                step_id=remedial_id,
                action_name="Clear Application Data",
                instruction="Open Settings > Apps > Email > Storage and tap Clear Data.",
                why_this_step="Cache flush was insufficient; resetting application data clears corrupted local state.",
                expected_result="Application database resets to fresh factory defaults.",
                category="critical",
                on_pass_target=next_sid,
                on_fail_target=next_sid,
                on_skip_target=next_sid,
                is_remedial=True
            )
            remedial_node_id = remedial_id

        # Set pass, fail, skip targets
        node.on_pass_target = next_sid
        node.on_skip_target = next_sid

        if is_last:
            # If the final step fails, escalate to Samsung Authorized Support
            node.on_fail_target = "ESCALATED"
            node.is_terminal = True
        elif remedial_node_id:
            node.on_fail_target = remedial_node_id
        else:
            # If an intermediate step fails, proceed to next diagnostic level
            node.on_fail_target = next_sid

    entry_id = main_step_ids[0]
    return DiagnosticFlow(
        flow_id=f"flow_{canonical_key.replace(' ', '_')}",
        title=goal.title,
        canonical_key=canonical_key,
        nodes=nodes,
        entry_node_id=entry_id,
        current_node_id=entry_id,
        total_main_steps=total_steps
    )
