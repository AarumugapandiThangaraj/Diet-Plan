import React from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'
import {
  MEAL_TIME_LABELS,
  MEAL_TIME_EMOJI
} from '../../config/constants.js'

export default function DayArranger() {
  const { setView } = useProfileContext()
  const {
    selectedMealTimes,
    selectedPoolsByTime,
    assignmentByTime,
    selectionDays,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDropOnDay,
    buildResultFromSelectedMeals,
    error
  } = usePlannerContext()

  return (
    <main className="plansLayout">
      <section className="panel planSummary">
        <div className="planSummaryHead">
          <div>
            <h2>Arrange days 📅</h2>
            <p>Drag meals into each day 🗓️. Swaps stay within the same meal time (breakfast ↔ breakfast) 🔁.</p>
          </div>
          <button type="button" className="secondaryBtn" onClick={() => setView('chooseMeals')}>
            Back to choices ⬅️
          </button>
        </div>
        {error ? <div className="inlineError">{error}</div> : null}
      </section>

      {selectedMealTimes.map((mealTime) => {
        const pool = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
        const assignment = Array.isArray(assignmentByTime?.[mealTime]) ? assignmentByTime[mealTime] : []

        return (
          <section key={`arrange-${mealTime}`} className="panel">
            <div className="planSummaryHead">
              <div>
                <h2 style={{ margin: 0, fontSize: 18 }}>
                  {MEAL_TIME_LABELS[mealTime] || mealTime} {MEAL_TIME_EMOJI[mealTime] || ''}
                </h2>
                <p style={{ margin: '6px 0 0', color: 'var(--muted)' }}>
                  Assign meals across Day 1…Day {selectionDays} 📅 (repeats allowed 🔁).
                </p>
              </div>
            </div>

            <div className="dragPool">
              {pool.map((m) => (
                <button
                  key={`pool-${mealTime}-${m.Meal_ID}`}
                  type="button"
                  className="dragItem"
                  draggable
                  onDragStart={(event) =>
                    handleDragStart(event, { mealTime, mealId: String(m.Meal_ID || '') })
                  }
                >
                  {m.meal_name}
                </button>
              ))}
            </div>

            <div
              className="dragGrid"
              style={{
                marginTop: 12,
                gridTemplateColumns: `repeat(${Math.min(selectionDays, 4)}, minmax(0, 1fr))`
              }}
            >
              {Array.from({ length: selectionDays }, (_, dayIndex) => dayIndex).map((dayIndex) => {
                const assignedId = String(assignment?.[dayIndex] || '')
                const assignedMeal = pool.find((m) => String(m?.Meal_ID || '') === assignedId)
                const label = assignedMeal?.meal_name || 'Drag a meal here'

                return (
                  <div
                    key={`arr-${mealTime}-d${dayIndex}`}
                    className={`dragSlot ${assignedMeal ? 'isFilled' : ''}`}
                    draggable={Boolean(assignedId)}
                    onDragStart={(event) =>
                      assignedId &&
                      handleDragStart(event, {
                        mealTime,
                        mealId: assignedId,
                        sourceDayIndex: dayIndex
                      })
                    }
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={(event) => handleDropOnDay(event, mealTime, dayIndex)}
                  >
                    <div className="dragSlotLabel">Day {dayIndex + 1} 📅</div>
                    <div className="dragSlotValue">{label}</div>
                    <div className="dragSlotHint">Drag within {MEAL_TIME_LABELS[mealTime] || mealTime}</div>
                  </div>
                )
              })}
            </div>
          </section>
        )
      })}

      <section className="panel">
        <div className="actions" style={{ marginTop: 0 }}>
          <button type="button" className="primaryBtn" onClick={buildResultFromSelectedMeals}>
            Generate plan ✅
          </button>
          <button type="button" className="secondaryBtn" onClick={() => setView('chooseMeals')}>
            Back ⬅️
          </button>
        </div>
      </section>
    </main>
  )
}
