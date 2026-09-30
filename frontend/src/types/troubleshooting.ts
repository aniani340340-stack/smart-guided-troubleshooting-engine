export type SessionStatus = 'ACTIVE' | 'RESOLVED' | 'ESCALATED' | 'FAILED';

export type ActionCategory = 'auto' | 'manual' | 'critical';

export interface ActionableDeeplink {
  deeplink: string;
  description: string;
  message?: string;
  originalType?: string;
}

export interface ValidationDeeplink {
  deeplink: string;
  key: string;
  resultType?: string;
  condition?: string;
  value?: string;
}

export interface DiagnosticStep {
  step_id: string;
  action_name: string;
  instruction: string;
  why_this_step: string;
  expected_result: string;
  category: ActionCategory;
  actionable_deeplink?: ActionableDeeplink | null;
  validation_deeplink?: ValidationDeeplink | null;
  is_remedial?: boolean;
}

export interface SessionProgress {
  current: number;
  total: number;
}

export interface SessionDiagnosis {
  title: string;
  summary: string;
  canonical_key: string;
  confidence: number;
  domain?: string;
  matched_via?: string;
  ai_fallback_used?: boolean;
  image_analysis_used?: boolean;
  image_evidence_confidence?: number;
  error_codes?: string[];
}

export interface StepRecord {
  step_id: string;
  action_name: string;
  instruction: string;
  result: 'passed' | 'failed' | 'skipped';
  timestamp: number;
  details?: Record<string, any>;
}

export interface ResolutionSummary {
  resolved: boolean;
  problem: string;
  steps_completed: number;
  total_steps: number;
  elapsed_seconds: number;
  actions_taken: string[];
  notes?: string;
}

export interface EscalationSummary {
  escalated: boolean;
  title: string;
  message: string;
  recommended_action: string;
  reason?: string;
  diagnostic_report?: Record<string, any>;
}

export interface DeviceContextInfo {
  model?: string;
  device_model?: string;
  series?: string;
  device_type?: string;
  os_version?: string;
  one_ui_version?: string;
  android_version?: string;
  accessory?: string;
  confidence?: number;
  is_explicitly_extracted?: boolean;
}

export interface IntentState {
  id: string;
  domain: string;
  issue: string;
  title: string;
  canonical_key: string;
  confidence: number;
  status: 'ACTIVE' | 'PENDING' | 'RESOLVED' | 'ESCALATED';
  progress: SessionProgress;
  current_step?: DiagnosticStep | null;
  diagnosis?: SessionDiagnosis;
  completed_steps?: StepRecord[];
  failed_steps?: StepRecord[];
  resolved?: boolean;
  escalated?: boolean;
  resolution_summary?: ResolutionSummary | null;
  escalation_summary?: EscalationSummary | null;
  image_analysis_used?: boolean;
  image_evidence_confidence?: number;
  error_codes?: string[];
}

export interface TroubleshootingSessionState {
  session_id: string;
  status: SessionStatus;
  query: string;
  device_context?: DeviceContextInfo;
  accessory?: string | null;
  diagnosis?: SessionDiagnosis;
  current_step?: DiagnosticStep | null;
  progress?: SessionProgress;
  completed_steps?: StepRecord[];
  failed_steps?: StepRecord[];
  resolved?: boolean;
  escalated?: boolean;
  resolution_summary?: ResolutionSummary | null;
  escalation_summary?: EscalationSummary | null;
  is_multi_intent?: boolean;
  active_intent_id?: string;
  intents?: IntentState[];
  matched_via?: string;
  ai_fallback_used?: boolean;
  image_analysis_used?: boolean;
  image_evidence_confidence?: number;
  error_codes?: string[];
  created_at?: number;
  updated_at?: number;
}

export interface ValidationResult {
  is_valid: boolean;
  key: string;
  target_state_key?: string;
  condition?: string;
  expected_value?: any;
  actual_value?: any;
  message: string;
  simulated_telemetry: Record<string, any>;
}

export interface DeviceTelemetryState {
  wifi_enabled: boolean;
  internet_connected: boolean;
  screen_responsive: boolean;
  battery_level: number;
  battery_charging: boolean;
  bluetooth_enabled: boolean;
  double_tap_to_wake: boolean;
  auto_rotate: boolean;
  safe_mode: boolean;
  airplane_mode: boolean;
  show_charging_information: boolean;
  allow_find_phone: boolean;
  motion_smoothness: string;
  power_saving_mode: boolean;
  storage_cache_cleared: boolean;
  [key: string]: any;
}
