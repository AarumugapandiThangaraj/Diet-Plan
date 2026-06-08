import React, { createContext, useContext } from 'react'
import { useProfile } from '../hooks/useProfile.js'

const ProfileContext = createContext(null)

export function ProfileProvider({ children }) {
  const value = useProfile()
  return (
    <ProfileContext.Provider value={value}>
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfileContext() {
  const context = useContext(ProfileContext)
  if (!context) {
    throw new Error('useProfileContext must be used within a ProfileProvider')
  }
  return context
}
