import { useCallback } from 'react'
import { generateDietPlanPDF } from '../utils/pdfExporter.js'

export function usePDFGenerator() {
  const generatePDF = useCallback((elementId = 'final-plan-container') => {
    generateDietPlanPDF(elementId)
  }, [])

  return {
    generatePDF
  }
}
