import React from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'

export default function MetricHub() {
  const { targets } = useProfileContext()

  return (
    <section className="panel calcPanel">
      <div className="panelHead">
        <h2>Metric Hub 🧮</h2>
        <p>These values update live while you type.</p>
      </div>

      <div className="metricGrid">
        <div className="metricCard">
          <span className="metricLabel">BMI ⚖️</span>
          <strong>{targets?.bmi ?? '—'}</strong>
          <span className={`bmiTag ${String(targets?.bmiCategory || 'Normal').toLowerCase()}`}>
            {targets?.bmiCategory || 'Normal'}
          </span>
        </div>
        <div className="metricCard">
          <span className="metricLabel">Target 🎯</span>
          <strong>{targets?.targetWeightKg ?? '—'}</strong>
          <span className="metricUnit">kg (BMI {targets?.targetBmi ?? '—'})</span>
        </div>
        <div className="metricCard">
          <span className="metricLabel">BMR 🔥</span>
          <strong>{targets?.bmr ?? '—'}</strong>
          <span className="metricUnit">kcal/day</span>
        </div>
        <div className="metricCard">
          <span className="metricLabel">TDEE ⚡</span>
          <strong>{targets?.tdee ?? '—'}</strong>
          <span className="metricUnit">kcal/day</span>
        </div>
        <div className="metricCard">
          <span className="metricLabel">Water 💧</span>
          <strong>{targets?.waterL ?? '—'}</strong>
          <span className="metricUnit">L/day</span>
        </div>
      </div>
    </section>
  )
}
