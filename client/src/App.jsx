import React, { useState } from 'react'
import { ProfileProvider } from './contexts/ProfileContext.jsx'
import { PlannerProvider } from './contexts/PlannerContext.jsx'
import PlanStudio from './features/planner/PlanStudio.jsx'
import Dashboard from './features/dashboard/Dashboard.jsx'

export default function App() {
  const [currentView, setCurrentView] = useState('studio')

  return (
    <ProfileProvider>
      <PlannerProvider>
        {currentView === 'dashboard' ? (
          <Dashboard onNavigateToStudio={() => setCurrentView('studio')} />
        ) : (
          <PlanStudio onNavigateToDashboard={() => setCurrentView('dashboard')} />
        )}
      </PlannerProvider>
    </ProfileProvider>
  )
}
