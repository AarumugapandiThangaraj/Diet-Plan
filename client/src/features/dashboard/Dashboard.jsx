import React, { useEffect, useState } from 'react'
import { useProfileContext } from '../../contexts/ProfileContext.jsx'
import { fetchDashboardSummary, logMealConsumption, logHydration } from '../../services/dietService.js'
import './Dashboard.css'

export default function Dashboard({ onNavigateToStudio }) {
  const { profile } = useProfileContext()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Interactive local states for a premium, alive feel
  const [glassesDrunk, setGlassesDrunk] = useState(0)
  const [consumedMeals, setConsumedMeals] = useState({})
  const mealsScrollRef = React.useRef(null)
  const [scrollProgress, setScrollProgress] = useState(0)

  const userIdentifier = profile.user_identifier || '00000000-0000-0000-0000-000000000000'

  const loadDashboardData = () => {
    setLoading(true)
    setError('')
    fetchDashboardSummary(userIdentifier)
      .then((res) => {
        setData(res)
        // Convert milliliters to glasses for display (1 glass = 250 ml)
        const consumedMl = res?.hydration?.consumedWaterMl || 0
        setGlassesDrunk(Math.round(consumedMl / 250))
        
        // Initialize consumedMeals state from todayMeals consumed properties
        const consumedMap = {}
        if (res?.todayMeals) {
          res.todayMeals.forEach(meal => {
            consumedMap[meal.mealId] = !!meal.consumed
          })
        }
        setConsumedMeals(consumedMap)
      })
      .catch((err) => {
        setError(String(err?.message || err || 'Failed to fetch dashboard data.'))
      })
      .finally(() => {
        setLoading(false)
      })
  }

  const handleWaterGlassClick = (glassesCount) => {
    const prevGlasses = glassesDrunk
    const nextMl = glassesCount * 250

    // 1. Optimistic Update
    setGlassesDrunk(glassesCount)

    // Format today's date as YYYY-MM-DD local time
    const todayStr = new Date().toLocaleDateString('en-CA')

    // 2. Call API to persist absolute value
    logHydration(userIdentifier, todayStr, nextMl)
      .catch((err) => {
        console.error('Failed to log water consumption:', err)
        // Rollback optimistic state on error
        setGlassesDrunk(prevGlasses)
      })
  }


  useEffect(() => {
    loadDashboardData()
  }, [userIdentifier])

  const toggleMealConsumed = (mealId) => {
    const nextConsumed = !consumedMeals[mealId]

    // 1. Optimistic Update
    setConsumedMeals(prev => ({
      ...prev,
      [mealId]: nextConsumed
    }))

    // Format today's date as YYYY-MM-DD local time
    const todayStr = new Date().toLocaleDateString('en-CA') // outputs YYYY-MM-DD

    // 2. Call API to persist
    logMealConsumption(userIdentifier, mealId, todayStr, nextConsumed)
      .catch((err) => {
        console.error('Failed to log meal consumption:', err)
        // Rollback optimistic state on error
        setConsumedMeals(prev => ({
          ...prev,
          [mealId]: !nextConsumed
        }))
      })
  }


  // Helper mapping for goal text
  const cleanGoalName = (g) => {
    if (!g) return 'Weight Management'
    return g.replace(/_/g, ' ')
  }

  if (loading) {
    return (
      <div className="dashboardOuter">
        <div className="dashboardSidebar">
          <div className="sidebarIcon active">📊</div>
          <div className="sidebarIcon">📅</div>
          <div className="sidebarIcon">🔄</div>
          <div className="sidebarIcon">⚖️</div>
          <div className="sidebarIcon">👤</div>
        </div>
        <div className="dashboardContent" style={{ padding: '24px', flex: 1 }}>
          <div className="skeletonCard" style={{ height: '80px', marginBottom: '20px' }} />
          <div className="dashboardGrid">
            <div className="skeletonCard" style={{ height: '300px' }} />
            <div className="skeletonCard" style={{ height: '300px' }} />
            <div className="skeletonCard" style={{ height: '300px' }} />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboardOuter">
        <div className="dashboardContent">
          <div className="inlineError" style={{ padding: '40px' }}>{error}</div>
        </div>
      </div>
    )
  }

  // Handle empty state gracefully
  if (data?.activePlan === false) {
    return (
      <div className="dashboardOuter">
        <div className="dashboardSidebar">
          <div className="sidebarIcon active" title="Dashboard">📊</div>
          <div className="sidebarIcon" onClick={onNavigateToStudio} title="Plan Studio">📅</div>
          <div className="sidebarIcon" onClick={onNavigateToStudio} title="Swaps">🔄</div>
          <div className="sidebarIcon" title="Health">⚖️</div>
          <div className="sidebarIcon" title="Profile">👤</div>
        </div>
        <div className="dashboardContent" style={{ flex: 1, padding: '24px' }}>
          <div className="emptyStateWrapper">
            <div className="emptyStateIcon">📅</div>
            <h2>No Active Diet Plan Found</h2>
            <p>Generate a customized diet plan in Plan Studio to view your daily dashboard summary.</p>
            <button type="button" className="primaryBtn" style={{ maxWidth: '240px' }} onClick={onNavigateToStudio}>
              Go to Plan Studio
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Compute calculated items
  const dailyTargets = data.dailyTargets || {}
  const healthMetrics = data.healthMetrics || {}
  const hydration = data.hydration || {}
  const energySummary = data.energySummary || { targetCalories: dailyTargets.caloriesKcal || 2000, consumedCalories: 0, remainingCalories: dailyTargets.caloriesKcal || 2000 }

  // Calculate local consumed calories from the checked checkboxes
  const localConsumedCalories = data?.todayMeals
    ? data.todayMeals.reduce((acc, meal) => {
        const isConsumed = !!consumedMeals[meal.mealId]
        return acc + (isConsumed ? Math.round(meal.macros?.caloriesKcal || 0) : 0)
      }, 0)
    : 0

  const targetCalories = Math.round(dailyTargets.caloriesKcal || 2000)
  const remainingCalories = Math.max(0, targetCalories - localConsumedCalories)
  const reachedPercent = targetCalories > 0 ? Math.round((localConsumedCalories / targetCalories) * 100) : 0


  // Weight dial calculations
  const currentWeight = Number(healthMetrics.weightKg || profile.weightKg || 70.0)
  const targetWeight = Number(healthMetrics.targetWeightKg || 65.0)
  const weightDelta = Number(healthMetrics.weightDeltaKg || (targetWeight - currentWeight))
  const startWeight = currentWeight - weightDelta

  // Percentage dial angle (mock or map between start and target)
  const dialPercent = 0.68 // sweet spot gauge filling

  const scrollMeals = (direction) => {
    if (mealsScrollRef.current) {
      const scrollAmount = 260 // card width + gap
      mealsScrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      })
    }
  }

  const handleMealsScroll = (e) => {
    const target = e.target
    const maxScroll = target.scrollWidth - target.clientWidth
    const progress = maxScroll > 0 ? (target.scrollLeft / maxScroll) * 100 : 0
    setScrollProgress(progress)
  }

  return (
    <div className="dashboardOuter">
      {/* Mock Navigation Sidebar */}
      <aside className="dashboardSidebar">
        <div className="sidebarIcon active" title="Dashboard">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1.5" />
            <rect x="14" y="3" width="7" height="7" rx="1.5" />
            <rect x="14" y="14" width="7" height="7" rx="1.5" />
            <rect x="3" y="14" width="7" height="7" rx="1.5" />
          </svg>
        </div>
        <div className="sidebarIcon" onClick={onNavigateToStudio} title="Plan Studio">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </div>
        <div className="sidebarIcon" onClick={onNavigateToStudio} title="Swaps & Alternatives">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 1l4 4-4 4" />
            <path d="M3 11V9a4 4 0 0 1 4-4h14" />
            <path d="M7 23l-4-4 4-4" />
            <path d="M21 13v2a4 4 0 0 1-4 4H3" />
          </svg>
        </div>
        <div className="sidebarIcon" title="Health Metrics">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
          </svg>
        </div>
        <div className="sidebarIcon" title="Settings / Profile">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      </aside>

      {/* Main Multi-Column Content Area */}
      <main className="dashboardContent">
        {/* 4-column Grid */}
        <div className="dashboardGrid4Col">
          
          {/* ================= COLUMN 1 ================= */}
          <div className="gridCol col1">
            <div className="dashboardTitleBlock">
              <p className="eyebrow">Your</p>
              <h1>Dashboard</h1>
            </div>

            {/* Genomic Teaser Card */}
            <div className="dbCard genomicCard">
              <span className="tagPill">Gene markers</span>
              <h3>Genomic nutrition</h3>
              <p>
                Your DNA determines which nutrients your body processes most efficiently — and which supplements you actually need.
              </p>
              <span className="comingSoonBtn">Coming soon</span>
            </div>

            {/* Hydration Card */}
            <div className="dbCard hydrationCard">
              <div className="cardHeader">
                <div>
                  <h3>Hydration Status 💧</h3>
                  <p className="cardSubtitle">Drinking enough water daily boosts energy and gut absorption.</p>
                </div>
                <button type="button" className="cardEditBtn">Edit</button>
              </div>
              
              <div className="hydrationTarget">
                {hydration.targetWaterL?.toFixed(2) || '—'} <span>Liters / Day</span>
              </div>

              {/* Tap glasses to log/increment water intake */}
              <div className="hydrationGlassesGrid">
                {[...Array(10)].map((_, i) => (
                  <div 
                    key={i} 
                    className={`glassIcon ${i < glassesDrunk ? 'filled' : 'empty'}`}
                    onClick={() => handleWaterGlassClick(i + 1)}
                    title={`Log ${((i + 1) * 0.25).toFixed(2)} Liters`}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18.8 3H5.2c-.4 0-.8.3-.8.8l1.8 16.5c.1.7.7 1.2 1.4 1.2h8.8c.7 0 1.3-.5 1.4-1.2L19.6 3.8c0-.5-.4-.8-.8-.8z" />
                      <line x1="4.6" y1="8" x2="19.4" y2="8" />
                    </svg>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ================= COLUMN 2 ================= */}
          <div className="gridCol col2">
            {/* Calories Main Card */}
            <div className="dbCard caloriesCard">
              <div className="cardHeader">
                <div>
                  <h3>Calories 🎯</h3>
                  <p className="cardSubtitle">Daily target calculated for your profile goal.</p>
                </div>
                <div className="bmiBadge" title={`BMI: ${healthMetrics.bmi?.toFixed(1) || '—'}`}>
                  ❤️ <small>BMI</small> <strong>{Math.round(healthMetrics.bmi || 22)}</strong>
                </div>
              </div>

              <div className="caloriesGrid">
                <div className="calorieAmount">
                  <strong>{targetCalories}</strong>
                  <span>Kcal Target</span>
                </div>
                <div className="calorieAmount" style={{ textAlign: 'right' }}>
                  <strong>{localConsumedCalories}</strong>
                  <span>Kcal Consumed</span>
                </div>
              </div>

              {/* CSS-based Bar Chart Representation */}
              <div className="caloriesBarChart" title="Daily meal calorie distribution estimation">
                <div className="calorieChartBar" style={{ height: '35%' }} />
                <div className="calorieChartBar" style={{ height: '55%' }} />
                <div className="calorieChartBar" style={{ height: '78%' }} />
                <div className="calorieChartBar" style={{ height: '42%' }} />
                <div className="calorieChartBar" style={{ height: '90%' }} />
                <div className="calorieChartBar" style={{ height: '62%' }} />
                <div className="calorieChartBar" style={{ height: '30%' }} />
                <div className="calorieChartBar" style={{ height: '48%' }} />
                <div className="calorieChartBar" style={{ height: '80%' }} />
                <div className="calorieChartBar" style={{ height: '95%' }} />
                <div className="calorieChartBar" style={{ height: '50%' }} />
                <div className="calorieChartBar" style={{ height: '25%' }} />
              </div>

              {/* Target Macros Breakdown */}
              <div className="macrosRowGrid">
                <div className="macroPillBox" title="Carbohydrates Target">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#D4A574" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  <strong>{Math.round(dailyTargets.carbsG || 0)}g</strong>
                  <span>Carbs</span>
                </div>
                <div className="macroPillBox" title="Protein Target">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#3F665C" strokeWidth="2">
                    <path d="M12 14c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5z" />
                    <path d="M18 21a6 6 0 0 0-12 0" />
                  </svg>
                  <strong>{Math.round(dailyTargets.proteinG || 0)}g</strong>
                  <span>Protein</span>
                </div>
                <div className="macroPillBox" title="Fiber Target">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#1B4332" strokeWidth="2">
                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                  <strong>{Math.round(dailyTargets.fiberG || 0)}g</strong>
                  <span>Fiber</span>
                </div>
                <div className="macroPillBox" title="Fat Target">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#D4A574" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                  <strong>{Math.round(dailyTargets.fatG || 0)}g</strong>
                  <span>Fat</span>
                </div>
              </div>
            </div>
          </div>

          {/* ================= COLUMN 3 ================= */}
          <div className="gridCol col3">
            <div className="col3Header">
              <div className="headerActionIcons">
                <button type="button" className="actionIconBtn" title="Hydration">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
                  </svg>
                </button>
                <button type="button" className="actionIconBtn" title="Diet Planner">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M9 12l2 2 4-4" />
                  </svg>
                </button>
                <button type="button" className="actionIconBtn" onClick={onNavigateToStudio} title="Profile / Settings">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Today's Meals Section */}
            <section className="dbCard mealsSectionPanel">
              <div className="mealsHeader">
                <h3>Today's Meals 🍽️</h3>
                <button type="button" className="cardEditBtn" onClick={onNavigateToStudio}>Edit</button>
              </div>
              
              {data.todayMeals?.length === 0 ? (
                <p className="heroText" style={{ padding: '20px 0' }}>No meals scheduled for today.</p>
              ) : (
                <>
                  <div className="mealsHorizontalScroll" ref={mealsScrollRef} onScroll={handleMealsScroll}>
                    {data.todayMeals.map((meal) => {
                      const isConsumed = !!consumedMeals[meal.mealId]
                      const fallbackChar = meal.name ? meal.name.charAt(0) : 'M'
                      const firstFoodId = meal.imageUrl || meal.mealId || ''
                      const imgUrl = firstFoodId ? `http://localhost:8000/api/food-image/${firstFoodId}` : null

                      return (
                        <div key={meal.mealId} className="mealScrollCard">
                          {/* Consumed checkbox */}
                          <div 
                            className="mealCheckedBox" 
                            onClick={() => toggleMealConsumed(meal.mealId)}
                            title={isConsumed ? "Mark as unconsumed" : "Mark as consumed"}
                          >
                            {isConsumed ? (
                              <svg viewBox="0 0 24 24" fill="var(--primaryContainer)" stroke="var(--primaryContainer)" strokeWidth="2">
                                <rect x="2" y="2" width="20" height="20" rx="4" />
                                <path d="M9 11l3 3 6-6" stroke="#fff" strokeWidth="3" fill="none" />
                              </svg>
                            ) : (
                              <svg viewBox="0 0 24 24" fill="none" stroke="var(--outline)" strokeWidth="2">
                                <rect x="2" y="2" width="20" height="20" rx="4" />
                              </svg>
                            )}
                          </div>

                          <div className="mealCardTop">
                            <div className="mealRoundImage">
                              {imgUrl ? (
                                <img src={imgUrl} alt={meal.name} onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
                              ) : null}
                              <div className="mealRoundFallback" style={{ display: imgUrl ? 'none' : 'flex' }}>
                                {fallbackChar}
                              </div>
                            </div>
                            <div className="mealTopMeta">
                              <span>{meal.session?.replace(/_/g, ' ')}</span>
                              <small>{meal.scheduledTime}</small>
                            </div>
                          </div>

                          <h4>{meal.name}</h4>

                          {/* Meal Card Macro Details */}
                          <div className="mealCardMacros">
                            <span title="Protein">P: <strong>{Math.round(meal.macros?.proteinG || 0)}g</strong></span>
                            <span title="Carbs">C: <strong>{Math.round(meal.macros?.carbsG || 0)}g</strong></span>
                            <span title="Fat">F: <strong>{Math.round(meal.macros?.fatG || 0)}g</strong></span>
                          </div>

                          <div className="mealCardBottom">
                            <span className="mealCardCal">{Math.round(meal.macros?.caloriesKcal || 0)} kcal</span>
                            {isConsumed && <span className="mealPillBadge">Consumed</span>}
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {/* Horizontal Scroll Controls */}
                  <div className="mealsScrollControls">
                    <button type="button" className="scrollArrowBtn" onClick={() => scrollMeals('left')} title="Scroll Left">‹</button>
                    <div className="scrollProgressTrack">
                      <div className="scrollProgressFill" style={{ width: `${scrollProgress}%` }} />
                    </div>
                    <button type="button" className="scrollArrowBtn" onClick={() => scrollMeals('right')} title="Scroll Right">›</button>
                  </div>
                </>
              )}
            </section>
          </div>

          {/* ================= COLUMN 4 ================= */}
          <div className="gridCol col4">
            {/* Energy Bank Card */}
            <div className="dbCard energyBankCard">
              <h3>Energy Bank ⚡</h3>
              <div className="bankValue">
                {remainingCalories} kcal
              </div>
              <p className="bankDesc">remaining calories to consume today</p>

              <div className="progressContainer">
                <div className="progressHeader">
                  <span>{reachedPercent}% REACHED</span>
                  <span>{remainingCalories} kcal LEFT</span>
                </div>
                <div className="progressBarTrack">
                  <div 
                    className="progressBarFill" 
                    style={{ width: `${Math.min(100, reachedPercent)}%` }} 
                  />
                </div>
              </div>
            </div>

            {/* Weight Progress Card */}
            <div className="dbCard weightCard">
              <h3>Weight Progress ⚖️</h3>
              <div className="weightGaugeContainer">
                <svg viewBox="0 0 100 55" className="weightGaugeSvg">
                  {/* Background arc */}
                  <path
                    d="M 10 50 A 40 40 0 0 1 90 50"
                    fill="none"
                    stroke="#e2e8f0"
                    strokeWidth="8"
                    strokeLinecap="round"
                  />
                  {/* Foreground filled arc */}
                  <path
                    d="M 10 50 A 40 40 0 0 1 90 50"
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray="125"
                    strokeDashoffset={125 * (1 - dialPercent)}
                  />
                </svg>
                <div className="weightGaugeValue">
                  <strong>{currentWeight.toFixed(1)} kg</strong>
                  <span>current weight</span>
                </div>
              </div>
              <div className="weightGaugeLabels">
                <span>Start: {startWeight.toFixed(1)} kg</span>
                <span>Target: {targetWeight.toFixed(1)} kg</span>
              </div>
            </div>

            {/* Plan Info Metadata Card */}
            <div className="dbCard planInfoCard">
              <div className="cardHeader">
                <div>
                  <h3>Plan Timeline 📋</h3>
                  <p className="cardSubtitle">Day {data.currentDay || 1} of {data.totalDays || 1}</p>
                </div>
                <button type="button" className="cardEditBtn" onClick={onNavigateToStudio}>Plan Studio</button>
              </div>
              <div className="infoCardGrid">
                <div className="infoItemBox">
                  <span>Goal</span>
                  <strong>{cleanGoalName(data.goal)}</strong>
                </div>
                <div className="infoItemBox">
                  <span>Activity</span>
                  <strong>{data.activityLevel?.replace(/_/g, ' ') || 'Moderate'}</strong>
                </div>
                <div className="infoItemBox">
                  <span>Cuisine</span>
                  <strong>{data.cuisineType?.replace(/_/g, ' ') || 'North Indian'}</strong>
                </div>
                <div className="infoItemBox">
                  <span>Duration</span>
                  <strong>{data.totalDays || 1} Days</strong>
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  )
}

