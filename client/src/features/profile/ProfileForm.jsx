import React from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'
import OptionGroup from '../../components/common/OptionGroup.jsx'
import {
  GOALS,
  ACTIVITY,
  DIET,
  CUISINES,
  PLAN_DAYS,
  MEAL_TIME_ORDER,
  MEAL_TIME_EMOJI,
  MEAL_TIME_LABELS
} from '../../config/constants.js'

export default function ProfileForm() {
  const {
    profile,
    updateProfile,
    updateMealsPerDay,
    toggleMealTime,
    resetProfile,
    validateInputsForMealChoice
  } = useProfileContext()

  const {
    planDays,
    updatePlanDays,
    goToMealChoices,
    resetPlanner,
    error,
    setError
  } = usePlannerContext()

  const handleNext = () => {
    const msg = validateInputsForMealChoice()
    goToMealChoices(msg)
  }

  const handleReset = () => {
    resetProfile()
    resetPlanner()
  }

  const mealsPerDay = profile.mealsPerDay
  const selectedMealTimes = profile.mealTimes

  return (
    <section className="panel formPanel">
      <div className="panelHead">
        <h2>Your Inputs 🧾</h2>
        <p>Height and weight are text boxes now, so you can freely type the values you want ✍️.</p>
      </div>

      <div className="fieldGrid">
        <label className="field">
          <span>Age</span>
          <input
            type="number"
            value={profile.age}
            min="1"
            max="120"
            onChange={(e) => updateProfile({ age: e.target.value })}
          />
        </label>

        <label className="field">
          <span>Gender</span>
          <select value={profile.gender} onChange={(e) => updateProfile({ gender: e.target.value })}>
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </label>

        <label className="field">
          <span>Height (cm)</span>
          <input
            type="text"
            inputMode="decimal"
            value={profile.heightCm}
            onChange={(e) => updateProfile({ heightCm: e.target.value })}
            placeholder="e.g., 165 or 165.5"
          />
        </label>

        <label className="field">
          <span>Weight (kg)</span>
          <input
            type="text"
            inputMode="decimal"
            value={profile.weightKg}
            onChange={(e) => updateProfile({ weightKg: e.target.value })}
            placeholder="e.g., 60 or 60.4"
          />
        </label>
      </div>

      <div className="fieldGrid" style={{ marginTop: 12 }}>
        <label className="field">
          <span>Primary goal</span>
          <select value={profile.goal} onChange={(e) => updateProfile({ goal: e.target.value })}>
            {GOALS.map((g) => (
              <option key={`goal-${g.value}`} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Activity level</span>
          <select value={profile.activityLevel} onChange={(e) => updateProfile({ activityLevel: e.target.value })}>
            {ACTIVITY.map((a) => (
              <option key={`act-${a.value}`} value={a.value}>
                {a.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <OptionGroup
        label="Diet preference 🥦🍗"
        options={DIET}
        selected={profile.dietType}
        onSelect={(value) => updateProfile({ dietType: value })}
      />

      <label className="field fullWidth" style={{ marginTop: 24, marginBottom: 8 }}>
        <span>Cuisine type 🌍</span>
        <select value={profile.cuisineType} onChange={(e) => updateProfile({ cuisineType: e.target.value })}>
          {CUISINES.map((c) => (
            <option key={`cuisine-${c.value}`} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </label>

      <OptionGroup
        label="Plan length 📅"
        options={PLAN_DAYS}
        selected={planDays}
        onSelect={(value) => updatePlanDays(value)}
        className="compact"
      />

      <div className="optionGroup">
        <div className="optionLabel">Meals per day</div>
        <div className="fieldGrid" style={{ marginTop: 0 }}>
          <label className="field">
            <span>How many meals per day?</span>
            <select value={mealsPerDay} onChange={(e) => updateMealsPerDay(e.target.value)}>
              {Array.from({ length: Math.max(0, MEAL_TIME_ORDER.length - 1) }, (_, i) => i + 2).map((n) => (
                <option key={`mpd-${n}`} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <div className="field">
            <span>Selected meal times</span>
            <div style={{ height: 44, display: 'flex', alignItems: 'center', color: 'var(--muted)', fontSize: 13 }}>
              {selectedMealTimes.length} / {mealsPerDay} selected
            </div>
          </div>
        </div>

        <div className="chipGrid" style={{ marginTop: 10 }}>
          {MEAL_TIME_ORDER.map((mealTime) => {
            const isSelected = selectedMealTimes.includes(mealTime)
            const isDisabled = !isSelected && selectedMealTimes.length >= mealsPerDay
            return (
              <button
                key={`mt-${mealTime}`}
                type="button"
                className={`choiceChip ${isSelected ? 'isActive' : ''}`}
                onClick={() => !isDisabled && toggleMealTime(mealTime)}
                disabled={isDisabled}
              >
                <span className="choiceTitle">
                  {MEAL_TIME_LABELS[mealTime] || mealTime} {MEAL_TIME_EMOJI[mealTime] || ''}
                </span>
                <span className="choiceDesc">{isSelected ? 'Selected' : 'Tap to include'}</span>
              </button>
            )
          })}
        </div>
      </div>

      <label className="field fullWidth">
        <span>Allergies (comma-separated)</span>
        <input
          type="text"
          value={profile.allergies}
          onChange={(e) => updateProfile({ allergies: e.target.value })}
          placeholder="e.g., dairy, egg, wheat"
        />
      </label>

      <div className="actions">
        <button type="button" className="primaryBtn" onClick={handleNext}>
          Next: Choose meals 🍽️
        </button>
        <button type="button" className="secondaryBtn" onClick={handleReset}>
          Reset inputs 🔄
        </button>
      </div>

      {error ? <div className="inlineError">{error}</div> : null}
    </section>
  )
}
