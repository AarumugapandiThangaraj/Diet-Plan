import React from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'
import { usePDFGenerator } from '../../hooks/usePDFGenerator.js'
import Progress from '../../components/common/Progress.jsx'
import {
  MEAL_TIME_ORDER,
  MEAL_TIME_LABELS,
  MEAL_TIME_EMOJI
} from '../../config/constants.js'

export default function PlanViewer({ onNavigateToDashboard }) {
  const { setView, targets } = useProfileContext()
  const {
    dayPlans,
    daysCount,
    totalsByDay,
    result,
    setSelectedMealDetails,
    handleSwapWholeMeal,
    handleSwapFood,
    getDisplayMealName,
    activateAndProceed
  } = usePlannerContext()

  const { generatePDF } = usePDFGenerator()

  return (
    <main className="plansLayout">
      <section className="panel planSummary">
        <div className="planSummaryHead">
          <div>
            <h2>Your Selected Plan ✅🍱</h2>
            <p>Only your generated plan is shown on this page for a cleaner experience ✨.</p>
          </div>
          <button type="button" className="secondaryBtn" onClick={() => setView('selectedMeals')}>
            Back ⬅️
          </button>
        </div>
      </section>

      <div id="final-plan-container">
        <section className="planGrid">
          {dayPlans.map((dayPlan, dayIndex) => (
            <div key={`day-${dayIndex + 1}`} className="dayBlock">
              <h3 className="dayTitle">Day {dayIndex + 1} 📅</h3>
              {totalsByDay?.[dayIndex] ? (
                <div className="dayTotals">
                  <div className="dayTotalsHead">Day {dayIndex + 1} nutrients 🧬</div>
                  <div className="progressWrap">
                    <Progress label="Calories 🔥" value={totalsByDay[dayIndex]?.caloriesKcal || 0} target={targets?.dailyCalories || 0} unit="" />
                    <Progress label="Protein 💪" value={totalsByDay[dayIndex]?.proteinG || 0} target={targets?.proteinG || 0} unit="g" />
                    <Progress label="Carbs 🍞" value={totalsByDay[dayIndex]?.carbsG || 0} target={targets?.carbsG || 0} unit="g" />
                    <Progress label="Fat 🥑" value={totalsByDay[dayIndex]?.fatG || 0} target={targets?.fatG || 0} unit="g" />
                    <Progress label="Fiber 🥦" value={totalsByDay[dayIndex]?.fiberG || 0} target={targets?.fiberG || 0} unit="g" />
                    <Progress label="Water 💧" value={targets?.waterL || 0} target={targets?.waterL || 0} unit="L" />
                  </div>
                </div>
              ) : null}
              <div className="dayGrid">
                {console.log("Meal Times", result?.mealTimes)}
                {(result?.mealTimes || MEAL_TIME_ORDER).map((mealTime) => {
                  const item = dayPlan?.[mealTime]
                  console.log("item", item)
                  return (
                    <article key={`${dayIndex}-${mealTime}`} className="planCard">
                      {(() => {
                        const foods = Array.isArray(item?.foods_struct) ? item.foods_struct : []
                        const firstFoodId = foods.length > 0 ? (foods[0]?.id || foods[0]?.ID || foods[0]?.food_id || '') : ''
                        if (firstFoodId) {
                          return (
                            <div className="planCardImage">
                              <img
                                src={`http://localhost:8000/api/food-image/${firstFoodId}`}
                                alt={getDisplayMealName(item)}
                                onError={(e) => { e.target.parentElement.style.display = 'none'; }}
                              />
                            </div>
                          )
                        }
                        return null
                      })()}
                      <header className="planCardHead">
                        <div>
                          <p className="slotLabel">
                            {MEAL_TIME_LABELS[mealTime] || mealTime} {MEAL_TIME_EMOJI[mealTime] || ''}
                          </p>
                          <h3>{getDisplayMealName(item)}</h3>
                          {item?.time ? <p className="slotTime">{item.time}</p> : null}
                        </div>
                        {item?.macros ? (
                          <div className="macroMiniGrid">
                            <div><strong>{Math.round(item.macros.caloriesKcal || 0)}</strong><span>kcal</span></div>
                            <div><strong>{Math.round(item.macros.proteinG || 0)}</strong><span>P</span></div>
                            <div><strong>{Math.round(item.macros.carbsG || 0)}</strong><span>C</span></div>
                            <div><strong>{Math.round(item.macros.fatG || 0)}</strong><span>F</span></div>
                          </div>
                        ) : null}
                      </header>

                      {item?.serving_size ? <p className="line"><span>Serving:</span> {item.serving_size}</p> : null}

                      <div className="actions html2pdf__ignore" style={{ marginTop: 12 }}>
                        <button
                          type="button"
                          className="primaryBtn"
                          onClick={() => setSelectedMealDetails(item)}
                          disabled={!item?.Meal_ID}
                        >
                          View Details
                        </button>
                        <button
                          type="button"
                          className="secondaryBtn"
                          onClick={() => handleSwapWholeMeal(dayIndex, mealTime)}
                          disabled={!item?.Meal_ID}
                        >
                          Swap whole meal
                        </button>
                        <button
                          type="button"
                          className="secondaryBtn"
                          onClick={() => handleSwapFood(dayIndex, mealTime)}
                          disabled={!item?.Meal_ID}
                        >
                          Swap food
                        </button>
                      </div>

                      {item?.caution ? <p className="cautionLine">{item.caution}</p> : null}
                    </article>
                  )
                })}
              </div>
            </div>
          ))}
        </section>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', margin: '32px 0' }}>
        <button
          type="button"
          className="primaryBtn"
          style={{ padding: '16px 32px', fontSize: '1.1rem' }}
          onClick={() => generatePDF('final-plan-container')}
        >
          Generate Final Plan 📄
        </button>
        <button
          type="button"
          className="secondaryBtn"
          style={{ padding: '16px 32px', fontSize: '1.1rem', minWidth: '240px' }}
          onClick={() => activateAndProceed(onNavigateToDashboard)}
        >
          Activate & Go to Dashboard 📊
        </button>
      </div>
    </main>
  )
}
