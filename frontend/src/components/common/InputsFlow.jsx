/**
 * InputsFlow — Phase 2
 * Organic Light Mode version.
 */
import React from 'react'
import Grid from '@mui/material/Grid'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import TextField from '@mui/material/TextField'
import MenuItem from '@mui/material/MenuItem'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Alert from '@mui/material/Alert'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import { NavigateNext, RestartAlt, CheckCircle } from '@mui/icons-material'

const GOALS = [
  { label: 'Skin Repair', value: 'skin_repair' },
  { label: 'Hair Repair', value: 'hair_repair' },
]
const ACTIVITY = [
  { label: 'Sedentary', value: 'sedentary' },
  { label: 'Light',     value: 'light' },
  { label: 'Moderate',  value: 'moderate' },
  { label: 'Heavy',     value: 'heavy' },
]
const DIET = [
  { label: '🥦 Vegetarian', value: 'veg' },
  { label: '🍗 Non-Veg',   value: 'non_veg' },
]
const PLAN_DAYS = [
  { label: '7 days',  value: 7 },
  { label: '14 days', value: 14 },
  { label: '21 days', value: 21 },
]
const MEAL_TIME_ORDER = ['early_morning','breakfast','mid_morning','lunch','evening','dinner','bedtime']
const MEAL_TIME_LABELS = {
  early_morning: 'Early Morning', breakfast: 'Breakfast',
  mid_morning: 'Mid-Morning',     lunch: 'Lunch',
  evening: 'Evening',             dinner: 'Dinner', bedtime: 'Bedtime',
}
const MEAL_TIME_EMOJI = {
  early_morning:'🌅', breakfast:'🍳', mid_morning:'🍌',
  lunch:'🍱', evening:'☕', dinner:'🍽️', bedtime:'🌙',
}

