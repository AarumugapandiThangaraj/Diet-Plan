import { calculateDailyTargets } from './nutrition.js'

export const MEAL_DISTRIBUTION = {
  early_morning: 0.05,
  breakfast: 0.3,
  mid_morning: 0.1,
  lunch: 0.25,
  evening: 0.1,
  dinner: 0.15,
  bedtime: 0.05
}

export const MEAL_TIME_ORDER = Object.keys(MEAL_DISTRIBUTION)

const NON_VEG_KEYWORDS = ['egg', 'chicken', 'fish', 'mutton', 'lamb', 'prawn', 'shrimp', 'meat']

function normalizeDietTypeForFiltering(dietType) {
  const dt = String(dietType || '').trim().toLowerCase()
  if (dt === 'veg') return 'veg'
  // Product requirement: "Non-veg" means show both veg + non-veg.
  if (dt === 'non_veg' || dt === 'non-veg' || dt === 'nonveg') return 'any'
  if (dt === 'any') return 'any'
  return 'any'
}

function mulberry32(seed) {
  let a = (seed >>> 0) || 1
  return function rng() {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function shuffleInPlace(arr, rng) {
  const random = typeof rng === 'function' ? rng : Math.random
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1))
    const tmp = arr[i]
    arr[i] = arr[j]
    arr[j] = tmp
  }
  return arr
}

function toNumber(x) {
  const n = Number(x)
  return Number.isFinite(n) ? n : 0
}

export function normalizeTag(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
}

export function normalizeGoal(goal) {
  const g = normalizeTag(goal)
  if (g === 'skin_repair') return 'skin_repair'
  if (g === 'hair_repair') return 'hair_repair'
  return g
}

export function parseNutritiveValues(text) {
  const t = String(text || '')

  const m = (re) => {
    const match = t.match(re)
    return match ? toNumber(match[1]) : 0
  }

  return {
    caloriesKcal: m(/(\d+(?:\.\d+)?)\s*kcal/i),
    proteinG: m(/protein\s*(\d+(?:\.\d+)?)\s*g/i),
    carbsG: m(/(?:carbs?|carbohydrates?)\s*(\d+(?:\.\d+)?)\s*g/i),
    fatG: m(/fat\s*(\d+(?:\.\d+)?)\s*g/i),
    fiberG: m(/(?:fiber|fibre)\s*(\d+(?:\.\d+)?)\s*g/i)
  }
}

