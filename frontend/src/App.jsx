import React, { useEffect, useMemo, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

import {
  buildPlanFromSelection,
  fetchRankedMeals,
  fetchStudioMeta,
  fetchStudioTargets,
  fetchSubstitutesForIngredients,
  fetchMagicPickWithPreference
} from './api/studioApi.js'

import AppHeader from './components/common/AppHeader.jsx'
import StepNav from './components/common/StepNav.jsx'
import InputsFlow from './components/common/InputsFlow.jsx'
import MealSelectionFlow from './components/meal/MealSelectionFlow.jsx'
import DragDropPlannerGrid from './components/meal/DragDropPlannerGrid.jsx'
import PlanView from './components/meal/PlanView.jsx'
import { NavigateNext, ArrowBack, AutoAwesome } from '@mui/icons-material'
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
  { label: '7 days ðŸ“…', value: 7 },
  { label: '14 days ðŸ“…', value: 14 },
  { label: '21 days ðŸ“…', value: 21 }
]

const MEAL_TIME_EMOJI = {
  early_morning: 'ðŸŒ…',
  breakfast: 'ðŸ³',
  mid_morning: 'ðŸŒ',
  lunch: 'ðŸ±',
  evening: 'â˜•',
  dinner: 'ðŸ½ï¸',
  bedtime: 'ðŸŒ™'
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
  return String(value || '').toLowerCase().trim()
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
  const [magicLoading, setMagicLoading] = useState(false)

  const [magicFeedback, setMagicFeedback] = useState(null)
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
    ingredients: '',
    choices: [],
    substitutesByKey: {},
    searchResults: []
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

  function openSubstitutionEditor(mealKey, ingredientsText, initialToken = '') {
    const nextOpen = subEditor.openKey === mealKey && !initialToken ? '' : mealKey
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
    const controller = new AbortController()

    setSubEditor({
      openKey: mealKey,
      ingredientToken: '',
      ingredientKey: '',
      loading: true,
      error: '',
      choices: [],
      substitutesByKey: {}
    })

    fetchSubstitutesForIngredients(ingredientsText, {
      signal: controller.signal
    })
      .then((data) => {
        if (nonce !== subRequestNonceRef.current) return
        setSubEditor((prev) => {
          let extra = {}
          if (initialToken) {
            const match = (data?.choices || []).find(c => c.token === initialToken)
            if (match) {
              extra = { ingredientToken: match.token, ingredientKey: match.key }
            }
          }
          return {
            ...prev,
            loading: false,
            choices: Array.isArray(data?.choices) ? data.choices : [],
            substitutesByKey: data?.substitutesByKey || {},
            ...extra
          }
        })
      })
      .catch((e) => {
        if (String(e?.name) === 'AbortError') return
        setSubEditor((prev) => ({
          ...prev,
          loading: false,
          error: String(e?.message || e || 'Failed')
        }))
      })
  }

  /**
   * handleMagicSelect — Automatically picks options for all slots.
   * Now upgraded to support AI-guided preferences if prefText is provided.
   */
  async function handleMagicSelect(prefText = '') {
    if (!selectedMealTimes.length) return

    setMagicFeedback(null) // Reset previous feedback
    let dataToUse = rankedMealsByTime
    
    // FETCH AI-ranked data (or standard with strict filtering)
    setMagicLoading(true)
    try {
      const resp = await fetchMagicPickWithPreference(profile, selectedMealTimes, prefText)
      dataToUse = resp.rankedByTime
      
      // Update feedback for UX
      if (resp.metadata) {
        setMagicFeedback(resp.metadata)
      }

      // Optionally update the general pool so they show up in the lists too
      setRankedMealsByTime(prev => ({ ...prev, ...resp.rankedByTime }))
    } catch (err) {
      setError(String(err?.message || 'AI Magic Pick failed. Using default recommendations.'))
    } finally {
      setMagicLoading(false)
    }

    const newPools = { ...selectedPoolsByTime }
    const newAssignment = { ...assignmentByTime }
    const TARGET_PER_SLOT = 3 

    selectedMealTimes.forEach(mt => {
      const ranked = dataToUse[mt] || []
      const currentPicked = newPools[mt] || []
      
      const pickedIds = new Set(currentPicked.map(m => m.Meal_ID))
      const toAdd = []
      
      for (const m of ranked) {
        if (toAdd.length + currentPicked.length >= TARGET_PER_SLOT) break
        if (!pickedIds.has(m.Meal_ID)) {
          toAdd.push(m)
        }
      }
      
      const fullPool = [...currentPicked, ...toAdd]
      newPools[mt] = fullPool

      if (fullPool.length > 0) {
        newAssignment[mt] = Array.from({ length: selectionDays }, (_, dayIndex) => {
          const picked = fullPool[dayIndex % fullPool.length]
          return String(picked?.Meal_ID || '')
        })
      }
    })

    setSelectedPoolsByTime(newPools)
    setAssignmentByTime(newAssignment)
  }

  function handleToggleMeal(mealTime, meal) {
    // ... logic for toggling
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

  async function replaceIngredientInMeal(dayIndex, mealTime, ingredientLabel, substituteLabel) {
    const meal = getMealFromResult(dayIndex, mealTime)
    const ingredients = String(meal?.ingredients || '')
    if (!ingredients.trim()) return

    const from = String(ingredientLabel || '').trim()
    const to = String(substituteLabel || '').trim()
    if (!from || !to) return

    const re = new RegExp(`\\b${escapeRegExp(from)}\\b`, 'gi')
    const nextIngredients = ingredients.replace(re, to)

    try {
      const response = await fetch('/api/studio/substitutes/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mealId: meal.Meal_ID,
          newIngredients: nextIngredients,
          substName: to
        })
      })
      if (!response.ok) throw new Error('Failed to evaluate substitution')
      const data = await response.json()
      
      // Update result with the backend's "Stable Identity" for this variant
      if (data.meal) {
        updateResultMeal(dayIndex, mealTime, { 
          ...data.meal,
          macros: data.meal.macros || data.meal._macros 
        })
      } else {
        updateResultMeal(dayIndex, mealTime, { ingredients: nextIngredients })
      }
    } catch (err) {
      console.error('Expansion Engine Error:', err)
      updateResultMeal(dayIndex, mealTime, { ingredients: nextIngredients })
    }
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

  // ——— DnD handlers (new — no existing logic changed) ——————————————————————
  function dndAssign(mealTime, dayIndex, mealId) {
    setAssignment(mealTime, dayIndex, mealId)
  }

  function dndUnassign(mealTime, dayIndex) {
    setAssignmentByTime((prev) => {
      const current = Array.isArray(prev?.[mealTime]) ? prev[mealTime].slice() : []
      // restore default (cycle from pool)
      const pool = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      current[dayIndex] = pool.length ? pool[dayIndex % pool.length]?.Meal_ID || '' : ''
      return { ...prev, [mealTime]: current }
    })
  }

  function dndSwap(mealTime, fromDay, toDay) {
    setAssignmentByTime((prev) => {
      const arr = Array.isArray(prev?.[mealTime]) ? prev[mealTime].slice() : []
      const tmp = arr[fromDay]
      arr[fromDay] = arr[toDay]
      arr[toDay] = tmp
      return { ...prev, [mealTime]: arr }
    })
  }

  function handleSubSelectIngredient(choice) {
    setSubEditor((prev) => ({ ...prev, ingredientToken: choice.token, ingredientKey: choice.key }))
  }

  function handleSubSelectSubstitute(dayIndex, mealTime, sub) {
    const fromText = extractIngredientName(subEditor.ingredientToken)
    replaceIngredientInMeal(dayIndex, mealTime, fromText, sub.name)
  }

  function handleCloseSubstitution() {
    setSubEditor({
      openKey: '',
      ingredientToken: '',
      ingredientKey: '',
      loading: false,
      error: '',
      choices: [],
      substitutesByKey: {},
      searchResults: []
    })
  }

  async function handleFoodSearch(query) {
    if (!query || query.length < 2) {
      setSubEditor(prev => ({ ...prev, searchResults: [] }));
      return;
    }
    try {
      const resp = await fetch('/api/studio/food/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 12 })
      });
      const results = await resp.json();
      setSubEditor(prev => ({ ...prev, searchResults: results }));
    } catch (e) {
      console.error("Search failed", e);
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', color: 'text.primary' }}>
      <AppHeader studioMeta={studioMeta} profile={profile} goal={profile.goal} />

      <StepNav view={view} result={result} onStepClick={(id) => {
        if (id === 'inputs') setView('inputs')
        else if (id === 'chooseMeals' && view !== 'inputs') goToMealChoices()
        else if (id === 'selectedMeals' && view !== 'inputs') goToSelectedMeals()
        else if (id === 'plans' && result) setView('plans')
      }} />

      {view === 'inputs' ? (
        <InputsFlow
          profile={profile}
          targets={targets}
          planDays={planDays}
          selectedMealTimes={selectedMealTimes}
          mealsPerDay={mealsPerDay}
          error={error}
          onProfileChange={updateProfile}
          onPlanDaysChange={updatePlanDays}
          onMealsPerDayChange={updateMealsPerDay}
          onToggleMealTime={toggleMealTime}
          onNext={goToMealChoices}
          onReset={resetInputs}
        />
      ) : view === 'chooseMeals' ? (
        <MealSelectionFlow
          selectedMealTimes={selectedMealTimes}
          rankedMealsByTime={rankedMealsByTime}
          selectedPoolsByTime={selectedPoolsByTime}
          rankLoading={rankLoading}
          magicLoading={magicLoading}
          error={error}
          isSelectionComplete={selectedMealTimes.every(
            (mt) => Array.isArray(selectedPoolsByTime[mt]) && selectedPoolsByTime[mt].length > 0
          )}
          onToggleMeal={toggleMealInPool}
          onMagicSelect={handleMagicSelect}
          onNext={() => setView('selectedMeals')}
          onBack={() => setView('inputs')}
          magicFeedback={magicFeedback}
        />
      ) : view === 'selectedMeals' ? (
        <DragDropPlannerGrid
          selectedMealTimes={selectedMealTimes}
          selectedPoolsByTime={selectedPoolsByTime}
          assignmentByTime={assignmentByTime}
          selectionDays={selectionDays}
          error={error}
          onAssign={dndAssign}
          onUnassign={dndUnassign}
          onSwap={dndSwap}
          onNext={buildResultFromSelectedMeals}
          onBack={() => setView('chooseMeals')}
        />
      ) : (
        <PlanView
          dayPlans={dayPlans}
          daysCount={daysCount}
          totalsByDay={totalsByDay}
          targets={targets}
          result={result}
          subEditor={subEditor}
          onBack={() => setView('selectedMeals')}
          onOpenSubstitution={openSubstitutionEditor}
          onReplaceIngredient={replaceIngredientInMeal}
          onSelectIngredient={handleSubSelectIngredient}
          onSelectSubstitute={handleSubSelectSubstitute}
          onFoodSearch={handleFoodSearch}
          onCloseSubstitution={handleCloseSubstitution}
        />
      )}

      <Box component="footer" sx={{ textAlign: 'center', py: 3, color: 'text.secondary' }}>
        <Typography variant="caption">
          Data source: <code>Diet Plan/data/master_meals_updated.json</code>
        </Typography>
      </Box>
    </Box>
  )
}
