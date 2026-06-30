import { useState, useEffect, useRef, useMemo } from 'react'
import {
  fetchRankedMeals,
  buildPlanFromSelection,
  fetchActivePlan,
  saveDietPlan
} from '../services/dietService.js'
import {
  fetchMealSwapOptions,
  applyMealSwap,
  fetchFoodSwapOptions,
  applyFoodSwap,
  fetchIngredientSwapOptions,
  applyIngredientSwap
} from '../services/swapService.js'
import {
  clampInt,
  toInt,
  sortMealTimes,
  windowed,
  dedupeMealsById,
  withRecomputedTotals
} from '../utils/helpers.js'
import { MEAL_TIME_ORDER, MEAL_TIME_LABELS } from '../config/constants.js'

export function usePlanner(profile, targets, setTargets) {
  const [view, setView] = useState('inputs')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [planDays, setPlanDays] = useState(7)
  const [justGenerated, setJustGenerated] = useState(false)

  const [rankedMealsByTime, setRankedMealsByTime] = useState({})
  const [rankLoading, setRankLoading] = useState(false)
  const [generateLoading, setGenerateLoading] = useState(false)

  const [carouselByTime, setCarouselByTime] = useState({})
  const [selectedPoolsByTime, setSelectedPoolsByTime] = useState({})
  const [assignmentByTime, setAssignmentByTime] = useState({})
  const generationNonceRef = useRef(0)

  const [swapState, setSwapState] = useState(null)
  const [selectedMealDetails, setSelectedMealDetails] = useState(null)

  const selectionDays = clampInt(toInt(planDays, 7), 7, 21)
  const selectedPlan = result?.plan || {}

  useEffect(() => {
    fetchActivePlan()
      .then((data) => {
        if (data && Object.keys(data).length > 0) {
          setResult(data)
          if (data.targets && setTargets) {
            setTargets(data.targets)
          }
          setView('plans')
        }
      })
      .catch((err) => {
        console.log("No active plan or error:", err)
      })
  }, [setTargets])

  const dayPlans = useMemo(() => {
    if (Array.isArray(result?.plans) && result.plans.length) return result.plans
    return [selectedPlan]
  }, [result, selectedPlan])

  const selectedMealTimes = useMemo(() => sortMealTimes(profile.mealTimes), [profile.mealTimes])

  // Build plan summary for the agent (meal names for each day/mealtime)
  const planSummary = useMemo(() => {
    if (!result) return null
    const days = result.days || 1
    const mealTimes = result.mealTimes || selectedMealTimes
    if (days <= 1) {
      const plan = result.plan || {}
      const meals = {}
      for (const mt of mealTimes) {
        const item = plan[mt]
        if (item) {
          const foods = Array.isArray(item.foods_struct) ? item.foods_struct : []
          const names = foods.map(f => (f?.name || '').trim()).filter(Boolean)
          meals[mt] = {
            name: names.length ? names.join(' with ') : (item.meal_name || 'Unknown'),
            id: item.Meal_ID || ''
          }
        }
      }
      return [{ day: 1, meals }]
    }
    const plans = Array.isArray(result.plans) ? result.plans : []
    return plans.map((plan, i) => {
      const meals = {}
      for (const mt of mealTimes) {
        const item = plan?.[mt]
        if (item) {
          const foods = Array.isArray(item.foods_struct) ? item.foods_struct : []
          const names = foods.map(f => (f?.name || '').trim()).filter(Boolean)
          meals[mt] = {
            name: names.length ? names.join(' with ') : (item.meal_name || 'Unknown'),
            id: item.Meal_ID || ''
          }
        }
      }
      return { day: i + 1, meals }
    })
  }, [result, selectedMealTimes])

  // Build selectedPoolIds: { breakfast: ["id1", "id2"], lunch: [...] }
  const selectedPoolIds = useMemo(() => {
    const out = {}
    for (const mt of Object.keys(selectedPoolsByTime || {})) {
      const pool = selectedPoolsByTime[mt]
      if (Array.isArray(pool)) {
        out[mt] = pool.map(m => m?.Meal_ID).filter(Boolean)
      }
    }
    return out
  }, [selectedPoolsByTime])

  const isSelectionComplete = useMemo(() => {
    if (!selectedMealTimes.length) return false
    return selectedMealTimes.every((mealTime) => {
      const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      return list.length >= 1
    })
  }, [selectedMealTimes, selectedPoolsByTime])

  useEffect(() => {
    if (view !== 'chooseMeals') return
    if (!selectedMealTimes.length) return

    setRankLoading(true)
    setError('')
    const controller = new AbortController()

    fetchRankedMeals(profile, selectedMealTimes, { limit: 180, signal: controller.signal })
      .then((data) => {
        setRankedMealsByTime(data?.rankedByTime || {})
        if (data?.targets && setTargets) setTargets(data.targets)
      })
      .catch((e) => {
        if (String(e?.name) === 'AbortError') return
        setError(String(e?.message || e || 'Failed to load meal options from backend.'))
      })
      .finally(() => setRankLoading(false))

    return () => controller.abort()
  }, [view, profile, selectedMealTimes, setTargets])
  useEffect(() => {
    if (!result) return
    console.log('result', result)
  }, [result])
  const updateResultMeal = async (dayIndex, mealTime, patch) => {
    if (!result) return
    const days = result.days || 1
    const safeDayIndex = Math.max(0, Math.min(days - 1, dayIndex || 0))
    let nextState;

    if (days === 1) {
      const plan = { ...(result.plan || {}) }
      const item = plan?.[mealTime]
      if (!item) return
      plan[mealTime] = { ...item, ...patch }
      nextState = withRecomputedTotals({ ...result, plan })
    } else {
      const plans = Array.isArray(result.plans) ? result.plans.slice() : []
      const dayPlan = { ...(plans[safeDayIndex] || {}) }
      const item = dayPlan?.[mealTime]
      if (!item) return
      dayPlan[mealTime] = { ...item, ...patch }
      plans[safeDayIndex] = dayPlan
      nextState = withRecomputedTotals({ ...result, plans })
    }

    setResult(nextState)

    try {
      await saveDietPlan(nextState.days || 1, nextState, profile)
    } catch (e) {
      console.error("Failed to auto-save swapped plan:", e)
    }
  }

  const getMealFromResult = (dayIndex, mealTime) => {
    if (!result) return null
    const days = result.days || 1
    const safeDayIndex = Math.max(0, Math.min(days - 1, dayIndex || 0))
    if (days === 1) return result?.plan?.[mealTime] || null
    return result?.plans?.[safeDayIndex]?.[mealTime] || null
  }

  const closeSwapModal = () => {
    setSwapState(null)
  }

  const handleDragStart = (event, payload) => {
    try {
      event.dataTransfer.setData('application/json', JSON.stringify(payload))
    } catch {
      event.dataTransfer.setData('text/plain', '')
    }
    event.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (event) => {
    event.preventDefault()
    event.currentTarget.classList.add('isOver')
  }

  const handleDragLeave = (event) => {
    event.currentTarget.classList.remove('isOver')
  }

  const setAssignment = (mealTime, dayIndex, mealId) => {
    setAssignmentByTime((prev) => {
      const current = Array.isArray(prev?.[mealTime]) ? prev[mealTime] : []
      const next = current.slice()
      const targetId = String(mealId || '')
      if (!targetId) return prev
      next[dayIndex] = targetId
      return { ...prev, [mealTime]: next }
    })
  }

  const handleDropOnDay = (event, mealTime, dayIndex) => {
    event.preventDefault()
    event.currentTarget.classList.remove('isOver')
    const raw = event.dataTransfer.getData('application/json')
    if (!raw) return
    let data = null
    try {
      data = JSON.parse(raw)
    } catch {
      return
    }
    if (!data || data.mealTime !== mealTime) return

    if (Number.isFinite(Number(data.sourceDayIndex))) {
      const sourceIndex = Number(data.sourceDayIndex)
      if (sourceIndex === dayIndex) return
      setAssignmentByTime((prev) => {
        const current = Array.isArray(prev?.[mealTime]) ? prev[mealTime] : []
        const next = current.slice()
        if (!next.length) return prev
        const temp = next[sourceIndex]
        next[sourceIndex] = next[dayIndex]
        next[dayIndex] = temp
        return { ...prev, [mealTime]: next }
      })
      return
    }

    const mealId = String(data.mealId || '')
    if (!mealId) return
    setAssignment(mealTime, dayIndex, mealId)
  }

  const getTargetMacrosForMealTime = (mealTime) => {
    const dist = {
      early_morning: 0.05,
      breakfast: 0.3,
      mid_morning: 0.1,
      lunch: 0.25,
      evening: 0.1,
      dinner: 0.15,
      bedtime: 0.05
    }
    const activeMealTimes = Array.isArray(result?.mealTimes) && result.mealTimes.length
      ? result.mealTimes
      : selectedMealTimes
    const selected = Array.isArray(activeMealTimes) ? activeMealTimes.filter((t) => dist[t]) : []
    const total = selected.length ? selected.reduce((sum, t) => sum + (dist[t] || 0), 0) : 0
    const w = total > 0 ? (dist[mealTime] || 0) / total : dist[mealTime] || 0
    return {
      caloriesKcal: Number(targets?.dailyCalories || 0) * w,
      proteinG: Number(targets?.proteinG || 0) * w,
      carbsG: Number(targets?.carbsG || 0) * w,
      fatG: Number(targets?.fatG || 0) * w,
      fiberG: Number(targets?.fiberG || 0) * w
    }
  }

  const handleSwapWholeMeal = async (dayIndex, mealTime) => {
    try {
      setError('')
      const meal = getMealFromResult(dayIndex, mealTime)
      if (!meal?.Meal_ID) {
        setError('No meal is assigned in this slot.')
        return
      }

      const allowedMealIds = Array.isArray(selectedPoolsByTime?.[mealTime])
        ? selectedPoolsByTime[mealTime].map((m) => m?.Meal_ID).filter(Boolean)
        : []

      const targetMacros = getTargetMacrosForMealTime(mealTime)

      const data = await fetchMealSwapOptions(profile, mealTime, meal.Meal_ID, {
        targetMacros,
        allowedMealIds,
        topN: 5
      })
      const options = Array.isArray(data?.options) ? data.options : []
      if (!options.length) {
        setError('No whole-meal swap options found for this slot.')
        return
      }

      setSwapState({
        open: true,
        type: 'meal',
        step: 'pickMeal',
        dayIndex,
        mealTime,
        meal,
        options,
        loading: false,
        error: ''
      })
    } catch (e) {
      setError(String(e?.message || e || 'Failed to swap whole meal.'))
    }
  }

  const handleSwapFood = async (dayIndex, mealTime) => {
    try {
      setError('')
      const meal = getMealFromResult(dayIndex, mealTime)
      if (!meal) {
        setError('No meal is assigned in this slot.')
        return
      }

      const foods = Array.isArray(meal.foods_struct) ? meal.foods_struct : []
      if (!foods.length) {
        setError('No structured foods are available for this meal.')
        return
      }

      setSwapState({
        open: true,
        type: 'food',
        step: 'pickFood',
        dayIndex,
        mealTime,
        meal,
        foodChoices: foods,
        options: [],
        selectedLabel: '',
        loading: false,
        error: ''
      })
    } catch (e) {
      setError(String(e?.message || e || 'Failed to swap food item.'))
    }
  }

  const handleSwapIngredient = async (dayIndex, mealTime) => {
    try {
      setError('')
      const meal = getMealFromResult(dayIndex, mealTime)
      if (!meal) {
        setError('No meal is assigned in this slot.')
        return
      }

      const ingredients = Array.isArray(meal.ingredients_struct) ? meal.ingredients_struct : []
      if (!ingredients.length) {
        setError('No structured ingredients are available for this meal.')
        return
      }

      setSwapState({
        open: true,
        type: 'ingredient',
        step: 'pickIngredient',
        dayIndex,
        mealTime,
        meal,
        ingredientChoices: ingredients,
        options: [],
        selectedLabel: '',
        loading: false,
        error: ''
      })
    } catch (e) {
      setError(String(e?.message || e || 'Failed to swap ingredient.'))
    }
  }

  // const isSelectionComplete = useMemo(() => {
  //   if (!selectedMealTimes.length) return false
  //   return selectedMealTimes.every((mealTime) => {
  //     const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
  //     return list.length >= 1
  //   })
  // }, [selectedMealTimes, selectedPoolsByTime])

  const goToMealChoices = (validationMsg) => {
    if (validationMsg) {
      setError(validationMsg)
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

  const refreshMealTimeOptions = (mealTime) => {
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

  const toggleMealInPool = (mealTime, meal) => {
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

  const autoSelectTopMeals = () => {
    setError('')
    setSelectedPoolsByTime((prev) => {
      const next = { ...(prev || {}) }
      for (const mealTime of selectedMealTimes) {
        const ranked = rankedMealsByTime?.[mealTime] || []
        const top7 = ranked.slice(0, 7)
        if (!top7.length) continue

        const existing = Array.isArray(next?.[mealTime]) ? next[mealTime] : []
        const existingIds = new Set(existing.map((m) => m?.Meal_ID).filter(Boolean))
        const remainingSlots = Math.max(0, 3 - existingIds.size)
        if (remainingSlots <= 0) continue

        const picks = []
        for (const meal of top7) {
          if (picks.length >= remainingSlots) break
          if (!meal?.Meal_ID) continue
          if (existingIds.has(meal.Meal_ID)) continue
          picks.push(meal)
        }

        const merged = dedupeMealsById([...existing, ...picks]).slice(0, 7)
        next[mealTime] = merged
      }
      return next
    })
  }

  const goToSelectedMeals = () => {
    setError('')
    for (const mealTime of selectedMealTimes) {
      const list = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
      if (list.length < 1) {
        setError(`Please select at least 1 meal for ${MEAL_TIME_LABELS[mealTime] || mealTime}.`)
        return
      }
    }

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

  const buildResultFromSelectedMeals = () => {
    setError('')
    setGenerateLoading(true)
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
      .then((res) => {
        if (nonce !== generationNonceRef.current) return

        // Fetch the active plan that was just saved by the backend
        return fetchActivePlan().then((activeData) => {
          if (nonce !== generationNonceRef.current) return
          console.log('Active plan data retrieved:', activeData)

          setResult(activeData)
          setJustGenerated(true)

          if (activeData?.targets && setTargets) setTargets(activeData.targets)
          setGenerateLoading(false)
          setView('plans')
        })
      })
      .catch((e) => {
        if (nonce !== generationNonceRef.current) return
        setGenerateLoading(false)
        setError(String(e?.message || e || 'Failed to build plan.'))
      })
  }

  const getDisplayMealName = (item) => {
    const foods = Array.isArray(item?.foods_struct) ? item.foods_struct : []
    const names = foods.map((food) => String(food?.name || '').trim()).filter(Boolean)
    if (names.length >= 2) return `${names[0]} with ${names.slice(1).join(' with ')}`
    if (names.length === 1) return names[0]
    return item?.meal_name || 'No meal selected'
  }

  const applyMealSwapSelection = async (option) => {
    if (!swapState) return
    setSwapState((prev) => ({ ...prev, loading: true, error: '' }))
    try {
      const chosen = option?.meal || option
      const applied = await applyMealSwap(chosen)
      const nextMeal = applied?.meal || chosen
      updateResultMeal(swapState.dayIndex, swapState.mealTime, nextMeal)
      closeSwapModal()
    } catch (e) {
      setSwapState((prev) => ({ ...prev, loading: false, error: String(e?.message || e || 'Failed to swap meal.') }))
    }
  }

  const loadFoodSwapOptions = async (food) => {
    if (!swapState?.meal) return
    const foodName = String(food?.name || '').trim()
    if (!foodName) return
    setSwapState((prev) => ({ ...prev, loading: true, error: '', selectedLabel: foodName }))
    try {
      const optionsRes = await fetchFoodSwapOptions(swapState.meal, foodName, { topN: 5 })
      console.log('Food swap options:', optionsRes)
      const options = Array.isArray(optionsRes?.options) ? optionsRes.options : []
      if (!options.length) {
        setSwapState((prev) => ({ ...prev, loading: false, error: 'No food-swap options found for that item.' }))
        return
      }
      setSwapState((prev) => ({ ...prev, step: 'pickFoodReplacement', options, loading: false }))
    } catch (e) {
      setSwapState((prev) => ({ ...prev, loading: false, error: String(e?.message || e || 'Failed to load food swap options.') }))
    }
  }

  const applyFoodSwapSelection = async (option) => {
    if (!swapState?.meal) return
    setSwapState((prev) => ({ ...prev, loading: true, error: '' }))
    try {
      const applied = await applyFoodSwap(swapState.meal, option)
      const nextMeal = applied?.meal
      if (nextMeal) updateResultMeal(swapState.dayIndex, swapState.mealTime, nextMeal)
      closeSwapModal()
    } catch (e) {
      setSwapState((prev) => ({ ...prev, loading: false, error: String(e?.message || e || 'Failed to swap food.') }))
    }
  }

  const loadIngredientSwapOptions = async (ingredient) => {
    if (!swapState?.meal) return
    const ingredientName = String(ingredient?.name || '').trim()
    if (!ingredientName) return
    setSwapState((prev) => ({ ...prev, loading: true, error: '', selectedLabel: ingredientName }))
    try {
      const optionsRes = await fetchIngredientSwapOptions(swapState.meal, ingredientName, { topN: 5 })
      const options = Array.isArray(optionsRes?.options) ? optionsRes.options : []
      if (!options.length) {
        setSwapState((prev) => ({ ...prev, loading: false, error: 'No ingredient-swap options found for that ingredient.' }))
        return
      }
      setSwapState((prev) => ({ ...prev, step: 'pickIngredientReplacement', options, loading: false }))
    } catch (e) {
      setSwapState((prev) => ({ ...prev, loading: false, error: String(e?.message || e || 'Failed to load ingredient options.') }))
    }
  }

  const applyIngredientSwapSelection = async (option) => {
    if (!swapState?.meal) return
    setSwapState((prev) => ({ ...prev, loading: true, error: '' }))
    try {
      const applied = await applyIngredientSwap(swapState.meal, option)
      const nextMeal = applied?.meal
      if (nextMeal) updateResultMeal(swapState.dayIndex, swapState.mealTime, nextMeal)
      closeSwapModal()
    } catch (e) {
      setSwapState((prev) => ({ ...prev, loading: false, error: String(e?.message || e || 'Failed to swap ingredient.') }))
    }
  }

  const resetPlanner = () => {
    setError('')
    setPlanDays(7)
    setResult(null)
    setSelectedPoolsByTime({})
    setAssignmentByTime({})
    setCarouselByTime({})
    setJustGenerated(false)
    setView('inputs')
  }

  const updatePlanDays = (next) => {
    const days = clampInt(toInt(next, 7), 7, 21)
    setPlanDays(days)
    setError('')
    setResult(null)
    setSelectedPoolsByTime({})
    setAssignmentByTime({})
    setCarouselByTime({})
    setJustGenerated(false)
    setView('inputs')
  }

  return {
    view,
    setView,
    result,
    setResult,
    error,
    setError,
    generateLoading,
    planDays,
    setPlanDays,
    rankedMealsByTime,
    rankLoading,
    carouselByTime,
    setCarouselByTime,
    selectedPoolsByTime,
    setSelectedPoolsByTime,
    assignmentByTime,
    setAssignmentByTime,
    swapState,
    setSwapState,
    selectedMealDetails,
    setSelectedMealDetails,
    selectionDays,
    dayPlans,
    selectedMealTimes,
    planSummary,
    selectedPoolIds,
    updateResultMeal,
    getMealFromResult,
    closeSwapModal,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDropOnDay,
    getTargetMacrosForMealTime,
    handleSwapWholeMeal,
    handleSwapFood,
    handleSwapIngredient,
    isSelectionComplete,
    goToMealChoices,
    refreshMealTimeOptions,
    toggleMealInPool,
    autoSelectTopMeals,
    goToSelectedMeals,
    buildResultFromSelectedMeals,
    getDisplayMealName,
    applyMealSwapSelection,
    loadFoodSwapOptions,
    applyFoodSwapSelection,
    loadIngredientSwapOptions,
    applyIngredientSwapSelection,
    resetPlanner,
    updatePlanDays,
    justGenerated,
    setJustGenerated
  }
}
