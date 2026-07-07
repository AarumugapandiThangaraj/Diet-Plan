import React from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'
import { windowed } from '../../utils/helpers.js'
import {
  MEAL_TIME_LABELS,
  MEAL_TIME_EMOJI
} from '../../config/constants.js'

export default function MealPoolSelector() {
  const { setView } = useProfileContext()
  const {
    selectedMealTimes,
    rankedMealsByTime,
    selectedPoolsByTime,
    carouselByTime,
    rankLoading,
    autoSelectTopMeals,
    refreshMealTimeOptions,
    toggleMealInPool,
    buildResultFromSelectedMeals,
    isSelectionComplete,
    error
  } = usePlannerContext()

  return (
    <main className="plansLayout">
      <section className="panel planSummary">
        <div className="planSummaryHead">
          <div />
          <div className="actions" style={{ marginTop: 0 }}>
            <button type="button" className="secondaryBtn" onClick={autoSelectTopMeals}>
              Magic select ✨
            </button>
            <button type="button" className="secondaryBtn" onClick={() => setView('inputs')}>
              Back to inputs ⬅️
            </button>
          </div>
        </div>
        {error ? <div className="inlineError">{error}</div> : null}
      </section>

      {selectedMealTimes.map((mealTime) => {
        const ranked = rankedMealsByTime?.[mealTime] || []
        const top7 = ranked.slice(0, 7)
        const picked = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
        const pickedIds = new Set(picked.map((m) => m?.Meal_ID).filter(Boolean))
        const candidates = top7.filter((m) => !pickedIds.has(m?.Meal_ID))
        const cursor = Number.isFinite(Number(carouselByTime?.[mealTime]?.cursor)) ? Number(carouselByTime[mealTime].cursor) : 0
        const safeCursor = candidates.length ? cursor % candidates.length : 0
        const options = windowed(candidates, safeCursor, 3)

        return (
          <section key={`choices-${mealTime}`} className="panel">
            <div className="planSummaryHead">
              <div>
                <h2 style={{ margin: 0, fontSize: 18 }}>
                  {MEAL_TIME_LABELS[mealTime] || mealTime} {MEAL_TIME_EMOJI[mealTime] || ''}
                </h2>
                <p style={{ margin: '6px 0 0', color: 'var(--muted)' }}>
                  Selected: <strong>{picked.length}</strong> ✅
                </p>
              </div>
              <button
                type="button"
                className="secondaryBtn"
                onClick={() => refreshMealTimeOptions(mealTime)}
                disabled={candidates.length <= 3}
              >
                No, I dont like any meal 🙅
              </button>
            </div>

            {picked.length ? (
              <div className="detailBlock" style={{ marginTop: 10 }}>
                <h4>Chosen</h4>
                <div className="chosenList">
                  {picked.map((m) => (
                    <div key={`chosen-${mealTime}-${m?.Meal_ID}`} className="chosenItem">
                      <span>{m?.meal_name}</span>
                      <button
                        type="button"
                        className="removeTinyBtn"
                        onClick={() => toggleMealInPool(mealTime, m)}
                        aria-label="Remove meal"
                        title="Remove"
                      >
                        -
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="dayGrid" style={{ marginTop: 12 }}>
              {options.length ? (
                options.map((meal) => (
                  <article key={`${mealTime}-${meal.Meal_ID}`} className="planCard">
                    {(() => {
                      const foods = Array.isArray(meal?.foods_struct) ? meal.foods_struct : []
                      const firstFoodId = foods.length > 0 ? (foods[0]?.id || foods[0]?.ID || foods[0]?.food_id || '') : ''
                      if (firstFoodId) {
                        return (
                          <div className="planCardImage">
                            <img
                              src={`http://localhost:8000/api/food-image/${firstFoodId}`}
                              alt={meal.meal_name}
                              onError={(e) => { e.target.parentElement.style.display = 'none'; }}
                            />
                          </div>
                        )
                      }
                      return null
                    })()}
                    <header className="planCardHead">
                      <div>
                        <p className="slotLabel">Option</p>
                        <h3>{meal.meal_name}</h3>
                        {meal?.time ? <p className="slotTime">{meal.time}</p> : null}
                      </div>
                      {meal?._macros ? (
                        <div className="macroMiniGrid">
                          <div><strong>{Math.round(meal._macros.caloriesKcal || 0)}</strong><span>kcal</span></div>
                          <div><strong>{Math.round(meal._macros.proteinG || 0)}</strong><span>P</span></div>
                          <div><strong>{Math.round(meal._macros.carbsG || 0)}</strong><span>C</span></div>
                          <div><strong>{Math.round(meal._macros.fatG || 0)}</strong><span>F</span></div>
                        </div>
                      ) : null}
                    </header>

                    {meal?.serving_size ? <p className="line"><span>Serving:</span> {meal.serving_size}</p> : null}
                    {meal?.caution ? <p className="cautionLine">{meal.caution}</p> : null}

                    <div className="actions" style={{ marginTop: 12 }}>
                      <button
                        type="button"
                        className="primaryBtn"
                        onClick={() => toggleMealInPool(mealTime, meal)}
                      >
                        {pickedIds.has(meal.Meal_ID) ? 'Remove' : 'Select'}
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div style={{ color: 'var(--muted)' }}>
                  {rankLoading ? 'Loading meals…' : 'No meals found for this meal time with the current filters.'}
                </div>
              )}
            </div>
          </section>
        )
      })}

      <section className="panel">
        <div className="actions" style={{ marginTop: 0 }}>
          <button type="button" className="primaryBtn" onClick={buildResultFromSelectedMeals} disabled={!isSelectionComplete}>
            Arrange days 📅
          </button>
          <button type="button" className="secondaryBtn" onClick={() => setView('inputs')}>
            Back ⬅️
          </button>
        </div>
      </section>
    </main>
  )
}
