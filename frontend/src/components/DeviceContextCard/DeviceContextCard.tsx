import React, { useState } from 'react';

interface DeviceContextCardProps {
  deviceModel: string;
  osVersion?: string;
  deviceType?: string;
  accessory?: string | null;
  onDeviceChange?: (model: string, os: string) => void;
}

const SUPPORTED_DEVICES = [
  { model: 'Galaxy S22', os: 'One UI 6.1 (Android 14)', type: 'Flagship' },
  { model: 'Galaxy S24 Ultra', os: 'One UI 6.1.1 (Android 14)', type: 'Flagship' },
  { model: 'Galaxy S23', os: 'One UI 6.1 (Android 14)', type: 'Flagship' },
  { model: 'Galaxy Z Fold 6', os: 'One UI 6.1.1 (Foldable)', type: 'Foldable' },
  { model: 'Galaxy Z Flip 6', os: 'One UI 6.1.1 (Flip)', type: 'Foldable' },
  { model: 'Galaxy A55 5G', os: 'One UI 6.1 (Android 14)', type: 'Mid-range' },
  { model: 'Galaxy Buds2 Pro', os: 'Galaxy Wearable Core 2.2', type: 'Audio' },
];

export const DeviceContextCard: React.FC<DeviceContextCardProps> = ({
  deviceModel,
  osVersion,
  deviceType,
  accessory,
  onDeviceChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Derive device icon
  let deviceIcon = '📱';
  const dmLower = (deviceModel || '').toLowerCase();
  if (dmLower.includes('fold') || dmLower.includes('flip')) deviceIcon = '📱';
  else if (dmLower.includes('tab')) deviceIcon = '📟';
  else if (dmLower.includes('watch')) deviceIcon = '⌚';

  // Format type display
  const typeDisplay = deviceType 
    ? (deviceType.charAt(0).toUpperCase() + deviceType.slice(1)) 
    : 'Phone';

  return (
    <div className="device-context-card">
      <div className="context-card-header">
        <span className="context-label">DEVICE CONTEXT</span>
        {onDeviceChange && (
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="btn-change-device"
            aria-expanded={isOpen}
          >
            {isOpen ? 'Close' : 'Change device'}
          </button>
        )}
      </div>

      <div className="current-device-display">
        <div className="device-avatar">{deviceIcon}</div>
        <div className="device-info">
          <span className="device-name">{deviceModel}</span>
          <span className="device-os">
            {typeDisplay} {osVersion ? `· ${osVersion}` : ''}
          </span>
        </div>
      </div>

      {accessory && (
        <div className="connected-accessory-box">
          <div className="accessory-header-line">
            <span className="accessory-badge-title">CONNECTED ACCESSORY</span>
          </div>
          <div className="accessory-details">
            <span className="accessory-icon" aria-hidden="true">
              {accessory.toLowerCase().includes('watch') ? '⌚' : '🎧'}
            </span>
            <div className="accessory-meta">
              <span className="accessory-name">{accessory}</span>
              <span className="accessory-status-tag">Connected &amp; Active</span>
            </div>
          </div>
        </div>
      )}

      {isOpen && onDeviceChange && (
        <div className="device-selector-dropdown">
          <span className="selector-title">Select Target Galaxy Hardware</span>
          <div className="device-list">
            {SUPPORTED_DEVICES.map((d) => (
              <button
                key={d.model}
                type="button"
                className={`device-option-btn ${d.model === deviceModel ? 'active' : ''}`}
                onClick={() => {
                  onDeviceChange(d.model, d.os);
                  setIsOpen(false);
                }}
              >
                <div className="opt-left">
                  <span className="opt-model">{d.model}</span>
                  <span className="opt-os">{d.os}</span>
                </div>
                <span className="opt-badge">{d.type}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
