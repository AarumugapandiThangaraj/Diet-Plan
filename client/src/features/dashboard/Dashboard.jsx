import React, { useEffect, useState } from 'react';
import { usePlannerContext } from '../../contexts/PlannerContext.jsx';
import { fetchDashboardSummary, logMealConsumption } from '../../services/dietService.js';
import PlanTabsLayout from '../../components/planner/PlanTabsLayout.jsx';
import './Dashboard.css';
import { MEAL_TIME_LABELS } from '../../config/constants.js';
import SwapModal from '../planner/SwapModal.jsx';
import MealDetailsModal from '../planner/MealDetailsModal.jsx';

export default function Dashboard({ onNavigateToStudio }) {
  const { handleSwapWholeMeal, handleSwapFood, activateAndProceed, generateLoading } = usePlannerContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboardData = () => {
    setLoading(true);
    setError('');
    fetchDashboardSummary()
      .then((res) => {
        setData(res);
      })
      .catch((err) => {
        setError(String(err?.message || err || 'Failed to fetch dashboard data.'));
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const getDisplayMealName = (meal) => {
    if (!meal || !meal.name) return 'Unknown Meal';
    return meal.name;
  };

  if (loading) {
    return (
      <div className="dashboardOuter">
        <div className="dashboardSidebar">
          <div className="sidebarIcon active">📊</div>
        </div>
        <div className="dashboardContent" style={{ flex: 1 }}>
          <div style={{ color: '#fff' }}>Loading plan data...</div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="dashboardOuter">
        <div className="dashboardContent">
          <div style={{ color: '#ff4a4a', padding: '40px' }}>{error || "No data"}</div>
        </div>
      </div>
    );
  }

  if (!data.weeks || data.weeks.length === 0) {
    return (
      <div className="dashboardOuter">
        <div className="dashboardSidebar">
          <div className="sidebarIcon active" title="Dashboard">📊</div>
          <div className="sidebarIcon" onClick={onNavigateToStudio} title="Plan Studio">📅</div>
        </div>
        <div className="dashboardContent">
          <div style={{ color: '#fff' }}>
            <h2>No Diet Plan Found</h2>
            <button className="btnPrimary" onClick={onNavigateToStudio}>Go to Plan Studio</button>
          </div>
        </div>
      </div>
    );
  }

  const isDraft = data.status === 'draft';
  const targetCalories = data.energySummary?.targetCalories || 2000;
  const consumedCalories = data.energySummary?.consumedCalories || 0;
  const progressPercent = targetCalories > 0 ? Math.min(100, Math.round((consumedCalories / targetCalories) * 100)) : 0;
  
  // SVG Circle calculations
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPercent / 100) * circumference;

  const renderDay = (day) => {
    return (
      <div className="mealList">
        {day.meals?.map((meal, idx) => (
          <div className="mealRow" key={idx}>
            {meal.imageUrl ? (
              <img src={`http://localhost:8000/api/food-image/${meal.foods?.[0]?.id || ''}`} alt={meal.name} className="mealImage" onError={(e) => { e.target.style.display = 'none'; }} />
            ) : (
              <div className="mealImage" />
            )}
            
            <div className="mealInfo">
              <span className="mealSession">
                {MEAL_TIME_LABELS[meal.session] || meal.session} {meal.scheduledTime ? `• ${meal.scheduledTime}` : ''}
              </span>
              <h4 className="mealName">{getDisplayMealName(meal)}</h4>
              <div className="mealMacros">
                <span>{Math.round(meal.macros?.caloriesKcal || 0)} kcal</span> | 
                {Math.round(meal.macros?.proteinG || 0)}g Protein | 
                {Math.round(meal.macros?.carbsG || 0)}g Carb | 
                {Math.round(meal.macros?.fatG || 0)}g Fats | 
                {Math.round(meal.macros?.fiberG || 0)}g Fiber
              </div>
            </div>

            {isDraft && (
              <div className="mealActions">
                <button className="btnSmall" onClick={() => handleSwapWholeMeal(day.dayNumber - 1, meal.session)}>
                  Swap meal
                </button>
                {meal.is_food_swappable !== false && (
                  <button className="btnSmall" onClick={() => handleSwapFood(day.dayNumber - 1, meal.session)}>
                    Swap food
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
        {isDraft && (
          <div className="bottomActions">
            <button className="btnOutline" onClick={onNavigateToStudio}>Back</button>
            <button 
              className="btnPrimary" 
              disabled={generateLoading}
              onClick={() => activateAndProceed(() => { loadDashboardData(); }, data.planId, data.version)}
            >
              {generateLoading ? 'Activating...' : 'Activate Plan'}
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="dashboardOuter">
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
      </aside>

      <main className="dashboardContent">
        <div className="dashboardMain">
          <header className="dashboardHeader">
            <div>
              <h1>{isDraft ? 'Customize Meal' : 'Active Diet Plan'}</h1>
              <p>{isDraft ? 'Review and edit your curated plan.' : 'Track your daily progress.'}</p>
            </div>
            {isDraft && (
              <div className="headerActions">
                <button className="btnOutline">View Meal Recipes</button>
                <button className="btnOutline">Download plan</button>
              </div>
            )}
          </header>

          <PlanTabsLayout weeks={data.weeks} renderDay={renderDay} />
        </div>

        {!isDraft && (
          <aside className="dashboardRight">
            <div className="summaryCard">
              <h3>Today's Summary</h3>
              <div className="progressRingContainer">
                <svg width="160" height="160" style={{ transform: 'rotate(-90deg)' }}>
                  <circle cx="80" cy="80" r={radius} stroke="rgba(255,255,255,0.1)" strokeWidth="12" fill="none" />
                  <circle 
                    cx="80" cy="80" r={radius} 
                    stroke="#2196f3" 
                    strokeWidth="12" 
                    fill="none" 
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                  />
                </svg>
                <div className="progressRingText">
                  <div className="value">{consumedCalories}</div>
                  <div className="label">OF {targetCalories} KCAL</div>
                </div>
              </div>
              
              <div className="macroList">
                <div className="macroItem">
                  <div className="macroLabel"><span className="macroDot" style={{backgroundColor: '#FF9800'}}></span> Protein</div>
                  <div className="macroValue">{data.dailyTargets?.proteinG}g</div>
                </div>
                <div className="macroItem">
                  <div className="macroLabel"><span className="macroDot" style={{backgroundColor: '#4CAF50'}}></span> Carbs</div>
                  <div className="macroValue">{data.dailyTargets?.carbsG}g</div>
                </div>
                <div className="macroItem">
                  <div className="macroLabel"><span className="macroDot" style={{backgroundColor: '#F44336'}}></span> Fat</div>
                  <div className="macroValue">{data.dailyTargets?.fatG}g</div>
                </div>
                <div className="macroItem">
                  <div className="macroLabel"><span className="macroDot" style={{backgroundColor: '#9C27B0'}}></span> Fiber</div>
                  <div className="macroValue">{data.dailyTargets?.fiberG}g</div>
                </div>
                <div className="macroItem">
                  <div className="macroLabel"><span className="macroDot" style={{backgroundColor: '#03A9F4'}}></span> Water</div>
                  <div className="macroValue">{data.hydration?.targetWaterL}L</div>
                </div>
              </div>
            </div>

            <div className="insightCard">
              <div className="insightHeader">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
                AI INSIGHT
              </div>
              <p className="insightContent">
                You're on track with your macros today. Try drinking a glass of water before dinner to reach your hydration goal!
              </p>
            </div>
            
            <div className="summaryCard">
              <h3>Meal Balance</h3>
              <p style={{ color: '#a0a0a0', fontSize: '0.9rem', lineHeight: '1.5' }}>
                Your current plan balances nutrient-dense meals with adequate hydration to support your metabolic goals.
              </p>
            </div>
          </aside>
        )}
      </main>
      <SwapModal />
      <MealDetailsModal />
    </div>
  );
}
