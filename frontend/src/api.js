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
