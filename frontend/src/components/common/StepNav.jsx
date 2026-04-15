/**
 * StepNav — horizontal step indicator using MUI Stepper.
 * Organic Light Mode version.
 */
import React from 'react'
import Stepper from '@mui/material/Stepper'
import Step from '@mui/material/Step'
import StepLabel from '@mui/material/StepLabel'
import StepButton from '@mui/material/StepButton'
import Box from '@mui/material/Box'

const STEPS = [
  { id: 'inputs',         label: 'Profile',         icon: '🧾' },
  { id: 'chooseMeals',   label: 'Meal Options',     icon: '🍽️' },
  { id: 'selectedMeals', label: 'Planner Grid',     icon: '📅' },
  { id: 'plans',         label: 'Final Plan',       icon: '✅' },
]

const VIEW_INDEX = { inputs: 0, chooseMeals: 1, selectedMeals: 2, plans: 3 }

export default function StepNav({ view, onStepClick, result }) {
  const activeStep = VIEW_INDEX[view] ?? 0

  return (
    <Box sx={{ 
      width: '100%', 
      px: { xs: 2, md: 6 }, 
      py: 3, 
      bgcolor: '#FFFFFF', 
      borderBottom: '1px solid', 
      borderColor: 'divider',
      boxShadow: '0 4px 12px rgba(0,0,0,0.02)'
    }}>
      <Stepper activeStep={activeStep} alternativeLabel nonLinear>
        {STEPS.map((step, index) => {
          const isDisabled =
            (index >= 1 && view === 'inputs') ||
            (index === 3 && !result)

          return (
            <Step key={step.id} completed={index < activeStep}>
              <StepButton
                onClick={() => !isDisabled && onStepClick(step.id)}
                disabled={isDisabled}
                sx={{
                  '& .MuiStepLabel-label': {
                    fontSize: { xs: '0.75rem', sm: '0.9rem' },
                    fontWeight: index === activeStep ? 800 : 500,
                    color: index === activeStep ? 'primary.main' : 'text.secondary',
                    mt: 1
                  },
                  '& .MuiStepLabel-iconContainer': {
                    transform: index === activeStep ? 'scale(1.2)' : 'scale(1)',
                    transition: 'transform 0.2s',
                  }
                }}
              >
                <StepLabel icon={<span style={{ fontSize: '1.2rem' }}>{step.icon}</span>}>
                  {step.label}
                </StepLabel>
              </StepButton>
            </Step>
          )
        })}
      </Stepper>
    </Box>
  )
}
