/**
 * ModelSelector - A component for selecting model configurations.
 * Shows preset options with cost/speed badges and allows custom selection.
 */

import { useState } from 'react';
import { useConfig, useModelSelection } from '../hooks/useConfig';
import './ModelSelector.css';

/**
 * Badge component for cost/speed tiers
 */
function TierBadge({ type, value }) {
  const colors = {
    cost: {
      low: '#22c55e',
      medium: '#f59e0b',
      high: '#ef4444',
    },
    speed: {
      fast: '#22c55e',
      medium: '#f59e0b',
      slow: '#ef4444',
    },
  };

  const labels = {
    cost: {
      low: '$',
      medium: '$$',
      high: '$$$',
    },
    speed: {
      fast: 'Fast',
      medium: 'Med',
      slow: 'Slow',
    },
  };

  const color = colors[type]?.[value] || '#999';
  const label = labels[type]?.[value] || value;

  return (
    <span
      className="tier-badge"
      style={{ backgroundColor: color }}
      title={`${type}: ${value}`}
    >
      {label}
    </span>
  );
}

/**
 * Preset card component
 */
function PresetCard({ preset, isSelected, onSelect }) {
  return (
    <div
      className={`preset-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(preset.name)}
    >
      <div className="preset-header">
        <h4>{preset.display_name}</h4>
        {isSelected && <span className="check-mark">&#10003;</span>}
      </div>
      <p className="preset-description">{preset.description}</p>
      <div className="preset-models">
        <div className="preset-model-group">
          <span className="model-role">Council:</span>
          <span className="model-count">{preset.council_models.length} models</span>
        </div>
        <div className="preset-model-group">
          <span className="model-role">Chairman:</span>
          <span className="model-name">{preset.chairman_model.split(':')[1]}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Model checkbox for custom selection
 */
function ModelCheckbox({ model, isSelected, onToggle, role }) {
  return (
    <label className="model-checkbox">
      <input
        type={role === 'council' ? 'checkbox' : 'radio'}
        name={role}
        checked={isSelected}
        onChange={() => onToggle(model.full_id)}
      />
      <div className="model-info">
        <span className="model-display-name">{model.display_name}</span>
        <div className="model-badges">
          <TierBadge type="cost" value={model.cost_tier} />
          <TierBadge type="speed" value={model.speed_tier} />
        </div>
      </div>
    </label>
  );
}

/**
 * Main ModelSelector component
 */
export default function ModelSelector({ isOpen, onClose, onSelect }) {
  const { providers, presets, currentConfig, isLoading, error } = useConfig();
  const modelSelection = useModelSelection(currentConfig);
  const [showAdvanced, setShowAdvanced] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = () => {
    const config = modelSelection.getModelConfig();
    onSelect(config);
    onClose();
  };

  const handleUseDefault = () => {
    modelSelection.useDefault();
    onSelect(null);
    onClose();
  };

  if (isLoading) {
    return (
      <div className="modal-overlay">
        <div className="model-selector-modal">
          <div className="modal-loading">Loading configuration...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="modal-overlay">
        <div className="model-selector-modal">
          <div className="modal-error">
            <p>Failed to load configuration: {error}</p>
            <button onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="model-selector-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Select Model Configuration</h2>
          <button className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-content">
          {/* Preset Selection */}
          <div className="preset-section">
            <h3>Presets</h3>
            <div className="preset-grid">
              {presets.map((preset) => (
                <PresetCard
                  key={preset.name}
                  preset={preset}
                  isSelected={
                    modelSelection.selectionMode === 'preset' &&
                    modelSelection.selectedPreset === preset.name
                  }
                  onSelect={modelSelection.selectPreset}
                />
              ))}
            </div>
          </div>

          {/* Advanced/Custom Selection Toggle */}
          <div className="advanced-toggle">
            <button
              className="toggle-btn"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? 'Hide' : 'Show'} Advanced Options
            </button>
          </div>

          {/* Advanced Custom Selection */}
          {showAdvanced && (
            <div className="advanced-section">
              <h3>Custom Model Selection</h3>

              {/* Council Models */}
              <div className="model-group">
                <h4>Council Models (select multiple)</h4>
                <div className="model-list">
                  {providers.map((provider) => (
                    <div key={provider.id} className="provider-group">
                      <div className="provider-name">{provider.display_name}</div>
                      {provider.models.map((model) => (
                        <ModelCheckbox
                          key={model.full_id}
                          model={model}
                          role="council"
                          isSelected={modelSelection.councilModels.includes(model.full_id)}
                          onToggle={modelSelection.toggleCouncilModel}
                        />
                      ))}
                    </div>
                  ))}
                </div>
              </div>

              {/* Chairman Model */}
              <div className="model-group">
                <h4>Chairman Model</h4>
                <div className="model-list">
                  {providers.map((provider) => (
                    <div key={provider.id} className="provider-group">
                      <div className="provider-name">{provider.display_name}</div>
                      {provider.models.map((model) => (
                        <ModelCheckbox
                          key={model.full_id}
                          model={model}
                          role="chairman"
                          isSelected={modelSelection.chairmanModel === model.full_id}
                          onToggle={modelSelection.selectChairman}
                        />
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={handleUseDefault}>
            Use Default
          </button>
          <button className="btn-primary" onClick={handleConfirm}>
            Create Conversation
          </button>
        </div>
      </div>
    </div>
  );
}
