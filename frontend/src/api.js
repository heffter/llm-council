/**
 * API client for the LLM Council backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   * @param {Object} modelConfig - Optional model configuration
   * @param {string} modelConfig.preset - Preset name (fast, balanced, comprehensive)
   * @param {string[]} modelConfig.council_models - List of provider:model strings
   * @param {string} modelConfig.chairman_model - Chairman model provider:model string
   * @param {string} modelConfig.research_model - Research model provider:model string
   */
  async createConversation(modelConfig = null) {
    const body = modelConfig ? { model_config_data: modelConfig } : {};
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get all available models grouped by provider.
   */
  async getModels() {
    const response = await fetch(`${API_BASE}/api/config/models`);
    if (!response.ok) {
      throw new Error('Failed to get models');
    }
    return response.json();
  },

  /**
   * Get all providers with their models.
   */
  async getProviders() {
    const response = await fetch(`${API_BASE}/api/config/providers`);
    if (!response.ok) {
      throw new Error('Failed to get providers');
    }
    return response.json();
  },

  /**
   * Get available presets.
   */
  async getPresets() {
    const response = await fetch(`${API_BASE}/api/config/presets`);
    if (!response.ok) {
      throw new Error('Failed to get presets');
    }
    return response.json();
  },

  /**
   * Get current model configuration.
   */
  async getCurrentConfig() {
    const response = await fetch(`${API_BASE}/api/config/current`);
    if (!response.ok) {
      throw new Error('Failed to get current config');
    }
    return response.json();
  },

  /**
   * Get council configuration with member metadata.
   */
  async getCouncilConfig() {
    const response = await fetch(`${API_BASE}/api/config/council`);
    if (!response.ok) {
      throw new Error('Failed to get council config');
    }
    return response.json();
  },

  /**
   * Validate a council configuration.
   * @param {Object} config - Council configuration to validate
   * @param {string[]} config.council_models - List of council model IDs
   * @param {string} config.chairman_model - Optional chairman model ID
   * @param {string} config.research_model - Optional research model ID
   * @returns {Promise<{valid: boolean, errors: string[], warnings: string[]}>}
   */
  async validateCouncil(config) {
    const response = await fetch(`${API_BASE}/api/config/council/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      throw new Error('Failed to validate council');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  // ==========================================================================
  // Export/Import Methods
  // ==========================================================================

  /**
   * Get export/import capability information.
   */
  async getExportInfo() {
    const response = await fetch(`${API_BASE}/api/conversations/export/info`);
    if (!response.ok) {
      throw new Error('Failed to get export info');
    }
    return response.json();
  },

  /**
   * Export a single conversation.
   * @param {string} conversationId - The conversation ID
   * @param {string} format - Export format: 'json' or 'markdown'
   * @returns {Promise<{blob: Blob, filename: string}>}
   */
  async exportConversation(conversationId, format = 'json') {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/export?format=${format}`
    );
    if (!response.ok) {
      throw new Error('Failed to export conversation');
    }

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `conversation.${format === 'markdown' ? 'md' : format}`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="([^"]+)"/);
      if (match) {
        filename = match[1];
      }
    }

    const blob = await response.blob();
    return { blob, filename };
  },

  /**
   * Export multiple conversations as a ZIP archive.
   * @param {string[]} conversationIds - Optional list of conversation IDs (all if not provided)
   * @param {boolean} includeMarkdown - Include Markdown versions in ZIP
   * @returns {Promise<{blob: Blob, filename: string}>}
   */
  async exportCollection(conversationIds = null, includeMarkdown = true) {
    const params = new URLSearchParams();
    if (conversationIds?.length) {
      params.append('ids', conversationIds.join(','));
    }
    params.append('include_markdown', includeMarkdown);

    const response = await fetch(
      `${API_BASE}/api/conversations/export/collection?${params}`
    );
    if (!response.ok) {
      throw new Error('Failed to export collection');
    }

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'llm-council-export.zip';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="([^"]+)"/);
      if (match) {
        filename = match[1];
      }
    }

    const blob = await response.blob();
    return { blob, filename };
  },

  /**
   * Validate a file for import without importing.
   * @param {File} file - The file to validate
   * @returns {Promise<{valid: boolean, errors: string[], warnings: string[]}>}
   */
  async validateImport(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${API_BASE}/api/conversations/import/validate`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) {
      throw new Error('Failed to validate import');
    }
    return response.json();
  },

  /**
   * Import conversations from a file.
   * @param {File} file - The file to import (JSON or ZIP)
   * @param {boolean} preserveIds - Try to preserve original conversation IDs
   * @returns {Promise<{success: boolean, conversation_ids: string[], warnings: string[], errors: string[]}>}
   */
  async importConversations(file, preserveIds = false) {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    params.append('preserve_ids', preserveIds);

    const response = await fetch(
      `${API_BASE}/api/conversations/import?${params}`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) {
      throw new Error('Failed to import conversations');
    }
    return response.json();
  },

  // ==========================================================================
  // Message Methods
  // ==========================================================================

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
