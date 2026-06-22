import React from 'react'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'
import { MEAL_TIME_LABELS } from '../../config/constants.js'

export default function SwapModal() {
  const {
    swapState,
    setSwapState,
    closeSwapModal,
    applyMealSwapSelection,
    loadFoodSwapOptions,
    applyFoodSwapSelection,
    loadIngredientSwapOptions,
    applyIngredientSwapSelection
  } = usePlannerContext()

  if (!swapState?.open) return null

  const swapTitle = (() => {
    if (swapState.type === 'meal') {
      return `Swap ${MEAL_TIME_LABELS[swapState.mealTime] || swapState.mealTime}`
    }
    if (swapState.type === 'food') {
      return swapState.step === 'pickFoodReplacement'
        ? `Replace ${swapState.selectedLabel || 'Food'}`
        : 'Pick a food to swap'
    }
    if (swapState.type === 'ingredient') {
      return swapState.step === 'pickIngredientReplacement'
        ? `Replace ${swapState.selectedLabel || 'Ingredient'}`
        : 'Pick an ingredient to swap'
    }
    return 'Swap'
  })()

  const swapHint = (() => {
    if (swapState.type === 'meal') return 'Only meals from your selected pool are shown.'
    if (swapState.type === 'food' && swapState.step === 'pickFood') return 'Choose one of the foods in this meal.'
    if (swapState.type === 'food') return 'Pick a replacement option with similar nutrition.'
    if (swapState.type === 'ingredient' && swapState.step === 'pickIngredient') return 'Choose an ingredient from this meal.'
    return 'Pick a replacement option with similar nutrition.'
  })()

  return (
    <div className="swapOverlay" onClick={closeSwapModal} role="dialog" aria-modal="true">
      <div className="swapPanel" onClick={(e) => e.stopPropagation()}>
        <div className="swapHead">
          <div>
            <p className="swapEyebrow">Swap</p>
            <h3>{swapTitle}</h3>
            {swapHint ? <p className="swapHint">{swapHint}</p> : null}
          </div>
          <div className="swapActions">
            {swapState.type === 'food' && swapState.step === 'pickFoodReplacement' ? (
              <button
                type="button"
                className="secondaryBtn"
                onClick={() => setSwapState((prev) => ({
                  ...prev,
                  step: 'pickFood',
                  options: [],
                  selectedLabel: '',
                  error: ''
                }))}
              >
                Back
              </button>
            ) : null}
            {swapState.type === 'ingredient' && swapState.step === 'pickIngredientReplacement' ? (
              <button
                type="button"
                className="secondaryBtn"
                onClick={() => setSwapState((prev) => ({
                  ...prev,
                  step: 'pickIngredient',
                  options: [],
                  selectedLabel: '',
                  error: ''
                }))}
              >
                Back
              </button>
            ) : null}
            <button type="button" className="secondaryBtn" onClick={closeSwapModal}>
              Close
            </button>
          </div>
        </div>

        {swapState.error ? <div className="inlineError">{swapState.error}</div> : null}
        {swapState.loading ? <div className="swapLoading">Loading…</div> : null}

        {swapState.type === 'meal' && swapState.step === 'pickMeal' ? (
          <div className="swapList">
            {swapState.options?.map((o) => {
              const m = o?.meal || {}
              const kcal = Math.round(Number(m?.macros?.caloriesKcal || 0))
              return (
                <button
                  type="button"
                  key={`swap-meal-${m?.Meal_ID}`}
                  className="swapOptionCard"
                  onClick={() => applyMealSwapSelection(o)}
                  disabled={swapState.loading}
                >
                  <div>
                    <strong>{m?.meal_name || 'Meal'}</strong>
                    <span>{kcal} kcal</span>
                  </div>
                  <span className="swapCta">Swap</span>
                </button>
              )
            })}
          </div>
        ) : null}

        {swapState.type === 'food' && swapState.step === 'pickFood' ? (
          <div className="swapList">
            {(swapState.foodChoices || []).map((food, idx) => {
              const qty = Number(food?.quantity || 0)
              const unit = food?.unit ? ` ${food.unit}` : ''
              return (
                <button
                  type="button"
                  key={`swap-food-${idx}`}
                  className="swapOptionCard"
                  onClick={() => loadFoodSwapOptions(food)}
                  disabled={swapState.loading}
                >
                  <div>
                    <strong>{food?.name || 'Food'}</strong>
                    <span>{qty ? `${Math.round(qty)}${unit}` : 'Tap to see options'}</span>
                  </div>
                  <span className="swapCta">Choose</span>
                </button>
              )
            })}
          </div>
        ) : null}

        {swapState.type === 'food' && swapState.step === 'pickFoodReplacement' ? (
          <div className="swapList">
            {(swapState.options || []).map((o, idx) => {
              const r = o?.replacement || {}
              const kcal = Math.round(Number(o?.projectedMealMacros?.caloriesKcal || 0))
              const qty = Math.round(Number(r.quantity || 0))
              const unit = r.unit || ''
              return (
                <button
                  type="button"
                  key={`swap-food-repl-${idx}`}
                  className="swapOptionCard"
                  onClick={() => applyFoodSwapSelection(o)}
                  disabled={swapState.loading}
                >
                  <div>
                    <strong>{r.name || 'Replacement'}</strong>
                    <span>{qty} {unit} · meal {kcal} kcal</span>
                  </div>
                  <span className="swapCta">Swap</span>
                </button>
              )
            })}
          </div>
        ) : null}

        {swapState.type === 'ingredient' && swapState.step === 'pickIngredient' ? (
          <div className="swapList">
            {(swapState.ingredientChoices || []).map((ing, idx) => {
              const qty = Number(ing?.quantity || 0)
              const unit = ing?.unit ? ` ${ing.unit}` : ''
              return (
                <button
                  type="button"
                  key={`swap-ingredient-${idx}`}
                  className="swapOptionCard"
                  onClick={() => loadIngredientSwapOptions(ing)}
                  disabled={swapState.loading}
                >
                  <div>
                    <strong>{ing?.name || 'Ingredient'}</strong>
                    <span>{qty ? `${Math.round(qty * 100) / 100}${unit}` : 'Tap to see options'}</span>
                  </div>
                  <span className="swapCta">Choose</span>
                </button>
              )
            })}
          </div>
        ) : null}

        {swapState.type === 'ingredient' && swapState.step === 'pickIngredientReplacement' ? (
          <div className="swapList">
            {(swapState.options || []).map((o, idx) => {
              const r = o?.replacement || {}
              const kcal = Math.round(Number(o?.projectedMealMacros?.caloriesKcal || 0))
              const qty = Math.round(Number(r.quantity || 0))
              const unit = r.unit || ''
              return (
                <button
                  type="button"
                  key={`swap-ingredient-repl-${idx}`}
                  className="swapOptionCard"
                  onClick={() => applyIngredientSwapSelection(o)}
                  disabled={swapState.loading}
                >
                  <div>
                    <strong>{r.name || 'Replacement'}</strong>
                    <span>{qty} {unit} · meal {kcal} kcal</span>
                  </div>
                  <span className="swapCta">Swap</span>
                </button>
              )
            })}
          </div>
        ) : null}
      </div>
    </div>
  )
}
