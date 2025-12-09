import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

/**
 * Friendly display names for common models.
 * Maps model identifiers to shorter, readable names for tabs.
 */
const MODEL_DISPLAY_NAMES = {
  // OpenAI models
  'gpt-4.1': 'GPT-4.1',
  'gpt-4': 'GPT-4',
  'gpt-4o': 'GPT-4o',
  'gpt-4o-mini': 'GPT-4o Mini',
  'gpt-4-turbo': 'GPT-4 Turbo',
  'gpt-3.5-turbo': 'GPT-3.5',
  'o1': 'o1',
  'o1-mini': 'o1 Mini',
  'o1-preview': 'o1 Preview',
  'o3-mini': 'o3 Mini',
  // Anthropic models
  'claude-3-5-sonnet': 'Claude 3.5 Sonnet',
  'claude-3-5-sonnet-20241022': 'Claude 3.5 Sonnet',
  'claude-3-5-haiku': 'Claude 3.5 Haiku',
  'claude-3-5-haiku-20241022': 'Claude 3.5 Haiku',
  'claude-3-opus': 'Claude 3 Opus',
  'claude-3-opus-20240229': 'Claude 3 Opus',
  'claude-3-sonnet': 'Claude 3 Sonnet',
  'claude-3-haiku': 'Claude 3 Haiku',
  'claude-sonnet-4-20250514': 'Claude Sonnet 4',
  'claude-opus-4-20250514': 'Claude Opus 4',
  // Google models
  'gemini-2.0-pro': 'Gemini 2.0 Pro',
  'gemini-2.0-flash': 'Gemini 2.0 Flash',
  'gemini-1.5-pro': 'Gemini 1.5 Pro',
  'gemini-1.5-flash': 'Gemini 1.5 Flash',
  'gemini-pro': 'Gemini Pro',
  // xAI models
  'grok-2': 'Grok 2',
  'grok-3': 'Grok 3',
  'grok-3-mini': 'Grok 3 Mini',
  // Mistral models
  'mistral-large': 'Mistral Large',
  'mistral-medium': 'Mistral Medium',
  'mistral-small': 'Mistral Small',
  // Perplexity models
  'sonar-pro': 'Sonar Pro',
  'sonar': 'Sonar',
  // DeepSeek models
  'deepseek-chat': 'DeepSeek Chat',
  'deepseek-reasoner': 'DeepSeek R1',
};

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

/**
 * Get a friendly display name for a model, suitable for tab labels.
 * Falls back to the short model name if no friendly name is defined.
 */
function getDisplayName(model) {
  const shortName = getShortModelName(model);
  return MODEL_DISPLAY_NAMES[shortName] || shortName;
}

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, model]) => {
    const modelShortName = getShortModelName(model);
    result = result.replace(new RegExp(label, 'g'), `**${modelShortName}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: Peer Rankings</h3>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {rankings.map((rank, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
            title={rank.model}
          >
            {getDisplayName(rank.model)}'s Ranking
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="ranking-model">
          {rankings[activeTab].model}
        </div>
        <div className="ranking-content markdown-content">
          <ReactMarkdown>
            {deAnonymizeText(rankings[activeTab].ranking, labelToModel)}
          </ReactMarkdown>
        </div>

        {rankings[activeTab].parsed_ranking &&
         rankings[activeTab].parsed_ranking.length > 0 && (
          <div className="parsed-ranking">
            <strong>Extracted Ranking:</strong>
            <ol>
              {rankings[activeTab].parsed_ranking.map((label, i) => (
                <li key={i}>
                  {labelToModel && labelToModel[label]
                    ? getShortModelName(labelToModel[label])
                    : label}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item" title={agg.model}>
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  {getDisplayName(agg.model)}
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
