import React, { useMemo, useEffect } from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'
import { usePlannerContext } from '../../contexts/PlannerContext.jsx'
import ProfileForm from '../profile/ProfileForm.jsx'
import MetricHub from '../profile/MetricHub.jsx'
import MealPoolSelector from './MealPoolSelector.jsx'
import DayArranger from './DayArranger.jsx'
import PlanViewer from './PlanViewer.jsx'
import SwapModal from './SwapModal.jsx'
import MealDetailsModal from './MealDetailsModal.jsx'
import ChatWidget from '../../components/ChatWidget.jsx'
import cornerSticker from '../../assets/whatsapp-sticker.webp'
import { applyMealSwap } from '../../services/swapService.js'
import { fetchMealSwapOptions } from '../../services/swapService.js'
import { sortMealTimes } from '../../utils/helpers.js'

export default function PlanStudio({ onNavigateToDashboard }) {
  const {
    profile,
    setProfile,
    studioMeta,
    targets,
    setTargets,
    updateProfile
  } = useProfileContext()

  const {
    view,
    setView,
    result,
    setResult,
    planDays,
    planSummary,
    selectedPoolIds,
    selectedPoolsByTime,
    updateResultMeal,
    handleSwapWholeMeal,
    handleSwapIngredient,
    closeSwapModal,
    justGenerated,
    setJustGenerated,
    isSelectionComplete
  } = usePlannerContext()

  // Scroll to top instantly when switching step views
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [view])



  const activeMealTimes = useMemo(() => {
    return result?.mealTimes || sortMealTimes(profile.mealTimes)
  }, [result, profile.mealTimes])

  const appContext = useMemo(() => ({
    view,
    profile,
    planDays,
    isPlanGenerated: !!result,
    planSummary,
    targets: targets ? {
      dailyCalories: targets.dailyCalories,
      proteinG: targets.proteinG,
      carbsG: targets.carbsG,
      fatG: targets.fatG,
    } : null,
    selectedPoolIds,
    activeMealTimes
  }), [view, profile, planDays, result, planSummary, targets, selectedPoolIds, activeMealTimes])

  const handleAgentCommand = (action) => {
    console.log("Agent command received:", action)
    if (!action || !action.type) return

    switch (action.type) {
      case 'SET_VIEW': {
        const validViews = ['inputs', 'chooseMeals', 'selectedMeals', 'plans']
        if (validViews.includes(action.view)) {
          setView(action.view)
        }
        break
      }
      case 'UPDATE_PROFILE':
        if (action.updates) {
          updateProfile(action.updates)
        }
        break
      case 'OPEN_SWAP':
        if (action.mealTime && result) {
          handleSwapWholeMeal(action.dayIndex || 0, action.mealTime)
        }
        break
      case 'OPEN_SWAP_FOOD':
        if (action.mealTime && result) {
          handleSwapFood(action.dayIndex || 0, action.mealTime)
        }
        break
      case 'OPEN_SWAP_INGREDIENT':
        if (action.mealTime && result) {
          handleSwapIngredient(action.dayIndex || 0, action.mealTime)
        }
        break
      case 'REMOVE_ALLERGEN': {
        const allergen = String(action.allergen || '').toLowerCase().trim()
        if (!allergen) break
        setProfile(p => {
          const existing = String(p.allergies || '').trim()
          const allergyList = existing ? existing.split(',').map(a => a.trim().toLowerCase()) : []
          if (!allergyList.includes(allergen)) {
            allergyList.push(allergen)
          }
          return { ...p, allergies: allergyList.join(', ') }
        })
        if (result) {
          setResult(prev => {
            if (!prev) return prev
            const containsAllergen = (item) => {
              if (!item) return false
              const ingredients = String(item.ingredients || '').toLowerCase()
              const ingStruct = Array.isArray(item.ingredients_struct)
                ? item.ingredients_struct.map(i => String(i?.name || '').toLowerCase()).join(' ')
                : ''
              const mealName = String(item.meal_name || '').toLowerCase()
              const caution = String(item.caution || '').toLowerCase()
              const fullText = `${ingredients} ${ingStruct} ${mealName} ${caution}`
              return fullText.includes(allergen)
            }
            if (prev.days <= 1 && prev.plan) {
              const plan = { ...prev.plan }
              for (const mt of Object.keys(plan)) {
                if (containsAllergen(plan[mt])) {
                  plan[mt] = { ...plan[mt], meal_name: `[Removed: contains ${allergen}]`, _removed: true }
                }
              }
              const totals = { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 }
              for (const mt of (result?.mealTimes || [])) {
                const item = plan?.[mt]
                if (!item) continue
                const m = item.macros || {}
                totals.caloriesKcal += Number(m.caloriesKcal || 0)
                totals.proteinG += Number(m.proteinG || 0)
                totals.carbsG += Number(m.carbsG || 0)
                totals.fatG += Number(m.fatG || 0)
                totals.fiberG += Number(m.fiberG || 0)
              }
              return { ...prev, plan, totals }
            }
            if (Array.isArray(prev.plans)) {
              const plans = prev.plans.map(p => {
                if (!p) return p
                const plan = { ...p }
                for (const mt of Object.keys(plan)) {
                  if (containsAllergen(plan[mt])) {
                    plan[mt] = { ...plan[mt], meal_name: `[Removed: contains ${allergen}]`, _removed: true }
                  }
                }
                return plan
              })
              const totalsByDay = plans.map(p => {
                const totals = { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 }
                for (const mt of (result?.mealTimes || [])) {
                  const item = p?.[mt]
                  if (!item) continue
                  const m = item.macros || {}
                  totals.caloriesKcal += Number(m.caloriesKcal || 0)
                  totals.proteinG += Number(m.proteinG || 0)
                  totals.carbsG += Number(m.carbsG || 0)
                  totals.fatG += Number(m.fatG || 0)
                  totals.fiberG += Number(m.fiberG || 0)
                }
                return totals
              })
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
              return { ...prev, plans, totalsByDay, totalsAll }
            }
            return prev
          })
        }
        break
      }
      case 'APPLY_SWAP': {
        const { dayIndex = 0, mealTime, mealId } = action
        if (!mealTime || !mealId || !result) {
          console.log("APPLY_SWAP: missing data or no plan", action)
          break
        }
        ; (async () => {
          try {
            const currentMeal = result.days <= 1 ? result?.plan?.[mealTime] : result?.plans?.[dayIndex]?.[mealTime]
            const currentId = currentMeal?.Meal_ID || ''

            const allowedMealIds = Array.isArray(selectedPoolsByTime?.[mealTime])
              ? selectedPoolsByTime[mealTime].map((m) => m?.Meal_ID).filter(Boolean)
              : []

            const targetMacros = (() => {
              const dist = { early_morning: 0.05, breakfast: 0.3, mid_morning: 0.1, lunch: 0.25, evening: 0.1, dinner: 0.15, bedtime: 0.05 }
              const activeMealTimes = Array.isArray(result?.mealTimes) && result.mealTimes.length ? result.mealTimes : sortMealTimes(profile.mealTimes)
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
            })()

            const res = await fetchMealSwapOptions(profile, mealTime, currentId, { targetMacros, allowedMealIds, topN: 20 })
            console.log('Swap options:', res)
            const options = Array.isArray(res?.options) ? res.options : []
            const match = options.find(o => String(o.mealId) === String(mealId))
            if (match) {
              const applied = await applyMealSwap(match.meal || match)
              const nextMeal = applied?.meal || match.meal || match
              updateResultMeal(dayIndex, mealTime, nextMeal)
            } else {
              console.log("APPLY_SWAP: meal not found in options", mealId, options)
            }
          } catch (e) {
            console.error("APPLY_SWAP error:", e)
          }
        })()
        break
      }
      default:
        console.log("Unknown action type:", action.type)
    }
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
        <div className="actions">
          <button type="button" className="secondaryBtn" onClick={onNavigateToDashboard}>
            Go to Dashboard 📊
          </button>
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
          onClick={() => view !== 'inputs' && isSelectionComplete && setView('selectedMeals')}
          disabled={view === 'inputs' || !isSelectionComplete}
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
          <ProfileForm />
          <MetricHub />
        </main>
      ) : view === 'chooseMeals' ? (
        <MealPoolSelector />
      ) : view === 'selectedMeals' ? (
        <DayArranger />
      ) : (
        <PlanViewer onNavigateToDashboard={onNavigateToDashboard} />
      )}

      <SwapModal />
      <MealDetailsModal />

      <footer className="footerText">
        Data source: <span className="mono">{studioMeta?.dataSource || 'Loading source...'}</span>
      </footer>

      <ChatWidget appContext={appContext} onCommand={handleAgentCommand} />
    </div>
  )
}
