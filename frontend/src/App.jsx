import React from 'react'
import { ProfileProvider } from './contexts/ProfileContext.jsx'
import { PlannerProvider } from './contexts/PlannerContext.jsx'
import PlanStudio from './features/planner/PlanStudio.jsx'

export default function App() {
  return (
    <ProfileProvider>
      <PlannerProvider>
        <PlanStudio />
      </PlannerProvider>
    </ProfileProvider>
  )
}
