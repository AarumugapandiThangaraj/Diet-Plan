import { useState, useEffect, useRef } from 'react'
import { fetchStudioMeta, fetchStudioTargets } from '../services/dietService.js'
import { clampInt, toInt, sortMealTimes } from '../utils/helpers.js'
import { MEAL_TIME_ORDER } from '../config/constants.js'

const DEFAULT_PROFILE = {
  age: '30',
  gender: 'female',
  heightCm: '165',
  weightKg: '60',
  activityLevel: 'sedentary',
  goal: 'skin_repair',
  dietType: 'non_veg',
  cuisineType: 'north_indian',
  allergies: '',
  mealsPerDay: 3,
  mealTimes: ['breakfast', 'lunch', 'dinner']
}

export function useProfile() {
  const [studioMeta, setStudioMeta] = useState(null)
  const [profile, setProfile] = useState({ ...DEFAULT_PROFILE })
  const [targets, setTargets] = useState(null)
  const targetsRequestNonceRef = useRef(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchStudioMeta({ signal: controller.signal })
      .then((data) => setStudioMeta(data))
      .catch(() => {})
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const nonce = (targetsRequestNonceRef.current += 1)
    const controller = new AbortController()
    const t = setTimeout(() => {
      fetchStudioTargets(profile, { signal: controller.signal })
        .then((data) => {
          if (nonce !== targetsRequestNonceRef.current) return
          setTargets(data)
        })
        .catch(() => {})
    }, 220)

    return () => {
      clearTimeout(t)
      controller.abort()
    }
  }, [profile.age, profile.gender, profile.heightCm, profile.weightKg, profile.activityLevel])

  const updateProfile = (patch) => {
    setProfile((prev) => ({ ...prev, ...patch }))
  }

  const updateMealsPerDay = (next) => {
    const selectedMealTimes = sortMealTimes(profile.mealTimes)
    const n = clampInt(toInt(next, profile.mealsPerDay), 2, MEAL_TIME_ORDER.length)
    setProfile((prev) => {
      const ordered = sortMealTimes(prev.mealTimes)
      return {
        ...prev,
        mealsPerDay: n,
        mealTimes: ordered.length > n ? ordered.slice(0, n) : ordered
      }
    })
  }

  const toggleMealTime = (mealTime) => {
    setProfile((prev) => {
      const ordered = sortMealTimes(prev.mealTimes)
      const set = new Set(ordered)
      if (set.has(mealTime)) {
        set.delete(mealTime)
        return { ...prev, mealTimes: MEAL_TIME_ORDER.filter((t) => set.has(t)) }
      }

      if (set.size >= clampInt(toInt(prev.mealsPerDay, profile.mealsPerDay), 2, MEAL_TIME_ORDER.length)) {
        return prev
      }

      set.add(mealTime)
      return { ...prev, mealTimes: MEAL_TIME_ORDER.filter((t) => set.has(t)) }
    })
  }

  const resetProfile = () => {
    setProfile({ ...DEFAULT_PROFILE })
    setTargets(null)
  }

  const validateInputsForMealChoice = () => {
    const selectedMealTimes = sortMealTimes(profile.mealTimes)
    if (!String(profile.heightCm).trim() || !String(profile.weightKg).trim()) {
      return 'Please enter both height and weight values.'
    }
    if (selectedMealTimes.length !== profile.mealsPerDay) {
      return `Please select exactly ${profile.mealsPerDay} meal times.`
    }
    return ''
  }

  return {
    profile,
    studioMeta,
    targets,
    updateProfile,
    updateMealsPerDay,
    toggleMealTime,
    resetProfile,
    validateInputsForMealChoice,
    setTargets
  }
}
