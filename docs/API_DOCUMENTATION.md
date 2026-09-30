# Samsung Smart Guided Troubleshooting Engine — API Documentation

**Version:** 1.0.0  
**Base URL:** `http://127.0.0.1:8000` (Local) / Configured via `VITE_API_BASE_URL` (Production)  
**Protocol:** REST over HTTP / JSON  

---

## Overview

The Troubleshooting Engine API provides two modes of operation:
1. **One-Shot Troubleshooting (`/v1/troubleshoot`):** Evaluates a user complaint against knowledge bases and returns a complete, static diagnostic plan matching the official Theme 02 schema.
2. **Interactive Session Engine (`/v1/session/*`):** State-machine driven, multi-turn troubleshooting with multi-intent decomposition, step-by-step guidance, settings deep linking, remedial branching, and simulated device validation.

---

## Endpoints Summary

| Method | Path | Description |
|:---:|:---|:---|
| `GET` | `/health` | Service health check and readiness probe. |
| `POST` | `/v1/troubleshoot` | Generates a static Theme 02 compliant troubleshooting plan. |
| `POST` | `/v1/session/start` | Starts an interactive guided troubleshooting session. |
| `GET` | `/v1/session/{session_id}` | Retrieves current session state and diagnostic progress. |
| `POST` | `/v1/session/{session_id}/feedback` | Records step feedback (`passed`, `failed`, `skipped`) and branches. |
| `POST` | `/v1/session/{session_id}/switch-intent` | Switches focused intent tab in multi-intent sessions. |
| `POST` | `/v1/session/{session_id}/simulate-validation` | Executes simulated device telemetry validation for the active step. |
| `GET` | `/v1/telemetry/state` | Returns the current state of simulated device sensors/toggles. |
| `POST` | `/v1/telemetry/state` | Updates the simulated device state toggles. |

---

## 1. GET `/health`

### Purpose
Readiness and liveness probe. Confirms that BM25 retriever, TF-IDF vectorizer, semantic cache, and PaddleOCR engines are initialized.

### Request
No parameters or request body required.

### Successful Response (`200 OK`)
```json
{
  "status": "ok"
}
```

### Error Responses
- `503 Service Unavailable`: Cache or indexes are still loading.

### Example
```bash
curl -X GET http://127.0.0.1:8000/health
```

---

## 2. POST `/v1/troubleshoot`

### Purpose
Processes a customer complaint and returns an atomic, canonical troubleshooting plan conforming to the official Theme 02 schema specification.

### Request Body
```json
{
  "query": "My Wi-Fi keeps disconnecting every few minutes",
  "siis_response": null
}
```

#### Fields
- `query` (string, required): The raw user complaint. Must be non-empty.
- `siis_response` (string | object, optional): Raw knowledge base article for cold-path extraction.

### Successful Response (`200 OK`)
```json
{
  "query": "My Wi-Fi keeps disconnecting every few minutes",
  "query_variations": [
    "wifi network connectivity",
    "wifi dropping out constantly",
    "cannot stay connected to wifi"
  ],
  "response": {
    "contexts": [
      {
        "goal": "Follow these steps to perform this Reset Network Settings",
        "title": "Reset Network Settings",
        "actions": [
          {
            "actionName": "Open Settings and select Reset Network",
            "category": "auto",
            "stepGroups": [
              {
                "groupName": "Navigate to Reset Settings",
                "steps": [
                  "Open device Settings",
                  "Tap General management",
                  "Tap Reset",
                  "Select Reset network settings"
                ]
              }
            ],
            "description": "It will reset your wireless configurations",
            "actionable_deeplink": {
              "deeplink": "bixby://dummy_positive",
              "description": "Reset network settings"
            },
            "validation_deeplink": {
              "deeplink": "bixby://dummy_positive",
              "description": "Verify network settings restored"
            }
          }
        ],
        "score": 0.95
      }
    ]
  },
  "meta": {
    "latency_ms": 3,
    "cache_hit": true,
    "cost_usd": 0.0,
    "fallback": null
  }
}
```

