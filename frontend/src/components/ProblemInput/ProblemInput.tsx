import React, { useState, useRef, useEffect } from 'react';

interface ProblemInputProps {
  query: string;
  onQueryChange: (q: string) => void;
  onSubmit: (imageData?: string | null, errorCode?: string | null) => void;
  loading: boolean;
}

const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const SUPPORTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

export const ProblemInput: React.FC<ProblemInputProps> = ({
  query,
  onQueryChange,
  onSubmit,
  loading,
}) => {
  const [errorCode, setErrorCode] = useState('');
  const [showOptional, setShowOptional] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageNotice, setImageNotice] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.max(120, textareaRef.current.scrollHeight)}px`;
    }
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    onSubmit(imagePreview, errorCode.trim() || null);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImageError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size === 0) {
      setImageError('Selected image file is empty.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setImageError('Image exceeds maximum size of 5 MB. Please select a smaller screenshot.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (!SUPPORTED_IMAGE_TYPES.includes(file.type.toLowerCase())) {
      setImageError('Unsupported format. Please upload a PNG, JPG, or WEBP screenshot.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
      setImageNotice(true);
    };
    reader.readAsDataURL(file);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="hero-problem-input-card">
      <form onSubmit={handleSubmit} className="hero-input-form">
        <div className="input-search-header">
          <div className="search-icon-badge" aria-hidden="true">
            <span className="search-icon">🔍</span>
          </div>
          <div className="search-heading-wrap">
            <label htmlFor="problem-textarea" className="search-prompt-label">
              Describe what's happening with your Galaxy...
            </label>
            <span className="search-prompt-hint">Natural language, symptom, or error message</span>
          </div>
        </div>

        <div className="textarea-glow-wrapper">
          <textarea
            id="problem-textarea"
            ref={textareaRef}
            rows={3}
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder='e.g., "My Galaxy S22 Wi-Fi keeps disconnecting and I cannot load web pages."'
            className="hero-textarea"
            autoFocus
          />
        </div>

        {/* Primary Action Row */}
        <div className="hero-action-bar">
          <div className="action-bar-left">
            <button
              type="button"
              className={`btn-toggle-options ${showOptional ? 'active' : ''}`}
              onClick={() => setShowOptional(!showOptional)}
              aria-expanded={showOptional}
            >
              <span>⚙️ Additional Information</span>
              <span className="caret">{showOptional ? '▲' : '▼'}</span>
            </button>
            <span className="shortcut-hint">Press <strong>Ctrl + Enter</strong> to diagnose</span>
          </div>

          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="btn-start-hero-diagnosis"
          >
            {loading ? (
              <>
                <span className="hero-spinner" aria-hidden="true" />
                <span>{imagePreview ? 'Analyzing Screenshot...' : 'Analyzing Problem...'}</span>
              </>
            ) : (
              <>
                <span>Start Diagnosis</span>
                <span className="btn-arrow" aria-hidden="true">→</span>
              </>
            )}
          </button>
        </div>

        {/* Optional Context Dropdown (Error Code & Screenshot) */}
        {showOptional && (
          <div className="optional-info-drawer">
            <div className="optional-grid">
              <div className="optional-col">
                <label htmlFor="error-code-input" className="opt-label">
                  Error Code or Number (Optional)
                </label>
                <input
                  id="error-code-input"
                  type="text"
                  value={errorCode}
                  onChange={(e) => setErrorCode(e.target.value)}
                  placeholder="e.g. ERR_SSL_PROTOCOL_ERROR or 1001"
                  className="opt-text-input"
                />
              </div>

              <div className="optional-col">
                <span className="opt-label">Screenshot / Photo of Display</span>
                <div className="file-upload-row">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleImageChange}
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden-file-input"
                    id="screenshot-file-input"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="btn-upload-screenshot"
                  >
                    <span>📷 Attach Screenshot</span>
                  </button>

                  {imagePreview && (
                    <div className="image-preview-badge">
                      <img src={imagePreview} alt="Screenshot preview" className="mini-thumb" />
                      <button
                        type="button"
                        onClick={() => {
                          setImagePreview(null);
                          setImageNotice(false);
                          setImageError(null);
                          if (fileInputRef.current) fileInputRef.current.value = '';
                        }}
                        className="btn-remove-thumb"
                        title="Remove screenshot"
                      >
                        ✕ Remove
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {imageError && (
              <div className="image-notice-banner" role="alert" style={{ borderColor: 'var(--rose-border)', background: 'var(--rose-subtle)', color: '#fca5a5' }}>
                <span className="notice-icon">⚠️</span>
                <span className="notice-text">{imageError}</span>
              </div>
            )}

            {imageNotice && imagePreview && (
              <div className="image-notice-banner" role="status">
                <span className="notice-icon">📷</span>
                <span className="notice-text">
                  Screenshot attached (max 5MB). Visual symptoms &amp; error codes will be extracted to support diagnosis.
                </span>
              </div>
            )}
          </div>
        )}
      </form>
    </div>
  );
};
