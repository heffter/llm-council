import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import './ExportMenu.css';

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

/**
 * Export menu for a single conversation.
 */
export default function ExportMenu({ conversationId, onExportStart, onExportEnd }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);
  const menuRef = useRef(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleExport = async (format) => {
    setIsExporting(true);
    setError(null);
    onExportStart?.();

    try {
      const { blob, filename } = await api.exportConversation(conversationId, format);
      downloadBlob(blob, filename);
      setIsOpen(false);
    } catch (err) {
      console.error('Export failed:', err);
      setError(`Export failed: ${err.message}`);
    } finally {
      setIsExporting(false);
      onExportEnd?.();
    }
  };

  return (
    <div className="export-menu" ref={menuRef}>
      <button
        className="export-menu-button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        title="Export conversation"
      >
        {isExporting ? 'Exporting...' : 'Export'}
      </button>

      {isOpen && (
        <div className="export-menu-dropdown">
          <button
            className="export-menu-item"
            onClick={() => handleExport('json')}
            disabled={isExporting}
          >
            <span className="export-format">JSON</span>
            <span className="export-description">Full data, re-importable</span>
          </button>
          <button
            className="export-menu-item"
            onClick={() => handleExport('markdown')}
            disabled={isExporting}
          >
            <span className="export-format">Markdown</span>
            <span className="export-description">Human-readable document</span>
          </button>

          {error && <div className="export-menu-error">{error}</div>}
        </div>
      )}
    </div>
  );
}
