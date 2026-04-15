/**
 * AppHeader — hero banner with live stat pills.
 * Organic Light Mode version.
 */
import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'

export default function AppHeader({ studioMeta, profile, goal }) {
  return (
    <Box
      component="header"
      sx={{
        background: 'linear-gradient(135deg, #E8F5E9 0%, #FFFFFF 100%)',
        borderBottom: '1px solid',
        borderColor: 'divider',
        px: { xs: 3, md: 8 },
        py: { xs: 3, md: 5 },
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 2,
      }}
    >
      <Box>
        <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 800, letterSpacing: 1.5, textTransform: 'uppercase' }}>
          Personalized Nutrition Planner
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.5, lineHeight: 1.2, color: 'text.primary' }}>
          Diet Plan Studio ✨
        </Typography>
        <Typography variant="body1" sx={{ mt: 1, color: 'text.secondary', maxWidth: 520, fontWeight: 500 }}>
          Set your profile, review live BMI / BMR / TDEE targets, then build a professional multi-day meal plan with fresh ingredients.
        </Typography>
      </Box>

      <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
        <Chip
          label={`🍽️ ${studioMeta?.mealsCount ?? '—'} meals`}
          size="medium"
          variant="filled"
          sx={{ bgcolor: 'primary.light', color: 'primary.contrastText', fontWeight: 700, px: 1 }}
        />
        <Chip
          label={`🎯 ${goal === 'hair_repair' ? 'Hair Repair' : 'Skin Repair'}`}
          size="medium"
          variant="filled"
          sx={{ bgcolor: 'secondary.main', color: 'secondary.contrastText', fontWeight: 700, px: 1 }}
        />
      </Stack>
    </Box>
  )
}
