import React from "react";

export default function EntityBadge({ label, count }) {
  return (
    <span className="entity-badge">
      {label}
      <span className="count">{count}</span>
    </span>
  );
}
