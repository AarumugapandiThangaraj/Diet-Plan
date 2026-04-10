import React, { useEffect, useMemo, useRef, useState } from 'react'

import cornerSticker from './assets/whatsapp-sticker.webp'

import {
  buildPlanFromSelection,
  fetchRankedMeals,
  fetchStudioMeta,
  fetchStudioTargets,
  fetchSubstitutesForIngredients
} from './api/studioApi.js'

const GOALS = [
  { label: 'Skin Repair', value: 'skin_repair', description: 'Focus on skin recovery foods' },
  { label: 'Hair Repair', value: 'hair_repair', description: 'Focus on scalp and hair nutrients' }
]

const ACTIVITY = [
  { label: 'Sedentary', value: 'sedentary' },
  { label: 'Light', value: 'light' },
  { label: 'Moderate', value: 'moderate' },
  { label: 'Heavy', value: 'heavy' }
]

const DIET = [
  { label: 'Veg', value: 'veg' },
  { label: 'Non-Veg', value: 'non_veg' }
]

const PLAN_DAYS = [
  { label: '7 days 📅', value: 7 },
  { label: '14 days 📅', value: 14 },
  { label: '21 days 📅', value: 21 }
]

const MEAL_TIME_EMOJI = {
  early_morning: '🌅',
  breakfast: '🍳',
  mid_morning: '🍌',
  lunch: '🍱',
  evening: '☕',
  dinner: '🍽️',
  bedtime: '🌙'
}

const MEAL_TIME_ORDER = [
  'early_morning',
  'breakfast',
  'mid_morning',
  'lunch',
  'evening',
  'dinner',
  'bedtime'
]

const MEAL_TIME_LABELS = {
  early_morning: 'Early Morning',
  breakfast: 'Breakfast',
  mid_morning: 'Mid-Morning',
  lunch: 'Lunch',
  evening: 'Evening',
  dinner: 'Dinner',
  bedtime: 'Bedtime'
}

function toInt(x, fallback) {
  const n = Number.parseInt(String(x), 10)
  return Number.isFinite(n) ? n : fallback
}

