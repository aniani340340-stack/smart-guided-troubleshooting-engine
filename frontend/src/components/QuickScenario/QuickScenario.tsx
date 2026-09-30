import React from 'react';

export interface QuickScenarioItem {
  id: string;
  icon: string;
  domain: string;
  title: string;
  description: string;
  prompt: string;
  defaultDevice: string;
  defaultOs: string;
}

export const SCENARIO_ITEMS: QuickScenarioItem[] = [
  {
    id: 'wifi',
    icon: '📶',
    domain: 'NETWORK',
    title: 'Wi-Fi Connectivity',
    description: 'Keeps disconnecting and cannot load web pages',
    prompt: 'My Galaxy S22 Wi-Fi keeps disconnecting and cannot load web pages',
    defaultDevice: 'Galaxy S22',
    defaultOs: 'One UI 6.1 (Android 14)',
  },
  {
    id: 'display',
    icon: '📱',
    domain: 'DISPLAY',
    title: 'Black Screen / Blank',
    description: 'Screen turns black but phone vibrates on incoming calls',
    prompt: 'My Galaxy S22 screen turns completely blank or white and no text appears',
    defaultDevice: 'Galaxy S22',
    defaultOs: 'One UI 6.1 (Android 14)',
  },
  {
    id: 'touch',
    icon: '👆',
    domain: 'NAVIGATION',
    title: 'Touch & Gestures',
    description: 'Swipe navigation bar misbehaving or unresponsive',
    prompt: 'My phone swipe navigation gestures are misbehaving and go the wrong way',
    defaultDevice: 'Galaxy S24 Ultra',
    defaultOs: 'One UI 6.1.1 (Android 14)',
  },
  {
    id: 'battery',
    icon: '🔋',
    domain: 'BATTERY',
    title: 'Battery & Charging',
    description: 'Rapid drain or phone does not initiate fast charge',
    prompt: 'Galaxy S22 battery draining fast overnight and charging is slow',
    defaultDevice: 'Galaxy S22',
    defaultOs: 'One UI 6.1 (Android 14)',
  },
  {
    id: 'bluetooth',
    icon: '🎧',
    domain: 'BLUETOOTH',
    title: 'Bluetooth Pairing',
    description: 'Buds or wearable fails to pair or keeps dropping',
    prompt: 'Galaxy Buds2 Pro bluetooth pairing fails with Galaxy S23',
    defaultDevice: 'Galaxy Buds2 Pro',
    defaultOs: 'Galaxy Wearable Core 2.2',
  },
  {
    id: 'multi_intent',
    icon: '⚡',
    domain: 'MULTI-INTENT',
    title: 'Dual Issue (Wi-Fi & Buds)',
    description: 'Wi-Fi disconnects and Bluetooth earbuds fail to connect',
    prompt: 'My Wi-Fi keeps disconnecting and my Bluetooth earbuds won\'t connect',
    defaultDevice: 'Galaxy S22',
    defaultOs: 'One UI 6.1 (Android 14)',
  },
];

interface QuickScenarioProps {
  onSelectScenario: (scenario: QuickScenarioItem) => void;
  selectedId?: string | null;
  disabled?: boolean;
}

export const QuickScenario: React.FC<QuickScenarioProps> = ({
  onSelectScenario,
  selectedId,
  disabled,
}) => {
  return (
    <section className="quick-scenarios-section" aria-labelledby="quick-diagnostics-heading">
      <div className="section-header-row">
        <h2 id="quick-diagnostics-heading" className="quick-scenarios-title">
          QUICK DIAGNOSTICS
        </h2>
        <span className="section-hint">Select a common scenario to populate verified troubleshooting flow</span>
      </div>

      <div className="scenarios-grid">
        {SCENARIO_ITEMS.map((item) => {
          const isSelected = selectedId === item.id;
          return (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              className={`scenario-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectScenario(item)}
              aria-pressed={isSelected}
            >
              <div className="card-top">
                <span className="scenario-icon" role="img" aria-label={item.title}>
                  {item.icon}
                </span>
                <span className="scenario-domain-tag">{item.domain}</span>
              </div>
              <h3 className="scenario-title">{item.title}</h3>
              <p className="scenario-desc">{item.description}</p>
              <div className="scenario-footer-arrow">
                <span>Start Flow</span>
                <span className="arrow-icon">→</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};
