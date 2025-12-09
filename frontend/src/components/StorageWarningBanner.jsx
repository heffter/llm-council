import { useState, useEffect } from 'react';
import './StorageWarningBanner.css';

const STORAGE_DISMISSED_KEY = 'storageWarningDismissed';

function StorageWarningBanner() {
  const [dismissed, setDismissed] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const isDismissed = localStorage.getItem(STORAGE_DISMISSED_KEY) === 'true';
    setDismissed(isDismissed);
  }, []);

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_DISMISSED_KEY, 'true');
    setDismissed(true);
  };

  const toggleDetails = () => {
    setShowDetails(!showDetails);
  };

  if (dismissed) {
    return null;
  }

  return (
    <div className="storage-warning-banner">
      <div className="banner-content">
        <div className="banner-icon">⚠️</div>
        <div className="banner-text">
          <strong>Data Storage Notice:</strong> Conversations are stored as{' '}
          <strong>unencrypted JSON files</strong> under <code>data/conversations/</code>{' '}
          on this machine. Do not store sensitive or personal data.
        </div>
        <div className="banner-actions">
          <button onClick={toggleDetails} className="banner-button secondary">
            Learn more
          </button>
          <button onClick={handleDismiss} className="banner-button primary">
            Dismiss
          </button>
        </div>
      </div>

      {showDetails && (
        <div className="banner-details">
          <h3>Storage Details</h3>
          <ul>
            <li>
              <strong>Location:</strong> <code>data/conversations/</code> directory
            </li>
            <li>
              <strong>Format:</strong> Unencrypted JSON files, one per conversation
            </li>
            <li>
              <strong>Encryption:</strong> None - all data is stored in plain text
            </li>
            <li>
              <strong>Deletion:</strong> Removing the <code>data/</code> folder will delete
              all conversation history
            </li>
            <li>
              <strong>Security:</strong> This storage method is suitable for local
              development and testing only
            </li>
          </ul>
          <p className="banner-warning-text">
            For production use with sensitive data, consider implementing encrypted storage,
            database backends, or other secure storage solutions.
          </p>
        </div>
      )}
    </div>
  );
}

export default StorageWarningBanner;