### Error Responses
- `400 Bad Request`: `{"detail": "Query string cannot be empty"}`
- `422 Unprocessable Entity`: Malformed JSON or invalid data types.

---

## 3. POST `/v1/session/start`

### Purpose
Initializes an interactive, multi-turn troubleshooting session with multi-intent decomposition, device context detection, and optional screenshot OCR.

### Request Body
```json
{
  "query": "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect",
  "device_model": "Galaxy S22",
  "os_version": "One UI 6.1 (Android 14)",
  "image_data": null,
  "image_filename": null,
  "error_code": null
}
```

#### Fields
- `query` (string, required): User complaint text.
- `device_model` (string, optional): Client device model (defaults to extracted or `Galaxy S22`).
- `os_version` (string, optional): Operating system version (defaults to `One UI 6.1`).
- `image_data` (string, optional): Base64-encoded image string or data URL (`data:image/png;base64,...`).
- `image_filename` (string, optional): Original uploaded filename.
- `error_code` (string, optional): Manual error code (e.g. `1001`, `BT-204`).

### Successful Response (`200 OK`)
```json
{
  "session_id": "7f8b9c2a-4d1e-450a-b28e-89a1b2c3d4e5",
  "status": "ACTIVE",
  "diagnosis": {
    "title": "Wi-Fi Disconnecting & Bluetooth Pairing Issue",
    "summary": "Identified potential network and bluetooth anomaly on Galaxy S22.",
    "canonical_key": "wifi_disconnecting",
    "confidence": 0.95,
    "domain": "NETWORK",
    "matched_via": "domain_grounded",
    "ai_fallback_used": false,
    "image_analysis_used": false,
    "image_evidence_confidence": 0.0,
    "error_codes": []
  },
  "current_step": {
    "step_id": "step_1",
    "action_name": "Toggle Wi-Fi Off and On",
    "description": "It will refresh your wireless connection",
    "instructions": [
      "Swipe down from top of screen to open Quick Settings",
      "Tap Wi-Fi icon to turn it off",
      "Wait 5 seconds and tap Wi-Fi icon again"
    ],
    "expected_result": "Wi-Fi reconnects automatically to saved network.",
    "is_remedial": false,
    "actionable_deeplink": {
      "deeplink": "bixby://dummy_positive",
      "description": "Open Wi-Fi Settings"
    },
    "validation_deeplink": {
      "deeplink": "bixby://dummy_positive",
      "description": "Check Wi-Fi Connected State"
    }
  },
  "progress": {
    "current": 1,
    "total": 4,
    "percent": 25
  },
  "device_context": {
    "model": "Galaxy S22",
    "device_model": "Galaxy S22",
    "series": "Galaxy S",
    "device_type": "phone",
    "os_version": "One UI 6.1 (Android 14)",
    "confidence": 0.85
  },
  "accessory": null,
  "matched_via": "domain_grounded",
  "ai_fallback_used": false,
  "image_analysis_used": false,
  "image_evidence_confidence": 0.0,
  "error_codes": [],
  "is_multi_intent": true,
  "active_intent_id": "intent_1",
  "intents": [
    {
      "id": "intent_1",
      "domain": "NETWORK",
      "issue": "Wi-Fi disconnecting",
      "title": "Wi-Fi Disconnecting",
      "status": "ACTIVE",
      "resolved": false,
      "progress": { "current": 1, "total": 4, "percent": 25 }
    },
    {
      "id": "intent_2",
      "domain": "BLUETOOTH",
      "issue": "Bluetooth earbuds won't connect",
      "title": "Bluetooth Pairing Failed",
      "status": "PENDING",
      "resolved": false,
      "progress": { "current": 0, "total": 3, "percent": 0 }
    }
  ]
}
```

---

## 4. POST `/v1/session/{session_id}/feedback`

### Purpose
Records outcome of the current diagnostic step (`passed`, `failed`, `skipped`). If the step failed, branches to a remedial action; if passed, advances to the next step or marks intent resolved.

