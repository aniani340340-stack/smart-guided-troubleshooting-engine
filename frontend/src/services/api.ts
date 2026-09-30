import {
  TroubleshootingSessionState,
  ValidationResult,
  DeviceTelemetryState
} from '../types/troubleshooting';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function startSession(
  query: string,
  deviceModel?: string,
  osVersion?: string,
  imageData?: string | null,
  errorCode?: string | null
): Promise<TroubleshootingSessionState> {
  const response = await fetch(`${API_BASE}/v1/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      device_model: deviceModel,
      os_version: osVersion,
      image_data: imageData || undefined,
      error_code: errorCode || undefined,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to start session (${response.status}): ${errorText}`);
  }

  return response.json();
}

export async function getSession(sessionId: string): Promise<TroubleshootingSessionState> {
  const response = await fetch(`${API_BASE}/v1/session/${sessionId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch session (${response.status})`);
  }
  return response.json();
}

export async function submitFeedback(
  sessionId: string,
  result: 'passed' | 'failed' | 'skipped',
  details?: Record<string, any>,
  intentId?: string
): Promise<TroubleshootingSessionState> {
  const response = await fetch(`${API_BASE}/v1/session/${sessionId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result, details, intent_id: intentId }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to submit feedback (${response.status}): ${errorText}`);
  }

  return response.json();
}

export async function switchIntent(
  sessionId: string,
  intentId: string
): Promise<TroubleshootingSessionState> {
  const response = await fetch(`${API_BASE}/v1/session/${sessionId}/switch-intent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ intent_id: intentId }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to switch intent (${response.status}): ${errorText}`);
  }

  return response.json();
}

export async function simulateValidation(
  sessionId: string,
  stateOverrides?: Record<string, any>
): Promise<ValidationResult> {
  const response = await fetch(`${API_BASE}/v1/session/${sessionId}/simulate-validation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state_overrides: stateOverrides }),
  });

  if (!response.ok) {
    throw new Error(`Simulation check failed (${response.status})`);
  }

  return response.json();
}

export async function getTelemetryState(): Promise<DeviceTelemetryState> {
  const response = await fetch(`${API_BASE}/v1/telemetry/state`);
  if (!response.ok) {
    throw new Error(`Failed to fetch telemetry state (${response.status})`);
  }
  return response.json();
}

export async function updateTelemetryState(
  state: Record<string, any>
): Promise<{ status: string; current_state: DeviceTelemetryState }> {
  const response = await fetch(`${API_BASE}/v1/telemetry/state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  });

  if (!response.ok) {
    throw new Error(`Failed to update telemetry state (${response.status})`);
  }

  return response.json();
}