export function splitKeywords(raw) {
  return String(raw || '')
    .toLowerCase()
    .split(/[,;/]|\band\b/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function containsAny(haystack, keywords) {
  if (!haystack || !keywords?.length) return false
  const h = String(haystack).toLowerCase()
  return keywords.some((k) => k && h.includes(k))
}

function isProbablyNonVeg(meal) {
  const text = `${meal.ingredients || ''}\n${meal.meal_name || ''}`.toLowerCase()

  // Avoid obvious false-positives like "eggless" / "meatless"
  if (/\beggless\b/i.test(text)) {
    // do nothing
  }

  const patterns = [
    { re: /\beggs?\b/i, neg: /\beggless\b/i },
    { re: /\bchicken\b/i },
    { re: /\bfish\b/i },
    { re: /\bmutton\b/i },
    { re: /\blamb\b/i },
    { re: /\b(?:prawn|shrimp|shrimps)\b/i },
    { re: /\bmeat\b/i, neg: /\bmeatless\b/i }
  ]

  return patterns.some((p) => p.re.test(text) && !(p.neg && p.neg.test(text)))
}

function isMealAllowed(meal, filters) {
  const allergyKeywords = filters.allergyKeywords || []
  if (allergyKeywords.length) {
    const combined = `${meal.ingredients || ''}\n${meal.caution || ''}`
    if (containsAny(combined, allergyKeywords)) return false
  }

  const dietType = normalizeDietTypeForFiltering(filters.dietType)
  if (dietType === 'veg') {
    const dt = String(meal.diet_type || '').toLowerCase()
    if (dt === 'non_veg') return false
    if (dt === '' && isProbablyNonVeg(meal)) return false
  }

  return true
}

function relativeError(actual, target) {
  const t = Math.max(0, toNumber(target))
  const a = Math.max(0, toNumber(actual))
  if (t === 0) return a === 0 ? 0 : 1
  return Math.abs(a - t) / t
}

function getMacroWeights(bmiCategory) {
  const c = String(bmiCategory || '').trim().toLowerCase()

  // Default scoring (balanced)
  const base = { calories: 1.8, protein: 1.2, carbs: 0.6, fat: 0.6 }

  // Product heuristics:
  // - Underweight: emphasize hitting calories/protein more than being low-fat.
  // - Overweight/Obese: emphasize being closer to fat target.
  if (c === 'underweight') return { calories: 2.0, protein: 1.35, carbs: 0.55, fat: 0.45 }
  if (c === 'overweight') return { calories: 1.8, protein: 1.25, carbs: 0.55, fat: 0.95 }
  if (c === 'obese') return { calories: 1.85, protein: 1.3, carbs: 0.5, fat: 1.05 }
  return base
}

function macroScore(macros, expected, weights) {
  const w = weights || { calories: 1.8, protein: 1.2, carbs: 0.6, fat: 0.6 }
  return (
    w.calories * relativeError(macros.caloriesKcal, expected.caloriesKcal) +
    w.protein * relativeError(macros.proteinG, expected.proteinG) +
    w.carbs * relativeError(macros.carbsG, expected.carbsG) +
    w.fat * relativeError(macros.fatG, expected.fatG)
  )
}

function scorePartial(totals, targets, usedWeight, weights) {
  const expected = {
    caloriesKcal: targets.caloriesKcal * usedWeight,
    proteinG: targets.proteinG * usedWeight,
    carbsG: targets.carbsG * usedWeight,
    fatG: targets.fatG * usedWeight
  }

  return macroScore(totals, expected, weights)
}

function scoreFinal(totals, targets, weights) {
  return macroScore(totals, targets, weights)
}

function addTotals(totals, macros) {
  return {
    caloriesKcal: totals.caloriesKcal + (macros.caloriesKcal || 0),
    proteinG: totals.proteinG + (macros.proteinG || 0),
    carbsG: totals.carbsG + (macros.carbsG || 0),
    fatG: totals.fatG + (macros.fatG || 0),
    fiberG: totals.fiberG + (macros.fiberG || 0)
  }
}

function getCandidatesForMealTime(
  allMeals,
  mealTime,
  filters,
  perMealTarget,
  maxCandidates,
  options = {}
) {
  const {
    expectedMacros = null,
    macroWeights = null,
    rng = null,
    usedMealIds = null,
    avoidRepeats = false,
    allowRelaxDiet = false
  } = options

  const used = usedMealIds instanceof Set ? usedMealIds : null

  const candidates = allMeals
    .filter((m) => String(m.meal_time) === mealTime)
    .filter((m) => normalizeGoal(m.goal) === filters.goal)
    .filter((m) => isMealAllowed(m, filters))
    .filter((m) => {
      if (!avoidRepeats || !used) return true
      const id = m.Meal_ID
      return !id || !used.has(id)
    })
    .map((m) => ({
      ...m,
      _macros: parseNutritiveValues(m.nutritive_values)
    }))
    .map((m) => {
      const cals = m._macros.caloriesKcal || 0
      const fallbackExpected = {
        caloriesKcal: perMealTarget || 0,
        proteinG: 0,
        carbsG: 0,
        fatG: 0
      }

      const expected = expectedMacros || fallbackExpected
      const score = macroScore(m._macros, expected, macroWeights)

      // keep a tiny calorie pull even if expected macros omit other fields
      const calNudge = perMealTarget > 0 ? 0.15 * Math.abs(cals - perMealTarget) / perMealTarget : 0

      return { meal: m, score: score + calNudge }
    })
    .sort((a, b) => a.score - b.score)
    .slice(0, Math.max(1, maxCandidates))
    .map((x) => x.meal)

  if (candidates.length && options.randomize !== false) {
    shuffleInPlace(candidates, rng)
  }

  if (candidates.length) return { candidates, usedFallback: null }

  // Fallback 1: relax goal (keep diet preference)
  const cand2 = allMeals
    .filter((m) => String(m.meal_time) === mealTime)
    .filter((m) => isMealAllowed(m, filters))
    .filter((m) => {
      if (!avoidRepeats || !used) return true
      const id = m.Meal_ID
      return !id || !used.has(id)
    })
    .map((m) => ({ ...m, _macros: parseNutritiveValues(m.nutritive_values) }))
    .slice(0, Math.max(1, maxCandidates))

  if (cand2.length) return { candidates: cand2, usedFallback: 'relaxed_goal' }

  // Fallback 2 (optional): relax diet type too (ONLY if explicitly allowed)
  const shouldRelaxDiet = allowRelaxDiet && String(filters.dietType || 'any') !== 'any'
  if (shouldRelaxDiet) {
    const relaxedDiet = { ...filters, dietType: 'any' }
    const cand3 = allMeals
      .filter((m) => String(m.meal_time) === mealTime)
      .filter((m) => isMealAllowed(m, relaxedDiet))
      .filter((m) => {
        if (!avoidRepeats || !used) return true
        const id = m.Meal_ID
        return !id || !used.has(id)
      })
      .map((m) => ({ ...m, _macros: parseNutritiveValues(m.nutritive_values) }))
      .slice(0, Math.max(1, maxCandidates))

    return { candidates: cand3, usedFallback: 'relaxed_goal_and_diet' }
  }

  return { candidates: [], usedFallback: 'no_candidates' }
}

export function generateDailyPlan({ meals, profile, options = {} }) {
  const targets = calculateDailyTargets(profile)
  const goal = normalizeGoal(profile.goal)
  const macroWeights = getMacroWeights(targets.bmiCategory)

  const filters = {
    goal,
    dietType: normalizeDietTypeForFiltering(profile.dietType),
    allergyKeywords: splitKeywords(profile.allergies)
  }

  const beamSize = Math.max(5, options.beamSize || 60)
  const perMealCandidates = Math.max(5, options.perMealCandidates || 25)
  const randomness = Math.max(0, toNumber(options.randomness ?? 0.0015))
  const seed = toNumber(options.seed)
  const rng = Number.isFinite(seed) ? mulberry32(seed) : Math.random
  const avoidRepeats = Boolean(options.avoidRepeats)
  const usedMealIds = options.usedMealIds instanceof Set ? options.usedMealIds : null
  const pickTop = Math.max(1, Math.round(toNumber(options.pickTop ?? 5)))

  const targetsTotals = {
    caloriesKcal: targets.dailyCalories,
    proteinG: targets.proteinG,
    carbsG: targets.carbsG,
    fatG: targets.fatG
  }

  const fallbacksUsed = {}
  const candidatesByTime = {}

  for (const mealTime of MEAL_TIME_ORDER) {
    const perMealTarget = targets.dailyCalories * (MEAL_DISTRIBUTION[mealTime] || 0)
    const expectedMacros = {
      caloriesKcal: targetsTotals.caloriesKcal * (MEAL_DISTRIBUTION[mealTime] || 0),
      proteinG: targetsTotals.proteinG * (MEAL_DISTRIBUTION[mealTime] || 0),
      carbsG: targetsTotals.carbsG * (MEAL_DISTRIBUTION[mealTime] || 0),
      fatG: targetsTotals.fatG * (MEAL_DISTRIBUTION[mealTime] || 0)
    }

    const { candidates, usedFallback } = getCandidatesForMealTime(
      meals,
      mealTime,
      filters,
      perMealTarget,
      perMealCandidates,
      {
        expectedMacros,
        macroWeights,
        rng,
        randomize: options.randomize,
        usedMealIds,
        avoidRepeats,
        allowRelaxDiet: Boolean(options.allowRelaxDiet)
      }
    )
    candidatesByTime[mealTime] = candidates
    if (usedFallback) fallbacksUsed[mealTime] = usedFallback
  }

  let beam = [
    {
      chosen: {},
      totals: { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 },
      usedWeight: 0
    }
  ]

  for (const mealTime of MEAL_TIME_ORDER) {
    const weight = MEAL_DISTRIBUTION[mealTime] || 0
    const optionsForTime = candidatesByTime[mealTime] || []
    if (!optionsForTime.length) continue

    const next = []
    for (const state of beam) {
      for (const meal of optionsForTime) {
        const totals = addTotals(state.totals, meal._macros)
        const usedWeight = state.usedWeight + weight
        const chosen = { ...state.chosen, [mealTime]: meal }
        const score = scorePartial(totals, targetsTotals, usedWeight, macroWeights) + (randomness ? rng() * randomness : 0)
        next.push({ state: { chosen, totals, usedWeight }, score })
      }
    }

    next.sort((a, b) => a.score - b.score)
    beam = next.slice(0, beamSize).map((x) => x.state)
  }

  const ranked = beam
    .slice()
    .sort((a, b) => scoreFinal(a.totals, targetsTotals, macroWeights) - scoreFinal(b.totals, targetsTotals, macroWeights))

  const topK = Math.min(pickTop, ranked.length)
  const best = ranked[Math.floor(rng() * topK)] || ranked[0]

  const plan = {}
  for (const mealTime of MEAL_TIME_ORDER) {
    const meal = best?.chosen?.[mealTime]
    if (!meal) continue

    plan[mealTime] = {
      Meal_ID: meal.Meal_ID,
      meal_name: meal.meal_name,
      time: meal.time || '',
      serving_size: meal.serving_size || '',
      ingredients: meal.ingredients || '',
      method: meal.method || '',
      caution: meal.caution || '',
      nutritive_values: meal.nutritive_values || '',
      macros: meal._macros
    }
  }

  return {
    targets,
    totals: best?.totals,
    plan,
    distribution: MEAL_DISTRIBUTION,
    filters,
    fallbacksUsed
  }
}

export function rankMealsForMealTime({ meals, profile, mealTime, options = {} }) {
  const targets = options.targets || calculateDailyTargets(profile)
  const goal = normalizeGoal(profile.goal)
  const macroWeights = getMacroWeights(targets.bmiCategory)

  const filters = {
    goal,
    dietType: normalizeDietTypeForFiltering(profile.dietType),
    allergyKeywords: splitKeywords(profile.allergies)
  }

  const weight = MEAL_DISTRIBUTION[mealTime] || 0
  const expectedMacros = {
    caloriesKcal: targets.dailyCalories * weight,
    proteinG: targets.proteinG * weight,
    carbsG: targets.carbsG * weight,
    fatG: targets.fatG * weight
  }

  const minOptions = Math.max(1, Math.round(toNumber(options.minOptions ?? 7)))
  const limit = Math.max(minOptions, Math.round(toNumber(options.limit ?? 120)))
  const allowRelaxGoal = options.allowRelaxGoal !== false
  const allowRelaxDiet = Boolean(options.allowRelaxDiet)

  const all = Array.isArray(meals) ? meals : []

  const scoreMeals = (list) =>
    list
      .map((m) => {
        const macros = parseNutritiveValues(m.nutritive_values)
        const score = macroScore(macros, expectedMacros, macroWeights)
        return { ...m, _macros: macros, _score: score }
      })
      .sort((a, b) => (a._score || 0) - (b._score || 0))

  const strict = scoreMeals(
    all
      .filter((m) => String(m.meal_time) === String(mealTime))
      .filter((m) => normalizeGoal(m.goal) === filters.goal)
      .filter((m) => isMealAllowed(m, filters))
  )

  const ranked = []
  const seen = new Set()
  const pushUnique = (items) => {
    for (const m of items) {
      const id = m?.Meal_ID
      if (!id || seen.has(id)) continue
      seen.add(id)
      ranked.push(m)
      if (ranked.length >= limit) break
    }
  }

  pushUnique(strict)

  if (allowRelaxGoal && ranked.length < minOptions) {
    const relaxedGoal = scoreMeals(
      all
        .filter((m) => String(m.meal_time) === String(mealTime))
        .filter((m) => isMealAllowed(m, filters))
    )
    pushUnique(relaxedGoal)
  }

  if (allowRelaxDiet && ranked.length < minOptions && String(filters.dietType || 'any') !== 'any') {
    const relaxedDietFilters = { ...filters, dietType: 'any' }
    const relaxedDiet = scoreMeals(
      all
        .filter((m) => String(m.meal_time) === String(mealTime))
        .filter((m) => isMealAllowed(m, relaxedDietFilters))
    )
    pushUnique(relaxedDiet)
  }

  return { targets, filters, mealTime, ranked }
}

export function generateMealPlan({ meals, profile, options = {} }) {
  const days = Math.max(1, Math.min(21, Math.round(toNumber(options.days ?? 1))))
  if (days === 1) {
    return {
      ...generateDailyPlan({ meals, profile, options }),
      days,
      plans: null,
      totalsByDay: null,
      totalsAll: null
    }
  }

  const avoidRepeatsAcrossDays = Boolean(options.avoidRepeatsAcrossDays)
  const usedMealIds = avoidRepeatsAcrossDays ? new Set() : null
  const baseSeed = Number.isFinite(toNumber(options.seed)) ? toNumber(options.seed) : Date.now()

  const totalsAll = { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 }
  const totalsByDay = []
  const plans = []
  const fallbacksByDay = []

  let lastTargets = null
  let lastFilters = null

  for (let dayIndex = 0; dayIndex < days; dayIndex += 1) {
    const daySeed = baseSeed + dayIndex * 10007
    const dayResult = generateDailyPlan({
      meals,
      profile,
      options: {
        ...options,
        seed: daySeed,
        usedMealIds: usedMealIds || undefined,
        avoidRepeats: avoidRepeatsAcrossDays
      }
    })

    lastTargets = dayResult.targets
    lastFilters = dayResult.filters

    plans.push(dayResult.plan)
    totalsByDay.push(dayResult.totals)
    fallbacksByDay.push(dayResult.fallbacksUsed)

    if (usedMealIds) {
      for (const mealTime of MEAL_TIME_ORDER) {
        const id = dayResult?.plan?.[mealTime]?.Meal_ID
        if (id) usedMealIds.add(id)
      }
    }

    if (dayResult?.totals) {
      totalsAll.caloriesKcal += dayResult.totals.caloriesKcal || 0
      totalsAll.proteinG += dayResult.totals.proteinG || 0
      totalsAll.carbsG += dayResult.totals.carbsG || 0
      totalsAll.fatG += dayResult.totals.fatG || 0
      totalsAll.fiberG += dayResult.totals.fiberG || 0
    }
  }

  return {
    targets: lastTargets,
    filters: lastFilters,
    distribution: MEAL_DISTRIBUTION,
    days,
    plans,
    totalsByDay,
    totalsAll,
    fallbacksUsed: fallbacksByDay
  }
}
