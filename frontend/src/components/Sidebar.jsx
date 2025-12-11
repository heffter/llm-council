import { useState } from 'react';
import { api } from '../api';
import './Sidebar.css';

/**
 * Helper to trigger file download from blob.
 */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onImport,
}) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExportAll = async () => {
    if (conversations.length === 0) return;

    setIsExporting(true);
    try {
      const { blob, filename } = await api.exportCollection(null, true);
      downloadBlob(blob, filename);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>LLM Council</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
        <div className="sidebar-actions">
          <button
            className="sidebar-action-btn"
            onClick={onImport}
            title="Import conversations"
          >
            Import
          </button>
          <button
            className="sidebar-action-btn"
            onClick={handleExportAll}
            disabled={isExporting || conversations.length === 0}
            title="Export all conversations"
          >
            {isExporting ? 'Exporting...' : 'Export All'}
          </button>
        </div>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Conversation'}
              </div>
              <div className="conversation-meta">
                {conv.message_count} messages
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