function clampInt(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

function sortMealTimes(times) {
  const set = new Set(Array.isArray(times) ? times : [])
  return MEAL_TIME_ORDER.filter((t) => set.has(t))
}

function windowed(arr, start, size) {
  const list = Array.isArray(arr) ? arr : []
  if (!list.length) return []
  const out = []
  const s = Math.max(0, Math.floor(start || 0))
  for (let i = 0; i < size; i += 1) {
    out.push(list[(s + i) % list.length])
    if (out.length >= list.length) break
  }
  return out
}

function normalizeName(value) {
  return String(value || '')
    .toLowerCase()
    .trim()
    .replace(/[()]/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function escapeRegExp(s) {
  return String(s || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function extractIngredientName(token) {
  const t = String(token || '').trim()
  if (!t) return ''
  const noParen = t.replace(/\([^)]*\)/g, ' ').trim()
  const cutAtNumber = noParen.replace(/\b\d+(?:\.\d+)?\b.*$/i, '').trim()
  return cutAtNumber || noParen
}

function dedupeMealsById(meals) {
  const out = []
  const seen = new Set()
  for (const m of Array.isArray(meals) ? meals : []) {
    const id = m?.Meal_ID
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push(m)
  }
  return out
}

function Progress({ label, value, target, unit }) {
  const pct = target > 0 ? Math.min(100, Math.round((value / target) * 100)) : 0
  return (
    <div className="progressRow">
      <div className="progressMeta">
        <span>{label}</span>
        <strong>
          {Math.round(value)}{unit} <span>/ {Math.round(target)}{unit}</span>
        </strong>
      </div>
      <div className="progressTrack">
        <div className="progressValue" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function OptionGroup({ label, options, selected, onSelect, className = '' }) {
  return (
    <div className={`optionGroup ${className}`.trim()}>
      <div className="optionLabel">{label}</div>
      <div className="chipGrid">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`choiceChip ${selected === option.value ? 'isActive' : ''}`}
            onClick={() => onSelect(option.value)}
          >
            <span className="choiceTitle">{option.label}</span>
            {option.description ? <span className="choiceDesc">{option.description}</span> : null}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [studioMeta, setStudioMeta] = useState(null)

  const [view, setView] = useState('inputs')
  const [profile, setProfile] = useState({
    age: '30',
    gender: 'female',
    heightCm: '165',
    weightKg: '60',
    activityLevel: 'sedentary',
    goal: 'skin_repair',
    dietType: 'non_veg',
    allergies: '',
    mealsPerDay: 3,
    mealTimes: ['breakfast', 'lunch', 'dinner']
  })

  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [planDays, setPlanDays] = useState(7)

  const [targets, setTargets] = useState(null)
  const targetsRequestNonceRef = useRef(0)

  const [rankedMealsByTime, setRankedMealsByTime] = useState({})
  const [rankLoading, setRankLoading] = useState(false)

  const [carouselByTime, setCarouselByTime] = useState({})
  const [selectedPoolsByTime, setSelectedPoolsByTime] = useState({})
  const [assignmentByTime, setAssignmentByTime] = useState({})
  const generationNonceRef = useRef(0)
  const subRequestNonceRef = useRef(0)

  const [subEditor, setSubEditor] = useState({
    openKey: '',
    ingredientToken: '',
    ingredientKey: '',
    loading: false,
    error: '',
    choices: [],
    substitutesByKey: {}
  })

  const selectionDays = clampInt(toInt(planDays, 7), 7, 21)
  const selectedPlan = result?.plan || {}
  const dayPlans = useMemo(() => {
    if (Array.isArray(result?.plans) && result.plans.length) return result.plans
    return [selectedPlan]
  }, [result, selectedPlan])

  const daysCount = result?.days || 1
  const totals = result?.totals || null
  const totalsByDay = useMemo(() => {
    if (Array.isArray(result?.totalsByDay) && result.totalsByDay.length) return result.totalsByDay
    return totals ? [totals] : []
  }, [result, totals])

  const selectedMealTimes = useMemo(() => sortMealTimes(profile.mealTimes), [profile.mealTimes])
  const mealsPerDay = clampInt(toInt(profile.mealsPerDay, 3), 2, MEAL_TIME_ORDER.length)

  useEffect(() => {
    const controller = new AbortController()
    fetchStudioMeta({ signal: controller.signal })
      .then((data) => setStudioMeta(data))
      .catch(() => {
        // keep silent; UI can run without this
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    // Debounce to keep typing smooth while still running calculations on the backend.
    const nonce = (targetsRequestNonceRef.current += 1)
    const controller = new AbortController()
    const t = setTimeout(() => {
      fetchStudioTargets(profile, { signal: controller.signal })
        .then((data) => {
          if (nonce !== targetsRequestNonceRef.current) return
          setTargets(data)
        })
        .catch(() => {
          // don't spam errors while user types
        })
    }, 220)

    return () => {
      clearTimeout(t)
      controller.abort()
    }
  }, [profile.age, profile.gender, profile.heightCm, profile.weightKg, profile.activityLevel])

  useEffect(() => {
    if (view !== 'chooseMeals') return
    if (!selectedMealTimes.length) return

    setRankLoading(true)
    setError('')
    const controller = new AbortController()

    fetchRankedMeals(profile, selectedMealTimes, { limit: 180, signal: controller.signal })
      .then((data) => {
        setRankedMealsByTime(data?.rankedByTime || {})
        if (data?.targets) setTargets(data.targets)
      })
      .catch((e) => {
        if (String(e?.name) === 'AbortError') return
        setError(String(e?.message || e || 'Failed to load meal options from backend.'))
      })
      .finally(() => setRankLoading(false))

    return () => controller.abort()
  }, [view, profile, selectedMealTimes])

  function openSubstitutionEditor(mealKey, ingredientsText) {
    const nextOpen = subEditor.openKey === mealKey ? '' : mealKey
    if (!nextOpen) {
      setSubEditor({
        openKey: '',
        ingredientToken: '',
        ingredientKey: '',
        loading: false,
        error: '',
        choices: [],
        substitutesByKey: {}
      })
      return
    }

    const nonce = (subRequestNonceRef.current += 1)
    setSubEditor({
      openKey: mealKey,
      ingredientToken: '',
      ingredientKey: '',
      loading: true,
      error: '',
      choices: [],
      substitutesByKey: {}
    })

    fetchSubstitutesForIngredients(String(ingredientsText || ''))
      .then((data) => {
        if (nonce !== subRequestNonceRef.current) return
        setSubEditor((prev) => ({
          ...prev,
          loading: false,
          choices: Array.isArray(data?.choices) ? data.choices : [],
          substitutesByKey: data?.substitutesByKey || {}
        }))
      })
      .catch((e) => {
        if (nonce !== subRequestNonceRef.current) return
        setSubEditor((prev) => ({ ...prev, loading: false, error: String(e?.message || e || 'Failed to load substitutes.') }))
      })
  }

  function updateResultMeal(dayIndex, mealTime, patch) {
    setResult((prev) => {
      if (!prev) return prev

      const days = prev.days || 1
      const safeDayIndex = Math.max(0, Math.min(days - 1, dayIndex || 0))

      if (days === 1) {
        const plan = { ...(prev.plan || {}) }
        const item = plan?.[mealTime]
        if (!item) return prev
        plan[mealTime] = { ...item, ...patch }
        return { ...prev, plan }
      }

      const plans = Array.isArray(prev.plans) ? prev.plans.slice() : []
      const dayPlan = { ...(plans[safeDayIndex] || {}) }
      const item = dayPlan?.[mealTime]
      if (!item) return prev
      dayPlan[mealTime] = { ...item, ...patch }
      plans[safeDayIndex] = dayPlan
      return { ...prev, plans }
    })
  }

  function getMealFromResult(dayIndex, mealTime) {
    if (!result) return null
    const days = result.days || 1
    const safeDayIndex = Math.max(0, Math.min(days - 1, dayIndex || 0))
    if (days === 1) return result?.plan?.[mealTime] || null
    return result?.plans?.[safeDayIndex]?.[mealTime] || null
  }

  function replaceIngredientInMeal(dayIndex, mealTime, ingredientLabel, substituteLabel) {
    const meal = getMealFromResult(dayIndex, mealTime)
    const ingredients = String(meal?.ingredients || '')
    if (!ingredients.trim()) return

    const from = String(ingredientLabel || '').trim()
    const to = String(substituteLabel || '').trim()
    if (!from || !to) return

    const re = new RegExp(`\\b${escapeRegExp(from)}\\b`, 'gi')
    const nextIngredients = ingredients.replace(re, to)
    updateResultMeal(dayIndex, mealTime, { ingredients: nextIngredients })
  }

  function updateProfile(patch) {
    setProfile((prev) => ({ ...prev, ...patch }))
  }

  const isSelectionComplete = useMemo(() => {
    if (!selectedMealTimes.length) return false
    return selectedMealTimes.every((mealTime) => {
      const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      return list.length >= 1
    })
  }, [selectedMealTimes, selectedPoolsByTime, selectionDays])

  function updateMealsPerDay(next) {
    const n = clampInt(toInt(next, mealsPerDay), 2, MEAL_TIME_ORDER.length)
    setProfile((prev) => {
      const ordered = sortMealTimes(prev.mealTimes)
      return {
        ...prev,
        mealsPerDay: n,
        mealTimes: ordered.length > n ? ordered.slice(0, n) : ordered
      }
    })
  }

  function toggleMealTime(mealTime) {
    setError('')
    setProfile((prev) => {
      const ordered = sortMealTimes(prev.mealTimes)
      const set = new Set(ordered)
      if (set.has(mealTime)) {
        set.delete(mealTime)
        return { ...prev, mealTimes: MEAL_TIME_ORDER.filter((t) => set.has(t)) }
      }

      if (set.size >= clampInt(toInt(prev.mealsPerDay, mealsPerDay), 2, MEAL_TIME_ORDER.length)) {
        return prev
      }

      set.add(mealTime)
      return { ...prev, mealTimes: MEAL_TIME_ORDER.filter((t) => set.has(t)) }
    })
  }

  function resetInputs() {
    setProfile({
      age: '30',
      gender: 'female',
      heightCm: '165',
      weightKg: '60',
      activityLevel: 'sedentary',
      goal: 'skin_repair',
      dietType: 'non_veg',
      allergies: '',
      mealsPerDay: 3,
      mealTimes: ['breakfast', 'lunch', 'dinner']
    })
    setError('')
    setPlanDays(7)
    setResult(null)
    setSelectedPoolsByTime({})
    setAssignmentByTime({})
    setCarouselByTime({})
    setView('inputs')
  }

  function updatePlanDays(next) {
    const days = clampInt(toInt(next, 7), 7, 21)
    setPlanDays(days)
    setError('')
    setResult(null)
    setSelectedPoolsByTime({})
    setAssignmentByTime({})
    setCarouselByTime({})
    setView('inputs')
  }

  function validateInputsForMealChoice() {
    if (!String(profile.heightCm).trim() || !String(profile.weightKg).trim()) {
      return 'Please enter both height and weight values.'
    }

    if (selectedMealTimes.length !== mealsPerDay) {
      return `Please select exactly ${mealsPerDay} meal times.`
    }

    return ''
  }

  function goToMealChoices() {
    setError('')
    const msg = validateInputsForMealChoice()
    if (msg) {
      setError(msg)
      return
    }

    const nextCarousel = {}
    for (const t of selectedMealTimes) nextCarousel[t] = { ids: [], cursor: 0 }
    setCarouselByTime(nextCarousel)
    setRankedMealsByTime({})
    setSelectedPoolsByTime({})
    setAssignmentByTime({})
    setResult(null)
    setView('chooseMeals')
  }

  function refreshMealTimeOptions(mealTime) {
    setError('')
    const ranked = rankedMealsByTime?.[mealTime] || []
    const top7 = ranked.slice(0, 7)
    const windowSize = 3
    const picked = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
    const pickedIdSet = new Set(picked.map((m) => String(m?.Meal_ID || '')).filter(Boolean))
    const candidates = top7.filter((m) => !pickedIdSet.has(String(m?.Meal_ID || '')))
    if (candidates.length <= windowSize) return

    setCarouselByTime((prev) => {
      const currentCursor = Number.isFinite(Number(prev?.[mealTime]?.cursor)) ? Number(prev[mealTime].cursor) : 0
      const nextCursor = (Math.max(0, currentCursor) + windowSize) % candidates.length
      return { ...prev, [mealTime]: { cursor: nextCursor } }
    })
  }

  function toggleMealInPool(mealTime, meal) {
    setError('')
    const id = meal?.Meal_ID
    if (!id) return

    setSelectedPoolsByTime((prev) => {
      const current = Array.isArray(prev?.[mealTime]) ? prev[mealTime] : []
      const already = current.some((m) => m?.Meal_ID === id)

      if (already) {
        const nextList = current.filter((m) => m?.Meal_ID !== id)
        return { ...prev, [mealTime]: nextList }
      }

      // prevent repeats across the entire plan selection
      const allSelectedIds = new Set(
        Object.values(prev || {}).flatMap((list) => (Array.isArray(list) ? list : [])).map((m) => m?.Meal_ID).filter(Boolean)
      )
      if (allSelectedIds.has(id)) {
        setError('That meal is already selected in another slot. Please choose a different meal.')
        return prev
      }

      if (current.length >= 7) {
        setError(`You can select up to 7 ${MEAL_TIME_LABELS[mealTime] || mealTime} meals. Selected meals will repeat in a cycle across ${selectionDays} days.`)
        return prev
      }

      const nextList = dedupeMealsById([...current, meal])
      return { ...prev, [mealTime]: nextList }
    })
  }

  function goToSelectedMeals() {
    setError('')
    for (const mealTime of selectedMealTimes) {
      const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      if (list.length < 1) {
        setError(`Please select at least 1 meal for ${MEAL_TIME_LABELS[mealTime] || mealTime}.`)
        return
      }
    }

    // initialize default assignment (Day 1..N) using selection order
    const nextAssignment = {}
    for (const mealTime of selectedMealTimes) {
      const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      nextAssignment[mealTime] = Array.from({ length: selectionDays }, (_, dayIndex) => {
        const picked = list[dayIndex % list.length]
        return String(picked?.Meal_ID || '')
      })
    }
    setAssignmentByTime(nextAssignment)
    setView('selectedMeals')
  }

  function setAssignment(mealTime, dayIndex, mealId) {
    setAssignmentByTime((prev) => {
      const current = Array.isArray(prev?.[mealTime]) ? prev[mealTime] : []
      const next = current.slice()
      const targetId = String(mealId || '')
      if (!targetId) return prev

      next[dayIndex] = targetId
      return { ...prev, [mealTime]: next }
    })
  }

  function buildResultFromSelectedMeals() {
    setError('')

    generationNonceRef.current += 1
    const nonce = generationNonceRef.current

    const poolsByTime = {}
    for (const mealTime of selectedMealTimes) {
      const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      poolsByTime[mealTime] = list.map((m) => String(m?.Meal_ID || '')).filter(Boolean)
    }

    buildPlanFromSelection(
      profile,
      {
        days: selectionDays,
        mealTimes: selectedMealTimes,
        poolsByTime,
        assignmentByTime
      }
    )
      .then((data) => {
        if (nonce !== generationNonceRef.current) return
        setResult(data)
        if (data?.targets) setTargets(data.targets)
        setView('plans')
      })
      .catch((e) => {
        if (nonce !== generationNonceRef.current) return
        setError(String(e?.message || e || 'Failed to build plan.'))
      })
  }

  return (
    <div className="appShell">
      <img className="cornerSticker" src={cornerSticker} alt="" aria-hidden="true" />
      <header className="hero">
        <div>
          <p className="eyebrow">Personalized Nutrition Planner 🥗</p>
          <h1>Diet Plan Studio 🥗✨</h1>
          <p className="heroText">Set your profile 🧾, review automatic BMI/BMR/TDEE 🧮, and generate a cleaner one-day plan view 📅.</p>
        </div>
        <div className="heroBadges">
          <div className="heroPill">Meals in dataset 🍽️: <strong>{studioMeta?.mealsCount ?? '—'}</strong></div>
          <div className="heroPill">Current goal 🎯: <strong>{profile.goal === 'hair_repair' ? 'Hair Repair' : 'Skin Repair'}</strong></div>
        </div>
      </header>

      <nav className="stepNav" aria-label="Form steps">
        <button type="button" className={`stepBtn ${view === 'inputs' ? 'active' : ''}`} onClick={() => setView('inputs')}>
          1. Inputs & meal times 🧾⏰
        </button>
        <button
          type="button"
          className={`stepBtn ${view === 'chooseMeals' ? 'active' : ''}`}
          onClick={() => view !== 'inputs' && setView('chooseMeals')}
          disabled={view === 'inputs'}
        >
          2. Choose meals 🍽️
        </button>
        <button
          type="button"
          className={`stepBtn ${view === 'selectedMeals' ? 'active' : ''}`}
          onClick={() => view !== 'inputs' && setView('selectedMeals')}
          disabled={view === 'inputs'}
        >
          3. Arrange days 📅
        </button>
        <button
          type="button"
          className={`stepBtn ${view === 'plans' ? 'active' : ''}`}
          onClick={() => result && setView('plans')}
          disabled={!result}
        >
          4. Plan ✅
        </button>
      </nav>

      {view === 'inputs' ? (
        <main className="inputsLayout">
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
              <button type="button" className="primaryBtn" onClick={goToMealChoices}>
                Next: Choose meals 🍽️
              </button>
              <button type="button" className="secondaryBtn" onClick={resetInputs}>
                Reset inputs 🔄
              </button>
            </div>

            {error ? <div className="inlineError">{error}</div> : null}
          </section>

          <section className="panel calcPanel">
            <div className="panelHead">
              <h2>Metric Hub 🧮</h2>
              <p>These values update live while you type.</p>
            </div>

            <div className="metricGrid">
              <div className="metricCard">
                <span className="metricLabel">BMI ⚖️</span>
                <strong>{targets?.bmi ?? '—'}</strong>
                <span className={`bmiTag ${String(targets?.bmiCategory || 'Normal').toLowerCase()}`}>{targets?.bmiCategory || 'Normal'}</span>
              </div>
              <div className="metricCard">
                <span className="metricLabel">Target 🎯</span>
                <strong>{targets?.targetWeightKg ?? '—'}</strong>
                <span className="metricUnit">kg (BMI {targets?.targetBmi ?? '—'})</span>
              </div>
              <div className="metricCard">
                <span className="metricLabel">BMR 🔥</span>
                <strong>{targets?.bmr ?? '—'}</strong>
                <span className="metricUnit">kcal/day</span>
              </div>
              <div className="metricCard">
                <span className="metricLabel">TDEE ⚡</span>
                <strong>{targets?.tdee ?? '—'}</strong>
                <span className="metricUnit">kcal/day</span>
              </div>
              <div className="metricCard">
                <span className="metricLabel">Water 💧</span>
                <strong>{targets?.waterL ?? '—'}</strong>
                <span className="metricUnit">L/day</span>
              </div>
            </div>
          </section>
        </main>
      ) : view === 'chooseMeals' ? (
        <main className="plansLayout">
          <section className="panel planSummary">
            <div className="planSummaryHead">
              <div />
              <button type="button" className="secondaryBtn" onClick={() => setView('inputs')}>
                Back to inputs ⬅️
              </button>
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
                    <div style={{ color: 'var(--muted)' }}>{rankLoading ? 'Loading meals…' : 'No meals found for this meal time with the current filters.'}</div>
                  )}
                </div>
              </section>
            )
          })}

          <section className="panel">
            <div className="actions" style={{ marginTop: 0 }}>
              <button type="button" className="primaryBtn" onClick={goToSelectedMeals} disabled={!isSelectionComplete}>
                Continue: Arrange days 📅
              </button>
              <button type="button" className="secondaryBtn" onClick={() => setView('inputs')}>
                Back ⬅️
              </button>
            </div>
          </section>
        </main>
      ) : view === 'selectedMeals' ? (
        <main className="plansLayout">
          <section className="panel planSummary">
            <div className="planSummaryHead">
              <div>
                <h2>Arrange days 📅</h2>
                <p>Assign meals for each day and meal time 🗓️. Repeats are allowed 🔁.</p>
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
                    <p style={{ margin: '6px 0 0', color: 'var(--muted)' }}>Assign meals across Day 1…Day {selectionDays} 📅 (repeats allowed 🔁).</p>
                  </div>
                </div>

                <div
                  style={{
                    marginTop: 12,
                    display: 'grid',
                    gap: 10,
                    gridTemplateColumns: `repeat(${Math.min(selectionDays, 4)}, minmax(0, 1fr))`
                  }}
                >
                  {Array.from({ length: selectionDays }, (_, dayIndex) => dayIndex).map((dayIndex) => (
                    <div key={`arr-${mealTime}-d${dayIndex}`} className="metricCard" style={{ padding: 12 }}>
                      <label className="field" style={{ gap: 6 }}>
                        <span>Day {dayIndex + 1} 📅</span>
                        <select
                          value={String(assignment?.[dayIndex] || '')}
                          onChange={(e) => setAssignment(mealTime, dayIndex, e.target.value)}
                        >
                          {pool.map((m) => (
                            <option key={`${mealTime}-${m.Meal_ID}`} value={String(m.Meal_ID)}>
                              {m.meal_name}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                  ))}
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
      ) : (
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

          <section className="planGrid">
            {dayPlans.map((dayPlan, dayIndex) => (
              <div key={`day-${dayIndex + 1}`} className="dayBlock">
                {daysCount > 1 ? <h3 className="dayTitle">Day {dayIndex + 1} 📅</h3> : null}
                {totalsByDay?.[dayIndex] ? (
                  <div className="dayTotals">
                    <div className="dayTotalsHead">Day {dayIndex + 1} nutrients 🧬</div>
                    <div className="progressWrap">
                      <Progress label="Calories 🔥" value={totalsByDay[dayIndex]?.caloriesKcal || 0} target={targets?.dailyCalories || 0} unit="" />
                      <Progress label="Protein 💪" value={totalsByDay[dayIndex]?.proteinG || 0} target={targets?.proteinG || 0} unit="g" />
                      <Progress label="Carbs 🍞" value={totalsByDay[dayIndex]?.carbsG || 0} target={targets?.carbsG || 0} unit="g" />
                      <Progress label="Fat 🥑" value={totalsByDay[dayIndex]?.fatG || 0} target={targets?.fatG || 0} unit="g" />
                      <Progress label="Fiber 🥦" value={totalsByDay[dayIndex]?.fiberG || 0} target={targets?.fiberG || 0} unit="g" />
                    </div>
                  </div>
                ) : null}
                <div className="dayGrid">
                  {(result?.mealTimes || MEAL_TIME_ORDER).map((mealTime) => {
                    const item = dayPlan?.[mealTime]
                    const mealKey = `${dayIndex}-${mealTime}`
                    const isOpen = subEditor.openKey === mealKey
                    const ingredientsText = String(item?.ingredients || '')
                    const ingredientChoices = isOpen ? subEditor.choices : []

                    return (
                      <article key={`${dayIndex}-${mealTime}`} className="planCard">
                        <header className="planCardHead">
                          <div>
                            <p className="slotLabel">
                              {MEAL_TIME_LABELS[mealTime] || mealTime} {MEAL_TIME_EMOJI[mealTime] || ''}
                            </p>
                            <h3>{item?.meal_name || 'No meal selected'}</h3>
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

                        <div className="actions" style={{ marginTop: 12 }}>
                          <button
                            type="button"
                            className="secondaryBtn"
                            onClick={() => openSubstitutionEditor(mealKey, ingredientsText)}
                            disabled={!ingredientsText.trim()}
                          >
                            Substitute ingredients
                          </button>
                        </div>

                        {isOpen ? (
                          <div className="detailBlock" style={{ marginTop: 10 }}>
                            <h4>Choose an ingredient</h4>
                            {subEditor.loading ? (
                              <p className="line" style={{ color: 'var(--muted)' }}>Loading substitutes…</p>
                            ) : null}
                            {subEditor.error ? (
                              <p className="line" style={{ color: 'var(--muted)' }}>{subEditor.error}</p>
                            ) : null}
                            {ingredientChoices.length ? (
                              <div className="chipGrid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
                                {ingredientChoices.map((c) => (
                                  <button
                                    key={`${mealKey}-${c.key}-${c.token}`}
                                    type="button"
                                    className={`choiceChip ${subEditor.ingredientToken === c.token ? 'isActive' : ''}`}
                                    onClick={() => setSubEditor((prev) => ({ ...prev, ingredientToken: c.token, ingredientKey: c.key }))}
                                  >
                                    <span className="choiceTitle">{c.label}</span>
                                    <span className="choiceDesc">Tap to see substitutes</span>
                                  </button>
                                ))}
                              </div>
                            ) : (
                              <p className="line" style={{ color: 'var(--muted)' }}>No substitutable ingredients detected for this meal.</p>
                            )}

                            {subEditor.ingredientKey ? (
                              <div style={{ marginTop: 12 }}>
                                <h4>Available substitutes</h4>
                                <div className="chipGrid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
                                  {(() => {
                                    const list = Array.isArray(subEditor.substitutesByKey?.[subEditor.ingredientKey])
                                      ? subEditor.substitutesByKey[subEditor.ingredientKey]
                                      : []
                                    const fromText = extractIngredientName(subEditor.ingredientToken)
                                    if (!list.length) {
                                      return (
                                        <p className="line" style={{ color: 'var(--muted)' }}>No substitute options found.</p>
                                      )
                                    }
                                    return list.map((s) => (
                                      <button
                                        key={`${mealKey}-sub-${s.norm}`}
                                        type="button"
                                        className="choiceChip"
                                        onClick={() => {
                                          replaceIngredientInMeal(dayIndex, mealTime, fromText, s.name)
                                        }}
                                      >
                                        <span className="choiceTitle">Replace with {s.name}</span>
                                        {s.details?.preparation ? <span className="choiceDesc">{s.details.preparation}</span> : <span className="choiceDesc">Tap to replace</span>}
                                      </button>
                                    ))
                                  })()}
                                </div>
                              </div>
                            ) : null}
                          </div>
                        ) : null}

                        {item?.ingredients ? (
                          <div className="detailBlock">
                            <h4>Ingredients</h4>
                            <p>{item.ingredients}</p>
                          </div>
                        ) : null}

                        {item?.method ? (
                          <div className="detailBlock">
                            <h4>Method</h4>
                            <p>{item.method}</p>
                          </div>
                        ) : null}

                        {item?.caution ? <p className="cautionLine">{item.caution}</p> : null}
                      </article>
                    )
                  })}
                </div>
              </div>
            ))}
          </section>
        </main>
      )}

      <footer className="footerText">
        Data source: <span className="mono">Diet Plan/data/master_meals_updated.json</span>
      </footer>
    </div>
  )
}
