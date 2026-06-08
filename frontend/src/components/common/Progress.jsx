import React from 'react'

export default function Progress({ label, value, target, unit }) {
  const pct = target > 0 ? Math.min(100, Math.round((value / target) * 100)) : 0
  return (
    <div className="progressRow">
      <div className="progressMeta">
        <span>{label}</span>
        <strong>
          {Math.round(value)}{unit} <span>/ {Math.round(target)}{unit}</span>
        </strong>
      </div>
      <div className="progressTrack">
        <div className="progressValue" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
