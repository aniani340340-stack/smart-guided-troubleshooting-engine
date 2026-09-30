import React from 'react';
import { DeviceTelemetryState } from '../../types/troubleshooting';

interface DeviceStatusProps {
  telemetry: DeviceTelemetryState | null;
  onToggle: (key: string) => void;
}

export const DeviceStatus: React.FC<DeviceStatusProps> = ({ telemetry, onToggle }) => {
  if (!telemetry) return null;

  return (
    <div className="simulated-device-status-card">
      <div className="device-status-header">
        <div className="status-title-group">
          <span className="telemetry-icon">📡</span>
          <div className="status-title-stack">
            <span className="status-main-title">SIMULATED DEVICE STATE</span>
            <span className="simulation-subtitle-demo">Demo telemetry • No physical device connection</span>
          </div>
        </div>
      </div>

      <p className="simulation-disclaimer-note">
        Simulated telemetry bindings for live diagnostic verification demonstration. Web application does not connect to physical Samsung hardware sensors.
      </p>

      <div className="telemetry-grid-list">
        {/* Wi-Fi */}
        <div
          className="telemetry-toggle-row"
          onClick={() => onToggle('wifi_enabled')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onToggle('wifi_enabled'); }}
          title="Click to toggle simulated Wi-Fi adapter state"
        >
          <div className="telemetry-label-col">
            <span className="telemetry-name">Wi-Fi</span>
            <span className="telemetry-sub">Adapter radio</span>
          </div>
          <span className={`telemetry-status-pill ${telemetry.wifi_enabled ? 'is-connected' : 'is-disconnected'}`}>
            <span className="state-dot" />
            <span>{telemetry.wifi_enabled ? 'Connected' : 'Disconnected'}</span>
          </span>
        </div>

        {/* Internet */}
        <div
          className="telemetry-toggle-row"
          onClick={() => onToggle('internet_connected')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onToggle('internet_connected'); }}
          title="Click to toggle simulated Internet route state"
        >
          <div className="telemetry-label-col">
            <span className="telemetry-name">Internet</span>
            <span className="telemetry-sub">DNS & Gateway</span>
          </div>
          <span className={`telemetry-status-pill ${telemetry.internet_connected ? 'is-connected' : 'is-disconnected'}`}>
            <span className="state-dot" />
            <span>{telemetry.internet_connected ? 'Available' : 'No Internet'}</span>
          </span>
        </div>

        {/* Battery */}
        <div
          className="telemetry-toggle-row"
          onClick={() => onToggle('battery_level')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onToggle('battery_level'); }}
          title="Click to cycle battery percentage (85% / 20%)"
        >
          <div className="telemetry-label-col">
            <span className="telemetry-name">Battery</span>
            <span className="telemetry-sub">{telemetry.battery_charging ? 'Fast Charging' : 'Discharging'}</span>
          </div>
          <span className="telemetry-status-pill metric-pill">
            <span>🔋 {telemetry.battery_level}%</span>
          </span>
        </div>

        {/* Bluetooth */}
        <div
          className="telemetry-toggle-row"
          onClick={() => onToggle('bluetooth_enabled')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onToggle('bluetooth_enabled'); }}
          title="Click to toggle simulated Bluetooth adapter state"
        >
          <div className="telemetry-label-col">
            <span className="telemetry-name">Bluetooth</span>
            <span className="telemetry-sub">BLE Subsystem</span>
          </div>
          <span className={`telemetry-status-pill ${telemetry.bluetooth_enabled ? 'is-connected' : 'is-disconnected'}`}>
            <span className="state-dot" />
            <span>{telemetry.bluetooth_enabled ? 'On' : 'Off'}</span>
          </span>
        </div>
      </div>
    </div>
  );
};
