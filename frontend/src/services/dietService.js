import { httpJson } from './apiClient.js'

export function fetchStudioMeta({ signal } = {}) {
  return httpJson('/api/studio/meta', { signal })
}

export function fetchStudioTargets(profile, { signal } = {}) {
  return httpJson('/api/studio/targets', {
    method: 'POST',
    body: { profile },
    signal
  })
}

export function fetchRankedMeals(profile, mealTimes, { limit = 180, signal } = {}) {
  return httpJson('/api/studio/rank', {
    method: 'POST',
    body: { profile, mealTimes, limit },
    signal
  })
}

export function buildPlanFromSelection(profile, { days, mealTimes, poolsByTime, assignmentByTime }, { signal } = {}) {
  return httpJson('/api/studio/plan/build', {
    method: 'POST',
    body: { profile, days, mealTimes, poolsByTime, assignmentByTime },
    signal
  })
}

export function fetchSubstitutesForIngredients(ingredients, { signal } = {}) {
  return httpJson('/api/studio/substitutes/from-ingredients', {
    method: 'POST',
    body: { ingredients },
    signal
  })
}
