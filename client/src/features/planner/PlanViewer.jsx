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

  // Convert result.plans into weeks format expected by PlanTabsLayout
  const weeks = useMemo(() => {
    if (!result || !result.plans) return [];
    
    const plansList = result.plans;
    const dayIds = result.dayIds || [];
    const weeksData = [];
    
    for (let i = 0; i < plansList.length; i += 7) {
      const weekDays = plansList.slice(i, i + 7);
      const weekNum = Math.floor(i / 7) + 1;
      
      const daysData = weekDays.map((dayPlan, j) => {
        const dayNum = i + j + 1;
        const pDayId = dayIds[i + j];
        
        const dayMeals = [];
        const dayTotals = { caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0, fiberG: 0 };
        
        for (const [session, meal] of Object.entries(dayPlan)) {
          if (!meal || typeof meal !== 'object') continue;
          
          const macros = meal.macros || {};
          dayTotals.caloriesKcal += Number(macros.caloriesKcal || 0);
          dayTotals.proteinG += Number(macros.proteinG || 0);
          dayTotals.carbsG += Number(macros.carbsG || 0);
          dayTotals.fatG += Number(macros.fatG || 0);
          dayTotals.fiberG += Number(macros.fiberG || 0);
          
          let foodsList = [];
          if (Array.isArray(meal.foods_struct)) {
            foodsList = meal.foods_struct.map(f => ({
              id: String(f.id || f.ID || f.food_id || ''),
              name: String(f.name || f.food_name || ''),
              servingSize: String(f.serving_size || ''),
              quantity: Number(f.quantity || 1.0),
              unit: String(f.unit || 'serving')
            }));
          }
          
          let scheduledTime = meal.scheduled_time || meal.time || '';
          if (!scheduledTime) {
            const timeMap = {
              "early_morning": "06:00 AM",
              "breakfast": "08:30 AM",
              "mid_morning": "11:00 AM",
              "lunch": "01:00 PM",
              "evening": "04:30 PM",
              "dinner": "08:00 PM",
              "bedtime": "10:00 PM"
            };
            scheduledTime = timeMap[session] || "12:00 PM";
          }
          
          dayMeals.push({
            mealId: String(meal.Meal_ID || ''),
            name: String(meal.meal_name || ''),
            imageUrl: String(meal.image_ID || ''),
            session: session,
            scheduledTime: scheduledTime,
            macros: {
              caloriesKcal: Number(macros.caloriesKcal || 0),
              proteinG: Number(macros.proteinG || 0),
              carbsG: Number(macros.carbsG || 0),
              fatG: Number(macros.fatG || 0),
              fiberG: Number(macros.fiberG || 0)
            },
            foods: foodsList
          });
        }
        
        return {
          dayNumber: dayNum,
          planDayId: pDayId,
          totals: dayTotals,
          meals: dayMeals
        };
      });
      
      weeksData.push({
        weekNumber: weekNum,
        days: daysData
      });
    }
    
    return weeksData;
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
              <button className="btnSmall" onClick={() => handleSwapFood(day.dayNumber - 1, meal.session)}>
                Swap food
              </button>
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
