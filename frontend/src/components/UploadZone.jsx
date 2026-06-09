import React, { useRef, useState } from "react";

const ACCEPTED = [".pdf", ".csv", ".txt"];
const ACCEPTED_MIME = ["application/pdf", "text/csv", "text/plain"];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB — matches backend limit

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  if (ext === "pdf") return "📄";
  if (ext === "csv") return "📊";
  return "📝";
}

export default function UploadZone({ onAnalyse, loading, error }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [sizeError, setSizeError] = useState(null);

  function handleFile(f) {
    if (!f) return;
    if (f.size > MAX_SIZE) {
      setFile(null);
      setSizeError(`File too large (${formatBytes(f.size)}). Maximum size is 10 MB.`);
      return;
    }
    setSizeError(null);
    setFile(f);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  function handleChange(e) {
    handleFile(e.target.files[0]);
  }

  function handleAnalyse() {
    if (file) onAnalyse(file);
  }

  return (
    <div className="card">
      <div className="card-header">
        🔒 Upload Document
      </div>
      <div className="card-body">
        <div
          className={`upload-zone${dragOver ? " drag-over" : ""}`}
          onClick={() => inputRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(",")}
            onChange={handleChange}
          />
          <span className="upload-icon">☁️</span>
          <strong>Drop a file here or click to browse</strong>
          <p>Drag and drop your document to get started</p>
          <p className="accepted">Accepted formats: PDF · CSV · TXT</p>
        </div>

        {file && (
          <div className="file-chip">
            <span className="file-icon">{fileIcon(file.name)}</span>
            <div className="file-info">
              <div className="file-name">{file.name}</div>
              <div className="file-size">{formatBytes(file.size)}</div>
            </div>
            <button
              className="remove-btn"
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              title="Remove file"
            >
              ✕
            </button>
          </div>
        )}

        {(sizeError || error) && <div className="error-box">⚠ {sizeError || error}</div>}

        <button
          className="btn btn-primary"
          onClick={handleAnalyse}
          disabled={!file || loading}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Analysing…
            </>
          ) : (
            "Analyse Document"
          )}
        </button>
      </div>
    </div>
  );
}
