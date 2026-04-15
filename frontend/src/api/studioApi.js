const DEFAULT_HEADERS = {
  'Content-Type': 'application/json'
}

async function httpJson(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(path, {
    method,
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
    signal
  })

  if (!res.ok) {
    let detail = ''
    try {
      const data = await res.json()
      detail = data?.detail ? String(data.detail) : JSON.stringify(data)
    } catch {
      try {
        detail = await res.text()
      } catch {
        detail = ''
      }
    }
    throw new Error(detail || `Request failed: ${res.status}`)
  }

  return res.json()
}

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

export function fetchMagicPickWithPreference(profile, mealTimes, preferenceText, { signal } = {}) {
  return httpJson('/api/studio/magic-pick-with-pref', {
    method: 'POST',
    body: { profile, mealTimes, preferenceText },
    signal
  })
}
