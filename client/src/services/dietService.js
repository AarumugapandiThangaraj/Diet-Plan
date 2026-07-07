import { httpJson } from './apiClient.js'

export function fetchStudioMeta({ signal } = {}) {
  return httpJson('/api/studio/meta', { signal })
}

export function fetchActivePlan({ signal } = {}) {
  return httpJson('/api/studio/plan/active', { signal })
}

export function fetchLatestPlan({ signal } = {}) {
  return httpJson('/api/studio/plan/latest', { signal })
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

export function createDraftPlan(profile, { days, mealTimes, poolsByTime }, { signal } = {}) {
  return httpJson('/api/studio/meal-plans', {
    method: 'POST',
    body: { profile, days, mealTimes, poolsByTime },
    signal
  })
}

export function getDraftPlan(planId, { signal } = {}) {
  return httpJson(`/api/studio/meal-plans/${planId}`, {
    method: 'GET',
    signal
  })
}

export function patchDraftPlan(planId, version, operations, { signal } = {}) {
  return httpJson(`/api/studio/meal-plans/${planId}`, {
    method: 'PATCH',
    body: { version, operations },
    signal
  })
}

export function activateDraftPlan(planId, version, { signal } = {}) {
  return httpJson(`/api/studio/meal-plans/${planId}/activate`, {
    method: 'POST',
    body: { version },
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

export function saveDietPlan(days, planData, profile, { signal } = {}) {
  return httpJson('/api/studio/plan/save', {
    method: 'POST',
    body: { days, plan_data: planData, profile },
    signal
  })
}

export function fetchDashboardSummary({ signal } = {}) {
  return httpJson(`/api/studio/dashboard`, {
    method: 'GET',
    signal
  })
}

export function logMealConsumption(mealId, mealDate, consumed, { signal } = {}) {
  return httpJson('/api/studio/dashboard/meals/consume', {
    method: 'POST',
    body: { mealId, mealDate, consumed },
    signal
  })
}

export function logHydration(planDayId, waterMl, { signal } = {}) {
  return httpJson('/api/studio/hydration', {
    method: 'POST',
    body: { planDayId, waterMl },
    signal
  })
}