### Request Body
```json
{
  "result": "passed",
  "details": {
    "notes": "Wi-Fi reconnected successfully"
  },
  "intent_id": null
}
```

#### Fields
- `result` (string, required): Must be one of `"passed"`, `"failed"`, or `"skipped"`.
- `details` (object, optional): Arbitrary client metadata or explicit override flags.
- `intent_id` (string, optional): Specific intent ID to submit feedback against (defaults to active intent).

### Successful Response (`200 OK`)
```json
{
  "session_id": "7f8b9c2a-4d1e-450a-b28e-89a1b2c3d4e5",
  "status": "ACTIVE",
  "current_step": {
    "step_id": "step_2",
    "action_name": "Restart Wi-Fi Router or Re-pair Network",
    "is_remedial": false
  },
  "progress": {
    "current": 2,
    "total": 4,
    "percent": 50
  },
  "resolved": false,
  "escalated": false,
  "completed_steps": ["Toggle Wi-Fi Off and On"],
  "failed_steps": [],
  "resolution_summary": null,
  "escalation_summary": null,
  "is_multi_intent": true,
  "active_intent_id": "intent_1",
  "intents": [...]
}
```

#### Remedial Branching on Failure:
When `result: "failed"` is submitted, `current_step` returns an alternative remedial step with `"is_remedial": true`.

#### Exhaustion Escalation:
If 6 consecutive steps fail, `status` becomes `"ESCALATED"`, and `escalation_summary` contains official Samsung Support instructions.

### Error Responses
- `400 Bad Request`: `Invalid result 'unknown'. Allowed: ['failed', 'passed', 'skipped']`
- `404 Not Found`: Session ID does not exist.

---

## 5. POST `/v1/session/{session_id}/switch-intent`

### Purpose
Switches active intent focus in a multi-intent session without resetting or modifying any intent's state.

### Request Body
```json
{
  "intent_id": "intent_2"
}
```

### Successful Response (`200 OK`)
Returns updated `SessionFeedbackResponse` with `active_intent_id: "intent_2"` and the current step corresponding to Intent 2.

### Error Responses
- `400 Bad Request`: Target intent ID does not exist in the session.
- `404 Not Found`: Session ID does not exist.

---

## 6. GET `/v1/session/{session_id}`

### Purpose
Fetches full multi-turn session state, device context, diagnostic progress, completed actions, and multi-intent metadata.

### Successful Response (`200 OK`)
Returns complete session dictionary including timestamps, history, and status flags.

### Error Responses
- `404 Not Found`: Session ID not found.

---

## 7. POST `/v1/session/{session_id}/simulate-validation`

### Purpose
Deterministically simulates a device hardware/sensor telemetry check for the active step (e.g. verifying whether Wi-Fi is actually connected or Bluetooth is enabled).

### Request Body
```json
{
  "state_overrides": {
    "wifi_connected": true
  }
}
```

### Successful Response (`200 OK`)
```json
{
  "is_valid": true,
  "key": "wifi_connected",
  "message": "Wi-Fi is currently connected.",
  "simulated_telemetry": {
    "wifi_enabled": true,
    "internet_connected": true,
    "bluetooth_enabled": false
  }
}
```

---

## 8. GET `/v1/telemetry/state` & POST `/v1/telemetry/state`

### Purpose
Inspects or toggles the in-memory simulated hardware state of the Galaxy device simulator.

### GET Response (`200 OK`)
```json
{
  "wifi_enabled": true,
  "internet_connected": true,
  "screen_responsive": true,
  "battery_level": 82,
  "bluetooth_enabled": false
}
```

### POST Request Body
```json
{
  "bluetooth_enabled": true
}
```

### POST Response (`200 OK`)
```json
{
  "status": "updated",
  "current_state": {
    "wifi_enabled": true,
    "internet_connected": true,
    "screen_responsive": true,
    "battery_level": 82,
    "bluetooth_enabled": true
  }
}
```
