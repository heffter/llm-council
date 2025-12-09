import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

// Allowed file extensions for upload
const ALLOWED_EXTENSIONS = ['.md', '.txt', '.json', '.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css', '.yaml', '.yml', '.xml', '.csv'];
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
}) {
  const [input, setInput] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    setFileError(null);

    if (!file) {
      setUploadedFile(null);
      return;
    }

    // Validate file extension
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFileError(`Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
      setUploadedFile(null);
      e.target.value = '';
      return;
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      setFileError(`File too large. Maximum size: ${MAX_FILE_SIZE / (1024 * 1024)}MB`);
      setUploadedFile(null);
      e.target.value = '';
      return;
    }

    // Read file content
    const reader = new FileReader();
    reader.onload = (event) => {
      setUploadedFile({
        name: file.name,
        content: event.target.result,
      });
    };
    reader.onerror = () => {
      setFileError('Failed to read file');
      setUploadedFile(null);
    };
    reader.readAsText(file);
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setFileError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((input.trim() || uploadedFile) && !isLoading) {
      // Combine user input with file content if present
      let messageContent = input.trim();
      if (uploadedFile) {
        const fileSection = `\n\n---\n**Attached File: ${uploadedFile.name}**\n\`\`\`\n${uploadedFile.content}\n\`\`\``;
        messageContent = messageContent ? messageContent + fileSection : `Please analyze this file:\n${fileSection}`;
      }
      onSendMessage(messageContent);
      setInput('');
      setUploadedFile(null);
      setFileError(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">LLM Council</div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <textarea
              className="message-input"
              placeholder="Ask your question... (Shift+Enter for new line, Enter to send)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={3}
            />

            {/* File upload section */}
            <div className="file-upload-section">
              <input
                ref={fileInputRef}
                type="file"
                id="file-upload"
                className="file-input-hidden"
                accept={ALLOWED_EXTENSIONS.join(',')}
                onChange={handleFileSelect}
                disabled={isLoading}
              />
              <label htmlFor="file-upload" className={`file-upload-button ${isLoading ? 'disabled' : ''}`}>
                Attach File
              </label>

              {uploadedFile && (
                <div className="uploaded-file-badge">
                  <span className="file-name">{uploadedFile.name}</span>
                  <button
                    type="button"
                    className="remove-file-button"
                    onClick={handleRemoveFile}
                    aria-label="Remove file"
                  >
                    x
                  </button>
                </div>
              )}

              {fileError && (
                <div className="file-error">{fileError}</div>
              )}
            </div>
          </div>

          <button
            type="submit"
            className="send-button"
            disabled={(!input.trim() && !uploadedFile) || isLoading}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
