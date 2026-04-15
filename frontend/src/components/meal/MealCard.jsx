/**
 * MealCard — reusable meal presentation card.
 * Organic Light Mode version.
 */
import React from 'react'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardActions from '@mui/material/CardActions'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import { CheckCircle, AddCircleOutlined, RemoveCircleOutlined } from '@mui/icons-material'

function MacroBadge({ label, value, color }) {
  return (
    <Box sx={{ textAlign: 'center', minWidth: 44 }}>
      <Typography variant="h4" sx={{ color, lineHeight: 1, fontWeight: 800 }}>
        {value != null ? Math.round(value) : '—'}
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase' }}>
        {label}
      </Typography>
    </Box>
  )
}

export default function MealCard({ meal, isSelected, onToggle }) {
  const macros = meal?._macros || meal?.macros

  return (
    <Card sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      border: '2px solid',
      borderColor: isSelected ? 'primary.main' : 'rgba(0,0,0,0.06)',
      boxShadow: isSelected ? '0 8px 24px rgba(46, 125, 50, 0.12)' : '0 2px 8px rgba(0,0,0,0.02)',
      bgcolor: isSelected ? '#F1F8E9' : 'background.paper',
      transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
      position: 'relative',
      '&:hover': {
        borderColor: isSelected ? 'primary.main' : 'primary.light',
        transform: 'translateY(-4px)',
        boxShadow: '0 12px 32px rgba(46, 125, 50, 0.15)',
      },
    }}>
      {isSelected && (
        <Box sx={{ position: 'absolute', top: 12, right: 12, zIndex: 1 }}>
          <CheckCircle sx={{ color: 'primary.main', fontSize: 24 }} />
        </Box>
      )}

      <CardContent sx={{ flex: 1, p: 2.5 }}>
        <Chip 
          label={isSelected ? 'Selected' : 'Option'} 
          size="small"
          color={isSelected ? 'primary' : 'default'} 
          variant={isSelected ? 'filled' : 'outlined'}
          sx={{ mb: 1.5, fontSize: '0.65rem', height: 20, fontWeight: 700 }} 
        />

        <Typography variant="h3" sx={{ mb: 1, pr: isSelected ? 3 : 0, lineHeight: 1.3, color: 'text.primary' }}>
          {meal?.meal_name || 'Unnamed meal'}
        </Typography>

        {meal?.time && (
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1.5, fontWeight: 600 }}>
            ⏱ {meal.time}
          </Typography>
        )}

        {macros && (
          <Stack direction="row" spacing={1} sx={{
            mt: 2, pt: 2,
            borderTop: '1px solid', borderColor: 'divider',
            justifyContent: 'space-around',
          }}>
            <MacroBadge label="kcal"   value={macros.caloriesKcal} color="secondary.main" />
            <MacroBadge label="Protein" value={macros.proteinG}    color="primary.main" />
            <MacroBadge label="Carbs"  value={macros.carbsG}       color="#1976D2" />
            <MacroBadge label="Fat"    value={macros.fatG}         color="#D84315" />
          </Stack>
        )}

        {meal?.serving_size && (
          <Typography variant="caption" sx={{ display: 'block', mt: 2, color: 'text.secondary', fontWeight: 500 }}>
            📦 Portion: {meal.serving_size}
          </Typography>
        )}
        {meal?.caution && (
          <Box sx={{ mt: 1.5, p: 1, bgcolor: '#FFF3E0', borderRadius: 1.5, borderLeft: '3px solid', borderColor: 'secondary.main' }}>
            <Typography variant="caption" sx={{ display: 'block', color: 'secondary.dark', fontWeight: 600 }}>
              ⚠️ {meal.caution}
            </Typography>
          </Box>
        )}
      </CardContent>

      {onToggle && (
        <CardActions sx={{ px: 2.5, pb: 2.5, pt: 0 }}>
          <Button fullWidth variant={isSelected ? 'outlined' : 'contained'}
            color={isSelected ? 'error' : 'primary'} size="medium"
            startIcon={isSelected ? <RemoveCircleOutlined /> : <AddCircleOutlined />}
            onClick={() => onToggle(meal)}>
            {isSelected ? 'Remove' : 'Select'}
          </Button>
        </CardActions>
      )}
    </Card>
  )
}
