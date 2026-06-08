import React, { createContext, useContext } from 'react'
import { usePlanner } from '../hooks/usePlanner.js'
import { useProfileContext } from './ProfileContext.jsx'

const PlannerContext = createContext(null)

export function PlannerProvider({ children }) {
  const { profile, targets, setTargets } = useProfileContext()
  const value = usePlanner(profile, targets, setTargets)
  return (
    <PlannerContext.Provider value={value}>
      {children}
    </PlannerContext.Provider>
  )
}

export function usePlannerContext() {
  const context = useContext(PlannerContext)
  if (!context) {
    throw new Error('usePlannerContext must be used within a PlannerProvider')
  }
  return context
}
