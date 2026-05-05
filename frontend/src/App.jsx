import React, { useState } from "react";
import UploadZone from "./components/UploadZone.jsx";
import RedactedViewer from "./components/RedactedViewer.jsx";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleAnalyse(file) {
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/redact", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || `Server error ${res.status}`);
      }

      setResult(data);
    } catch (err) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }

  function handleDownload() {
    if (!result) return;
    window.open(`/api/download/${encodeURIComponent(result.file_name)}`, "_blank");
  }

  function handleReset() {
    setResult(null);
    setError(null);
  }

  return (
    <>
      <header className="header">
        <span style={{ fontSize: "1.4rem" }}>🔒</span>
        <h1>PII Redaction Tool</h1>
        <span className="subtitle">GDPR-compliant document anonymisation</span>
      </header>

      <main className="main">
        {!result ? (
          <div className="grid">
            <UploadZone onAnalyse={handleAnalyse} loading={loading} error={error} />

            <div className="card">
              <div className="card-header">ℹ How It Works</div>
              <div className="card-body" style={{ fontSize: "0.875rem", color: "#374151", lineHeight: 1.8 }}>
                <ol style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  <li>Upload a <strong>PDF</strong>, <strong>CSV</strong>, or <strong>TXT</strong> document containing personal data.</li>
                  <li>The backend extracts text and runs it through <strong>openai/privacy-filter</strong>, a token-classification model trained to detect PII.</li>
                  <li>Detected spans — names, emails, phone numbers, addresses, and more — are replaced with labelled placeholders such as <mark style={{ background: "#fde68a", borderRadius: 3, padding: "0 4px", color: "#92400e", fontWeight: 600 }}>[NAME REDACTED]</mark>.</li>
                  <li>A redacted copy is saved and available for download.</li>
                </ol>
                <div style={{ marginTop: "1.25rem", padding: "0.875rem", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 6 }}>
                  <strong style={{ color: "#065f46" }}>Supported entity types</strong>
                  <div style={{ marginTop: "0.4rem", color: "#047857", fontSize: "0.8rem" }}>
                    NAME · EMAIL · PHONE · ADDRESS · ID · DATE · ORGANIZATION · and more
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid">
            <RedactedViewer
              result={result}
              onDownload={handleDownload}
              onReset={handleReset}
            />
          </div>
        )}
      </main>

      <footer className="footer">
        PII Redaction Tool · Powered by openai/privacy-filter &amp; FastAPI · Data never leaves your machine
      </footer>
    </>
  );
}
