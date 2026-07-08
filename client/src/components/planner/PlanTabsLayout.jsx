import React, { useState } from 'react';
import './PlanTabsLayout.css';

export default function PlanTabsLayout({ weeks = [], renderDay }) {
  const [activeWeekNum, setActiveWeekNum] = useState(weeks.length > 0 ? weeks[0].weekNumber : 1);
  const activeWeek = weeks.find(w => w.weekNumber === activeWeekNum) || weeks[0];
  
  const [activeDayNum, setActiveDayNum] = useState(
    activeWeek?.days?.length > 0 ? activeWeek.days[0].dayNumber : 1
  );

  const activeDay = activeWeek?.days?.find(d => d.dayNumber === activeDayNum) || activeWeek?.days?.[0];

  if (!weeks || weeks.length === 0) {
    return <div className="tabsLayoutEmpty">No plan data available.</div>;
  }

  const handleWeekChange = (weekNum) => {
    setActiveWeekNum(weekNum);
    const newActiveWeek = weeks.find(w => w.weekNumber === weekNum);
    if (newActiveWeek?.days?.length > 0) {
      setActiveDayNum(newActiveWeek.days[0].dayNumber);
    }
  };

  return (
    <div className="planTabsLayout">
      <div className="weekTabs">
        {weeks.map(week => (
          <button
            key={week.weekNumber}
            className={`weekTab ${activeWeekNum === week.weekNumber ? 'active' : ''}`}
            onClick={() => handleWeekChange(week.weekNumber)}
          >
            Week {week.weekNumber}
          </button>
        ))}
      </div>

      <div className="dayTabs">
        {activeWeek?.days?.map(day => (
          <button
            key={day.dayNumber}
            className={`dayTab ${activeDayNum === day.dayNumber ? 'active' : ''}`}
            onClick={() => setActiveDayNum(day.dayNumber)}
          >
            Day {day.dayNumber}
          </button>
        ))}
      </div>

      <div className="dayContent">
        {activeDay && renderDay(activeDay)}
      </div>
    </div>
  );
}
