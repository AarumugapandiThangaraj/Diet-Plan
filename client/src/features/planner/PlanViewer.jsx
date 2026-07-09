import React, { useMemo } from 'react';
import { usePlannerContext } from '../../contexts/PlannerContext.jsx';
import { usePDFGenerator } from '../../hooks/usePDFGenerator.js';
import PlanTabsLayout from '../../components/planner/PlanTabsLayout.jsx';
import { MEAL_TIME_LABELS } from '../../config/constants.js';
import '../dashboard/Dashboard.css';

export default function PlanViewer({ onNavigateToDashboard }) {
  const {
    result,
    handleSwapWholeMeal,
    handleSwapFood,
    activateAndProceed,
    setView,
    generateLoading
  } = usePlannerContext();

  const { generatePDF } = usePDFGenerator();

  const weeks = useMemo(() => {
    if (!result || !result.weeks) return [];
    return result.weeks;
  }, [result]);

  const renderDay = (day) => {
    return (
      <div className="mealList" id="final-plan-container">
        {day.meals?.map((meal, idx) => (
          <div className="mealRow" key={idx}>
            {meal.imageUrl ? (
              <img 
                src={`http://localhost:8000/api/food-image/${meal.foods?.[0]?.id || ''}`} 
                alt={meal.name} 
                className="mealImage" 
                onError={(e) => { e.target.style.display = 'none'; }} 
              />
            ) : (
              <div className="mealImage" />
            )}
            
            <div className="mealInfo">
              <span className="mealSession">
                {MEAL_TIME_LABELS[meal.session] || meal.session} {meal.scheduledTime ? `• ${meal.scheduledTime}` : ''}
              </span>
              <h4 className="mealName">{meal.name}</h4>
              <div className="mealMacros">
                <span>{Math.round(meal.macros?.caloriesKcal || 0)} kcal</span> | 
                {Math.round(meal.macros?.proteinG || 0)}g Protein | 
                {Math.round(meal.macros?.carbsG || 0)}g Carb | 
                {Math.round(meal.macros?.fatG || 0)}g Fats | 
                {Math.round(meal.macros?.fiberG || 0)}g Fiber
              </div>
            </div>

            <div className="mealActions html2pdf__ignore">
              <button className="btnSmall" onClick={() => handleSwapWholeMeal(day.dayNumber - 1, meal.session)}>
                Swap meal
              </button>
              {meal.is_food_swappable !== false && (
                <button className="btnSmall" onClick={() => handleSwapFood(day.dayNumber - 1, meal.session)}>
                  Swap food
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <main className="dashboardOuter" style={{ minHeight: 'auto', background: 'transparent' }}>
      <div className="dashboardMain" style={{ width: '100%' }}>
        <header className="dashboardHeader">
          <div>
            <h1>Customize Meal</h1>
            <p>Review and edit your curated plan.</p>
          </div>
          <div className="headerActions">
            <button className="btnOutline" onClick={() => setView('selectedMeals')}>Back</button>
            <button className="btnOutline" onClick={() => generatePDF('final-plan-container')}>Download plan</button>
            <button 
              className="btnPrimary" 
              disabled={generateLoading}
              onClick={() => activateAndProceed(onNavigateToDashboard)}
            >
              {generateLoading ? 'Activating...' : 'Activate Plan'}
            </button>
          </div>
        </header>

        <PlanTabsLayout weeks={weeks} renderDay={renderDay} />
      </div>
    </main>
  );
}
