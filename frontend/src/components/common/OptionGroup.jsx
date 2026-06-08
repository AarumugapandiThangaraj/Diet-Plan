import React from 'react'

export default function OptionGroup({ label, options, selected, onSelect, className = '' }) {
  return (
    <div className={`optionGroup ${className}`.trim()}>
      <div className="optionLabel">{label}</div>
      <div className="chipGrid">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`choiceChip ${selected === option.value ? 'isActive' : ''}`}
            onClick={() => onSelect(option.value)}
          >
            <span className="choiceTitle">{option.label}</span>
            {option.description ? <span className="choiceDesc">{option.description}</span> : null}
          </button>
        ))}
      </div>
    </div>
  )
}
