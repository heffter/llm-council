import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

/**
 * Extract short model name from provider:model or provider/model format.
 * Examples:
 *   "openai:gpt-4.1" -> "gpt-4.1"
 *   "anthropic:claude-3-5-sonnet" -> "claude-3-5-sonnet"
 *   "openrouter/some-model" -> "some-model"
 *   "plain-model-name" -> "plain-model-name"
 */
function getShortModelName(model) {
  if (!model) return model;
  // Try colon first (new provider:model format), then slash (legacy format)
  if (model.includes(':')) {
    return model.split(':')[1] || model;
  }
  if (model.includes('/')) {
    return model.split('/')[1] || model;
  }
  return model;
}

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {getShortModelName(resp.model)}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-name">{responses[activeTab].model}</div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
