import { httpJson } from './apiClient.js'

export function fetchMealSwapOptions(
  profile,
  mealTime,
  currentMealId,
  { targetMacros = null, excludeMealIds = [], allowedMealIds = [], topN = 5, signal } = {}
) {
  return httpJson('/api/studio/swap/meal/options', {
    method: 'POST',
    body: { profile, mealTime, currentMealId, targetMacros, excludeMealIds, allowedMealIds, topN },
    signal
  })
}

export function applyMealSwap(meal, { signal } = {}) {
  return httpJson('/api/studio/swap/meal/apply', {
    method: 'POST',
    body: { meal },
    signal
  })
}

export function fetchFoodSwapOptions(meal, foodName, { topN = 5, signal } = {}) {
  return httpJson('/api/studio/swap/food/options', {
    method: 'POST',
    body: { meal, foodName, topN },
    signal
  })
}

export function applyFoodSwap(meal, option, { signal } = {}) {
  return httpJson('/api/studio/swap/food/apply', {
    method: 'POST',
    body: { meal, option },
    signal
  })
}

export function fetchIngredientSwapOptions(meal, ingredientQuery, { topN = 5, signal } = {}) {
  return httpJson('/api/studio/swap/ingredient/options', {
    method: 'POST',
    body: { meal, ingredientQuery, topN },
    signal
  })
}

export function applyIngredientSwap(meal, option, { signal } = {}) {
  return httpJson('/api/studio/swap/ingredient/apply', {
    method: 'POST',
    body: { meal, option },
    signal
  })
}
