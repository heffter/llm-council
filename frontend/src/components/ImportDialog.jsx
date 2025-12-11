import { useState, useRef } from 'react';
import { api } from '../api';
import './ImportDialog.css';

/**
 * Import dialog for importing conversations from JSON or ZIP files.
 */
export default function ImportDialog({ isOpen, onClose, onImportComplete }) {
  const [file, setFile] = useState(null);
  const [validation, setValidation] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [preserveIds, setPreserveIds] = useState(false);
  const fileInputRef = useRef(null);

  const resetState = () => {
    setFile(null);
    setValidation(null);
    setIsValidating(false);
    setIsImporting(false);
    setImportResult(null);
    setPreserveIds(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleFileSelect = async (e) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Check file extension
    const ext = selectedFile.name.toLowerCase();
    if (!ext.endsWith('.json') && !ext.endsWith('.zip')) {
      setValidation({
        valid: false,
        errors: ['Invalid file type. Only .json and .zip files are supported.'],
        warnings: [],
      });
      return;
    }

    setFile(selectedFile);
    setValidation(null);
    setImportResult(null);
    setIsValidating(true);

    try {
      const result = await api.validateImport(selectedFile);
      setValidation(result);
    } catch (err) {
      setValidation({
        valid: false,
        errors: [`Validation failed: ${err.message}`],
        warnings: [],
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleImport = async () => {
    if (!file || !validation?.valid) return;

    setIsImporting(true);
    setImportResult(null);

    try {
      const result = await api.importConversations(file, preserveIds);
      setImportResult(result);

      if (result.success) {
        onImportComplete?.(result.conversation_ids);
      }
    } catch (err) {
      setImportResult({
        success: false,
        conversation_ids: [],
        warnings: [],
        errors: [`Import failed: ${err.message}`],
      });
    } finally {
      setIsImporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="import-dialog-overlay" onClick={handleClose}>
      <div className="import-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="import-dialog-header">
          <h2>Import Conversations</h2>
          <button className="import-dialog-close" onClick={handleClose}>
            x
          </button>
        </div>

        <div className="import-dialog-body">
          {/* File selection */}
          <div className="import-file-section">
            <input
              ref={fileInputRef}
              type="file"
              id="import-file"
              className="import-file-input"
              accept=".json,.zip"
              onChange={handleFileSelect}
              disabled={isImporting}
            />
            <label htmlFor="import-file" className="import-file-label">
              {file ? file.name : 'Choose a file...'}
            </label>
            <p className="import-file-hint">
              Supports JSON (single conversation) or ZIP (multiple conversations)
            </p>
          </div>

          {/* Validation status */}
          {isValidating && (
            <div className="import-status validating">
              <div className="spinner-small"></div>
              <span>Validating file...</span>
            </div>
          )}

          {validation && !isValidating && (
            <div className={`import-validation ${validation.valid ? 'valid' : 'invalid'}`}>
              {validation.valid ? (
                <div className="validation-success">File is valid and ready to import</div>
              ) : (
                <div className="validation-errors">
                  {validation.errors.map((err, i) => (
                    <div key={i} className="validation-error">{err}</div>
                  ))}
                </div>
              )}

              {validation.warnings.length > 0 && (
                <div className="validation-warnings">
                  {validation.warnings.map((warn, i) => (
                    <div key={i} className="validation-warning">{warn}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Import options */}
          {validation?.valid && !importResult?.success && (
            <div className="import-options">
              <label className="import-option">
                <input
                  type="checkbox"
                  checked={preserveIds}
                  onChange={(e) => setPreserveIds(e.target.checked)}
                  disabled={isImporting}
                />
                <span>Preserve original conversation IDs (if available)</span>
              </label>
            </div>
          )}

          {/* Import result */}
          {importResult && (
            <div className={`import-result ${importResult.success ? 'success' : 'error'}`}>
              {importResult.success ? (
                <>
                  <div className="result-success">
                    Successfully imported {importResult.conversation_ids.length} conversation(s)
                  </div>
                  {importResult.warnings.length > 0 && (
                    <div className="result-warnings">
                      {importResult.warnings.map((warn, i) => (
                        <div key={i} className="result-warning">{warn}</div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="result-errors">
                  {importResult.errors.map((err, i) => (
                    <div key={i} className="result-error">{err}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="import-dialog-footer">
          {importResult?.success ? (
            <button className="import-btn primary" onClick={handleClose}>
              Done
            </button>
          ) : (
            <>
              <button className="import-btn secondary" onClick={handleClose}>
                Cancel
              </button>
              <button
                className="import-btn primary"
                onClick={handleImport}
                disabled={!validation?.valid || isImporting || isValidating}
              >
                {isImporting ? 'Importing...' : 'Import'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
