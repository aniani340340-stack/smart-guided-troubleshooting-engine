import { useState, useEffect, useCallback } from 'react';
import {
  TroubleshootingSessionState,
  ValidationResult,
  DeviceTelemetryState
} from '../types/troubleshooting';
import * as api from '../services/api';

export function useTroubleshootingSession() {
  const [session, setSession] = useState<TroubleshootingSessionState | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<DeviceTelemetryState | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [validationLoading, setValidationLoading] = useState<boolean>(false);

  // Fetch initial telemetry state
  useEffect(() => {
    api.getTelemetryState()
      .then(setTelemetry)
      .catch((err) => console.error('Failed to load telemetry state', err));
  }, []);

  const start = useCallback(async (
    query: string,
    deviceModel?: string,
    osVersion?: string,
    imageData?: string | null,
    errorCode?: string | null
  ) => {
    setLoading(true);
    setError(null);
    setValidationResult(null);
    try {
      const newSession = await api.startSession(query, deviceModel, osVersion, imageData, errorCode);
      setSession(newSession);
      // Refresh telemetry state
      const tState = await api.getTelemetryState();
      setTelemetry(tState);
    } catch (err: any) {
      setError(err.message || 'Failed to start diagnostic session');
    } finally {
      setLoading(false);
    }
  }, []);

  const feedback = useCallback(async (result: 'passed' | 'failed' | 'skipped', details?: Record<string, any>, intentId?: string) => {
    if (!session?.session_id) return;
    setLoading(true);
    setError(null);
    setValidationResult(null);
    try {
      const updated = await api.submitFeedback(session.session_id, result, details, intentId);
      setSession(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to submit step feedback');
    } finally {
      setLoading(false);
    }
  }, [session?.session_id]);

  const switchIntent = useCallback(async (intentId: string) => {
    if (!session?.session_id) return;
    setLoading(true);
    setError(null);
    setValidationResult(null);
    try {
      const updated = await api.switchIntent(session.session_id, intentId);
      setSession(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to switch troubleshooting intent');
    } finally {
      setLoading(false);
    }
  }, [session?.session_id]);

  const validateCurrentStep = useCallback(async () => {
    if (!session?.session_id) return;
    setValidationLoading(true);
    try {
      const result = await api.simulateValidation(session.session_id, telemetry || undefined);
      setValidationResult(result);
    } catch (err: any) {
      setError(err.message || 'Validation simulation failed');
    } finally {
      setValidationLoading(false);
    }
  }, [session?.session_id, telemetry]);

  const toggleTelemetry = useCallback(async (key: string) => {
    if (!telemetry) return;
    const currentVal = telemetry[key];
    let nextVal: any;
    if (typeof currentVal === 'boolean') {
      nextVal = !currentVal;
    } else if (typeof currentVal === 'number') {
      nextVal = currentVal > 50 ? 20 : 85;
    } else {
      nextVal = currentVal;
    }

    const updatedTelemetry = { ...telemetry, [key]: nextVal };
    setTelemetry(updatedTelemetry);

    try {
      await api.updateTelemetryState(updatedTelemetry);
    } catch (err) {
      console.error('Failed to sync telemetry state', err);
    }
  }, [telemetry]);

  const reset = useCallback(() => {
    setSession(null);
    setError(null);
    setValidationResult(null);
  }, []);

  return {
    session,
    loading,
    error,
    telemetry,
    validationResult,
    validationLoading,
    start,
    feedback,
    switchIntent,
    validateCurrentStep,
    toggleTelemetry,
    reset,
  };
}
