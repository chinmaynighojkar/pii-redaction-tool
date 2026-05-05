import React, { useMemo } from "react";
import EntityBadge from "./EntityBadge.jsx";

function highlightRedactions(text) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return escaped.replace(
    /\[([A-Z0-9_]+ REDACTED)\]/g,
    '<mark>[$1]</mark>'
  );
}

function buildEntityCounts(summary) {
  const counts = {};
  for (const item of summary) {
    counts[item.label] = (counts[item.label] || 0) + 1;
  }
  return counts;
}

export default function RedactedViewer({ result, onDownload, onReset }) {
  const { redacted_text, entity_summary, entity_count, file_name } = result;

  const highlighted = useMemo(() => highlightRedactions(redacted_text), [redacted_text]);
  const entityCounts = useMemo(() => buildEntityCounts(entity_summary), [entity_summary]);

  return (
    <div className="card" style={{ gridColumn: "1 / -1" }}>
      <div className="stats-bar">
        <span>File: <strong>{file_name}</strong></span>
        <span>Entities detected: <strong>{entity_count}</strong></span>
        <span>Unique types: <strong>{Object.keys(entityCounts).length}</strong></span>
      </div>

      {Object.keys(entityCounts).length > 0 && (
        <div className="card-body" style={{ borderBottom: "1px solid var(--color-border)" }}>
          <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#6b7280", marginBottom: "0.6rem" }}>
            ENTITY TYPES FOUND
          </div>
          <div className="entity-list">
            {Object.entries(entityCounts).map(([label, count]) => (
              <EntityBadge key={label} label={label} count={count} />
            ))}
          </div>
        </div>
      )}

      <div className="card-body">
        <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#6b7280", marginBottom: "0.6rem" }}>
          REDACTED OUTPUT
        </div>
        <div
          className="redacted-text"
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />
      </div>

      <div className="action-row">
        <button className="btn btn-primary" style={{ width: "auto" }} onClick={onDownload}>
          ⬇ Download Redacted File
        </button>
        <button className="btn btn-ghost" onClick={onReset}>
          ↩ Redact Another File
        </button>
      </div>
    </div>
  );
}
