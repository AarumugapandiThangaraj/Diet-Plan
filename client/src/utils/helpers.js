import { MEAL_TIME_ORDER } from '../config/constants.js'

export function toInt(x, fallback) {
  const n = Number.parseInt(String(x), 10)
  return Number.isFinite(n) ? n : fallback
}

export function clampInt(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

export function sortMealTimes(times) {
  const set = new Set(Array.isArray(times) ? times : [])
  return MEAL_TIME_ORDER.filter((t) => set.has(t))
}

export function windowed(arr, start, size) {
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

export function dedupeMealsById(meals) {
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

export function normalizeMacros(macros) {
  const m = macros || {}
  const toNum = (x) => {
    const n = Number(x)
    return Number.isFinite(n) ? n : 0
  }
  return {
    caloriesKcal: toNum(m.caloriesKcal),
    proteinG: toNum(m.proteinG),
    carbsG: toNum(m.carbsG),
    fatG: toNum(m.fatG),
    fiberG: toNum(m.fiberG)
  }
}

export function sumMacrosFromPlan(plan, mealTimes) {
  const totals = { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 }
  
  // If plan has a meals array (Draft format)
  if (plan?.meals && Array.isArray(plan.meals)) {
    for (const meal of plan.meals) {
        const m = normalizeMacros(meal?.macros)
        totals.caloriesKcal += m.caloriesKcal
        totals.proteinG += m.proteinG
        totals.carbsG += m.carbsG
        totals.fatG += m.fatG
        totals.fiberG += m.fiberG
    }
    return totals
  }

  // Fallback for old dictionary format
  for (const mt of Array.isArray(mealTimes) ? mealTimes : []) {
    const item = plan?.[mt]
    if (!item) continue
    const m = normalizeMacros(item?.macros)
    totals.caloriesKcal += m.caloriesKcal
    totals.proteinG += m.proteinG
    totals.carbsG += m.carbsG
    totals.fatG += m.fatG
    totals.fiberG += m.fiberG
  }
  return totals
}

export function withRecomputedTotals(resultLike) {
  if (!resultLike) return resultLike
  const mealTimes = Array.isArray(resultLike.mealTimes) ? resultLike.mealTimes : []

  if (resultLike.weeks) {
    let totalsAll = { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 }
    // We update the totals directly on each day object inside weeks
    for (const week of resultLike.weeks) {
        for (const day of week.days || []) {
            const t = sumMacrosFromPlan(day, mealTimes)
            day.totals = t // ensure day totals are stored
            totalsAll.caloriesKcal += t.caloriesKcal
            totalsAll.proteinG += t.proteinG
            totalsAll.carbsG += t.carbsG
            totalsAll.fatG += t.fatG
            totalsAll.fiberG += t.fiberG
        }
    }
    return { ...resultLike, totalsAll }
  }

  const days = Number(resultLike.days || 1)

  if (days <= 1) {
    const totals = sumMacrosFromPlan(resultLike.plan || {}, mealTimes)
    return { ...resultLike, totals }
  }

  const plans = Array.isArray(resultLike.days) ? resultLike.days : (Array.isArray(resultLike.plans) ? resultLike.plans : [])
  const totalsByDay = plans.map((p) => sumMacrosFromPlan(p || {}, mealTimes))
  const totalsAll = totalsByDay.reduce(
    (acc, t) => ({
      caloriesKcal: acc.caloriesKcal + t.caloriesKcal,
      proteinG: acc.proteinG + t.proteinG,
      carbsG: acc.carbsG + t.carbsG,
      fatG: acc.fatG + t.fatG,
      fiberG: acc.fiberG + t.fiberG
    }),
    { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 }
  )

  return { ...resultLike, totalsByDay, totalsAll }
}
