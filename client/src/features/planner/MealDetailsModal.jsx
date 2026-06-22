import React from 'react'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'

export default function MealDetailsModal() {
  const {
    selectedMealDetails,
    setSelectedMealDetails,
    getDisplayMealName
  } = usePlannerContext()

  if (!selectedMealDetails) return null

  return (
    <div className="swapOverlay" onClick={() => setSelectedMealDetails(null)} role="dialog" aria-modal="true">
      <div className="swapPanel foodDetailsPanel" onClick={(e) => e.stopPropagation()}>
        <div className="swapHead">
          <div>
            <p className="swapEyebrow">Meal Details</p>
            <h3>{getDisplayMealName(selectedMealDetails)}</h3>
            {selectedMealDetails?.time ? <p className="swapHint">{selectedMealDetails.time}</p> : null}
          </div>
          <div className="swapActions">
            <button type="button" className="secondaryBtn" onClick={() => setSelectedMealDetails(null)}>
              Close
            </button>
          </div>
        </div>
        
        <div className="foodDetailsScroll">
          {(() => {
            const foods = Array.isArray(selectedMealDetails?.foods_struct) ? selectedMealDetails.foods_struct : []
            if (!foods.length) return <p style={{ color: 'var(--muted)' }}>No food details available.</p>
            
            return foods.map((food, idx) => {
              const prep = String(food?.preparation || '').trim()
              const name = String(food?.name || '').trim() || 'Food'
              const foodId = food?.id || food?.ID || food?.food_id || ''
              const steps = prep
                .split(/\s*\d+\.\s*/)
                .map((s) => s.trim())
                .filter(Boolean)
              const ingredients = Array.isArray(food?.ingredients_struct) ? food.ingredients_struct : []
              
              return (
                <div key={`modal-food-${idx}`} className="foodDetailItem">
                  <h4 className="foodDetailName">{name}</h4>
                  {foodId && (
                    <div className="foodImageWrapper">
                      <img 
                        src={`http://localhost:8000/api/food-image/${foodId}`} 
                        alt={name}
                        className="foodImage"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    </div>
                  )}
                  
                  {ingredients.length > 0 && (
                    <div className="foodDetailSection">
                      <div className="foodDetailLabel">Ingredients</div>
                      <ul className="ingList">
                        {ingredients.map((ing, iIdx) => (
                          <li key={`modal-ing-${idx}-${iIdx}`}>
                            {ing.name} - {Math.round((ing.quantity || 0) * 10) / 10} {ing.unit}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {steps.length > 0 && (
                    <div className="foodDetailSection">
                      <div className="foodDetailLabel">Preparation</div>
                      <ol className="prepSteps">
                        {steps.map((step, stepIndex) => (
                          <li key={`modal-prep-${idx}-${stepIndex}`}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              )
            })
          })()}
          
          {selectedMealDetails?.caution ? (
            <div style={{ marginTop: 24 }}>
              <p className="cautionLine">{selectedMealDetails.caution}</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