function MetricCard({ label, value, unit, sublabel, highlight }) {
  return (
    <Card sx={{
      bgcolor: highlight ? '#E8F5E9' : '#FFFFFF',
      border: '1px solid',
      borderColor: highlight ? 'primary.main' : 'rgba(0,0,0,0.08)',
      boxShadow: highlight ? '0 4px 14px rgba(46, 125, 50, 0.1)' : '0 2px 8px rgba(0,0,0,0.02)',
      height: '100%',
      transition: 'all 0.25s',
      '&:hover': {
        transform: 'translateY(-2px)',
        boxShadow: '0 6px 18px rgba(0,0,0,0.06)',
      }
    }}>
      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 1, fontWeight: 700 }}>
          {label}
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, color: highlight ? 'primary.main' : 'text.primary', fontSize: '1.75rem' }}>
          {value ?? '—'}
        </Typography>
        {unit && <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>{unit}</Typography>}
        {sublabel && (
          <Typography variant="caption" display="block" sx={{ mt: 1, color: 'secondary.main', fontWeight: 800, fontSize: '0.7rem' }}>
            {sublabel}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}

function SelectableChip({ label, selected, onClick, disabled }) {
  return (
    <Chip
      label={label}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      icon={selected ? <CheckCircle style={{ fontSize: 16 }} /> : undefined}
      variant={selected ? 'filled' : 'outlined'}
      color={selected ? 'primary' : 'default'}
      sx={{
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontWeight: 700,
        px: 1,
        transition: 'all 0.2s',
        '&:hover': { bgcolor: selected ? 'primary.dark' : 'rgba(46, 125, 50, 0.08)' },
      }}
    />
  )
}

export default function InputsFlow({
  profile, targets, planDays, selectedMealTimes, mealsPerDay, error,
  onProfileChange, onPlanDaysChange, onMealsPerDayChange,
  onToggleMealTime, onNext, onReset,
}) {
  return (
    <Box sx={{ px: { xs: 2, md: 4 }, py: 4, mx: 'auto' }}>
  <Grid container spacing={4} alignItems="stretch">

    {/* LEFT: Inputs */}
    <Grid item xs={12} md={6} lg={7}>
      <Card sx={{ borderRadius: 4, overflow: 'hidden', height: '100%' }}>
        <Box sx={{ p: 4 }}>

          <Typography variant="h2" gutterBottom color="primary.dark">
            Your Profile 🧾
          </Typography>

          <Typography
            variant="body1"
            sx={{ color: 'text.secondary', mb: 4, fontWeight: 500 }}
          >
            Adjust your baseline data to calculate precise nutritional requirements.
          </Typography>

          {/* BASIC INFO */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={6}>
              <TextField fullWidth label="Age" type="number"
                value={profile.age}
                onChange={(e) => onProfileChange({ age: e.target.value })} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth label="Gender" select
                value={profile.gender}
                onChange={(e) => onProfileChange({ gender: e.target.value })}>
                <MenuItem value="female">Female</MenuItem>
                <MenuItem value="male">Male</MenuItem>
              </TextField>
            </Grid>
          </Grid>

          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={6}>
              <TextField fullWidth label="Height (cm)"
                value={profile.heightCm}
                onChange={(e) => onProfileChange({ heightCm: e.target.value })} />
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth label="Weight (kg)"
                value={profile.weightKg}
                onChange={(e) => onProfileChange({ weightKg: e.target.value })} />
            </Grid>
          </Grid>

          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={6}>
              <TextField fullWidth label="Primary Goal" select
                value={profile.goal}
                onChange={(e) => onProfileChange({ goal: e.target.value })}>
                {GOALS.map((g) => (
                  <MenuItem key={g.value} value={g.value}>{g.label}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={6}>
              <TextField fullWidth label="Activity Level" select
                value={profile.activityLevel}
                onChange={(e) => onProfileChange({ activityLevel: e.target.value })}>
                {ACTIVITY.map((a) => (
                  <MenuItem key={a.value} value={a.value}>{a.label}</MenuItem>
                ))}
              </TextField>
            </Grid>
          </Grid>

          <Divider sx={{ my: 4 }} />

          {/* 🔥 DIET CONFIGURATION (NOW INCLUDED) */}
          <Typography variant="h4" sx={{ mb: 2 }}>
            Diet & Plan Configuration
          </Typography>

          {/* DIET TYPE */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="body2" sx={{ fontWeight: 700, mb: 1.5 }}>
              Preference
            </Typography>
            <Stack direction="row" spacing={1.5}>
              {DIET.map((d) => (
                <SelectableChip
                  key={d.value}
                  label={d.label}
                  selected={profile.dietType === d.value}
                  onClick={() => onProfileChange({ dietType: d.value })}
                />
              ))}
            </Stack>
          </Box>

          {/* PLAN DAYS */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="body2" sx={{ fontWeight: 700, mb: 1.5 }}>
              Duration
            </Typography>
            <Stack direction="row" spacing={1.5}>
              {PLAN_DAYS.map((d) => (
                <SelectableChip
                  key={d.value}
                  label={d.label}
                  selected={planDays === d.value}
                  onClick={() => onPlanDaysChange(d.value)}
                />
              ))}
            </Stack>
          </Box>

          {/* MEALS + SLOTS */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={6}>
              <TextField fullWidth label="Meals per day" select
                value={mealsPerDay}
                onChange={(e) => onMealsPerDayChange(e.target.value)}>
                {Array.from({ length: 6 }, (_, i) => i + 2).map((n) => (
                  <MenuItem key={n} value={n}>{n} meals</MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="body2" sx={{ fontWeight: 700, mb: 1.5 }}>
                Select Slots ({selectedMealTimes.length}/{mealsPerDay})
              </Typography>

              <Stack direction="row" flexWrap="wrap" spacing={1} useFlexGap>
                {MEAL_TIME_ORDER.map((mt) => (
                  <SelectableChip
                    key={mt}
                    label={`${MEAL_TIME_EMOJI[mt]} ${MEAL_TIME_LABELS[mt]}`}
                    selected={selectedMealTimes.includes(mt)}
                    disabled={
                      !selectedMealTimes.includes(mt) &&
                      selectedMealTimes.length >= mealsPerDay
                    }
                    onClick={() => onToggleMealTime(mt)}
                  />
                ))}
              </Stack>
            </Grid>
          </Grid>

          {/* ALLERGIES */}
          <TextField
            fullWidth
            label="Allergies (comma-separated)"
            value={profile.allergies}
            onChange={(e) => onProfileChange({ allergies: e.target.value })}
            placeholder="None"
            sx={{ mb: 4 }}
          />

          {error && (
            <Alert severity="error" sx={{ mb: 4 }}>
              {error}
            </Alert>
          )}

          {/* ACTIONS */}
          <Stack direction="row" spacing={2}>
            <Button
              variant="contained"
              size="large"
              endIcon={<NavigateNext />}
              onClick={onNext}
              sx={{ flex: 2, height: 56 }}
            >
              Next: Choose Meals
            </Button>

            <Button
              variant="outlined"
              size="large"
              startIcon={<RestartAlt />}
              onClick={onReset}
              sx={{ flex: 1 }}
            >
              Reset
            </Button>
          </Stack>

        </Box>
      </Card>
    </Grid>

    {/* RIGHT: Metrics */}
    <Grid item xs={12} md={6} lg={5}>
      <Box sx={{ position: { md: 'sticky' }, top: 32 }}>
        
            <Typography variant="h2" gutterBottom color="primary.dark">Nutritional Targets 📊</Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 3, fontWeight: 500 }}>
              Calculated precisely based on your unique body metrics.
            </Typography>
            
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={6}><MetricCard label="BMI ⚖️" value={targets?.bmi} sublabel={targets?.bmiCategory} highlight /></Grid>
              <Grid item xs={6}><MetricCard label="TDEE ⚡" value={targets?.tdee} unit="kcal/day" highlight /></Grid>
              <Grid item xs={6}><MetricCard label="Daily Goal 🔥" value={targets?.dailyCalories} unit="kcal/day" /></Grid>
              <Grid item xs={6}><MetricCard label="Water 💧" value={targets?.waterL} unit="L/day" /></Grid>
            </Grid>

            {targets && (
              <Card sx={{ borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h3" sx={{ mb: 3 }}>Daily Macro Breakdown</Typography>
                  {[
                    { label: 'Protien 💪', value: targets.proteinG, unit: 'g', color: 'primary.main', track: '#E8F5E9' },
                    { label: 'Carbs 🍞',   value: targets.carbsG,   unit: 'g', color: '#1E88E5',   track: '#E3F2FD' },
                    { label: 'Fats 🥑',    value: targets.fatG,     unit: 'g', color: '#F4511E',   track: '#FBE9E7' },
                  ].map(({ label, value, unit, color, track }) => (
                    <Box key={label} sx={{ mb: 2.5 }}>
                      <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{label}</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 800, color }}>{Math.round(value)}{unit}</Typography>
                      </Stack>
                      <Box sx={{ height: 8, bgcolor: track, borderRadius: 4, overflow: 'hidden' }}>
                        <Box sx={{ height: '100%', width: '100%', bgcolor: color, opacity: 0.8 }} />
                      </Box>
                    </Box>
                  ))}
                  <Divider sx={{ my: 3 }} />
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic', display: 'block', textAlign: 'center' }}>
                    * Values adjusted for your "{profile.goal.replace('_',' ')}" goal.
                  </Typography>
                </CardContent>
              </Card>
            )}
      </Box>
    </Grid>

  </Grid>
</Box>
  )
}
