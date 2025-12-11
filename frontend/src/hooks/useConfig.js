/**
 * Hook for fetching and caching model configuration data.
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';

/**
 * Custom hook to fetch and manage model configuration.
 * Fetches providers, presets, and current config on mount.
 * Provides helpers for model selection state management.
 */
export function useConfig() {
  const [providers, setProviders] = useState([]);
  const [presets, setPresets] = useState([]);
  const [currentConfig, setCurrentConfig] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all config data on mount
  useEffect(() => {
    const fetchConfig = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [providersData, presetsData, currentData] = await Promise.all([
          api.getProviders(),
          api.getPresets(),
          api.getCurrentConfig(),
        ]);
        setProviders(providersData);
        setPresets(presetsData);
        setCurrentConfig(currentData);
      } catch (err) {
        console.error('Failed to fetch config:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfig();
  }, []);

  // Get all models as a flat list
  const getAllModels = useCallback(() => {
    return providers.flatMap((provider) => provider.models);
  }, [providers]);

  // Get models for a specific provider
  const getModelsForProvider = useCallback(
    (providerId) => {
      const provider = providers.find((p) => p.id === providerId);
      return provider ? provider.models : [];
    },
    [providers]
  );

  // Get a preset by name
  const getPreset = useCallback(
    (presetName) => {
      return presets.find((p) => p.name === presetName);
    },
    [presets]
  );

  // Resolve a preset to a model config object
  const resolvePreset = useCallback(
    (presetName) => {
      const preset = getPreset(presetName);
      if (!preset) return null;
      return {
        preset: presetName,
        council_models: preset.council_models,
        chairman_model: preset.chairman_model,
        research_model: preset.research_model,
      };
    },
    [getPreset]
  );

  return {
    providers,
    presets,
    currentConfig,
    isLoading,
    error,
    getAllModels,
    getModelsForProvider,
    getPreset,
    resolvePreset,
  };
}

/**
 * Hook for managing model selection state for conversation creation.
 */
export function useModelSelection(currentConfig) {
  // Selection mode: 'default' (use global config), 'preset', or 'custom'
  const [selectionMode, setSelectionMode] = useState('default');

  // Selected preset name (when mode is 'preset')
  const [selectedPreset, setSelectedPreset] = useState(null);

  // Custom model selections (when mode is 'custom')
  const [councilModels, setCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState(null);
  const [researchModel, setResearchModel] = useState(null);

  // Initialize custom selections from current config
  useEffect(() => {
    if (currentConfig) {
      setCouncilModels(currentConfig.council_models || []);
      setChairmanModel(currentConfig.chairman_model || null);
      setResearchModel(currentConfig.research_model || null);
    }
  }, [currentConfig]);

  // Switch to preset mode
  const selectPreset = useCallback((presetName) => {
    setSelectionMode('preset');
    setSelectedPreset(presetName);
  }, []);

  // Switch to custom mode
  const switchToCustom = useCallback(() => {
    setSelectionMode('custom');
    setSelectedPreset(null);
  }, []);

  // Switch to default mode (use global config)
  const useDefault = useCallback(() => {
    setSelectionMode('default');
    setSelectedPreset(null);
  }, []);

  // Toggle a model in the council selection
  const toggleCouncilModel = useCallback((modelId) => {
    setCouncilModels((prev) => {
      if (prev.includes(modelId)) {
        return prev.filter((id) => id !== modelId);
      } else {
        return [...prev, modelId];
      }
    });
    setSelectionMode('custom');
    setSelectedPreset(null);
  }, []);

  // Set chairman model
  const selectChairman = useCallback((modelId) => {
    setChairmanModel(modelId);
    setSelectionMode('custom');
    setSelectedPreset(null);
  }, []);

  // Set research model
  const selectResearch = useCallback((modelId) => {
    setResearchModel(modelId);
    setSelectionMode('custom');
    setSelectedPreset(null);
  }, []);

  // Get the model config to send with conversation creation
  const getModelConfig = useCallback(() => {
    if (selectionMode === 'default') {
      return null; // Use global defaults
    }

    if (selectionMode === 'preset') {
      return { preset: selectedPreset };
    }

    // Custom mode - only include non-empty selections
    const config = {};
    if (councilModels.length > 0) {
      config.council_models = councilModels;
    }
    if (chairmanModel) {
      config.chairman_model = chairmanModel;
    }
    if (researchModel) {
      config.research_model = researchModel;
    }

    return Object.keys(config).length > 0 ? config : null;
  }, [selectionMode, selectedPreset, councilModels, chairmanModel, researchModel]);

  // Reset to defaults
  const reset = useCallback(() => {
    setSelectionMode('default');
    setSelectedPreset(null);
    if (currentConfig) {
      setCouncilModels(currentConfig.council_models || []);
      setChairmanModel(currentConfig.chairman_model || null);
      setResearchModel(currentConfig.research_model || null);
    }
  }, [currentConfig]);

  return {
    selectionMode,
    selectedPreset,
    councilModels,
    chairmanModel,
    researchModel,
    selectPreset,
    switchToCustom,
    useDefault,
    toggleCouncilModel,
    selectChairman,
    selectResearch,
    getModelConfig,
    reset,
  };
}

export default useConfig;
