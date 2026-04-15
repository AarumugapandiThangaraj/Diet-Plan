/**
 * MealSelectionFlow — Phase 3
 * Organic Light Mode version with Magic Selection.
 */
import React from 'react'
import Box from '@mui/material/Box'
import Grid from '@mui/material/Grid'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Alert from '@mui/material/Alert'
import Divider from '@mui/material/Divider'
import CircularProgress from '@mui/material/CircularProgress'
import Chip from '@mui/material/Chip'
import Tooltip from '@mui/material/Tooltip'
import { NavigateNext, ArrowBack, AutoAwesome, CheckCircle, InfoOutlined } from '@mui/icons-material'
import TextField from '@mui/material/TextField'
import InputAdornment from '@mui/material/InputAdornment'
import MealCard from '../meal/MealCard.jsx'

const MEAL_TIME_LABELS = {
  early_morning: 'Early Morning', breakfast: 'Breakfast',
  mid_morning: 'Mid-Morning',     lunch: 'Lunch',
  evening: 'Evening',             dinner: 'Dinner', bedtime: 'Bedtime',
}
const MEAL_TIME_EMOJI = {
  early_morning:'🌅', breakfast:'🍳', mid_morning:'🍌',
  lunch:'🍱', evening:'☕', dinner:'🍽️', bedtime:'🌙',
}

export default function MealSelectionFlow({
  selectedMealTimes, rankedMealsByTime, selectedPoolsByTime,
  rankLoading, magicLoading, error, isSelectionComplete,
  onToggleMeal, onMagicSelect, onNext, onBack, magicFeedback
}) {
  const [prefText, setPrefText] = React.useState('')

  const handleMagicClick = () => {
    onMagicSelect(prefText)
  }
  return (
    <Box sx={{ px: { xs: 2, md: 6 }, py: 4, maxWidth: 1400, mx: 'auto' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h2" sx={{ color: 'primary.dark' }}>Choose Your Meals 🍽️</Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', mt: 0.5, fontWeight: 500 }}>
            Select at least one option per slot to fill your week.
          </Typography>
        </Box>
        <Stack direction="row" spacing={2} alignItems="center">
          <TextField 
            variant="outlined"
            size="small"
            placeholder="Describe your preference (e.g. I like chicken, high protein)"
            value={prefText}
            onChange={(e) => setPrefText(e.target.value)}
            disabled={magicLoading}
            sx={{ 
              width: 350, 
              bgcolor: 'background.paper',
              '& .MuiOutlinedInput-root': { borderRadius: 4 }
            }}
            InputProps={{
              startIcon: <InfoOutlined color="action" />
            }}
          />
          <Tooltip title="Automatically select the best options based on your targets and preferences!" placement="bottom">
            <Button 
              variant="contained" 
              color="secondary" 
              startIcon={magicLoading ? <CircularProgress size={20} color="inherit" /> : <AutoAwesome />}
              onClick={handleMagicClick}
              disabled={magicLoading}
              sx={{ boxShadow: '0 4px 14px rgba(245, 124, 0, 0.3)', borderRadius: 4, height: 40 }}
            >
              {magicLoading ? 'Curating...' : 'Magic Pick'}
            </Button>
          </Tooltip>
          <Button variant="outlined" color="inherit" startIcon={<ArrowBack />} onClick={onBack} sx={{ borderRadius: 4, height: 40 }}>Back</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 3 }}>{error}</Alert>}

      {magicFeedback && magicFeedback.filtered_count > 0 && (
        <Alert 
          severity="info" 
          icon={<AutoAwesome fontSize="inherit" />}
          sx={{ mb: 3, borderRadius: 3, bgcolor: '#E3F2FD', '& .MuiAlert-icon': { color: '#0288D1' } }}
        >
          <b>Magic Filter Applied:</b> {magicFeedback.filtered_count} meals were hidden based on your profile allergies and avoided ingredients.
        </Alert>
      )}

      {rankLoading ? (
        <Stack alignItems="center" justifyContent="center" sx={{ py: 12 }}>
          <CircularProgress color="primary" thickness={5} size={50} />
          <Typography variant="h3" sx={{ mt: 3, color: 'text.secondary' }}>
            Curating your healthy options…
          </Typography>
        </Stack>
      ) : (
        <>
          {selectedMealTimes.map((mealTime) => {
            const ranked    = rankedMealsByTime?.[mealTime] || []
            const topOptions = ranked.slice(0, 8) // Show top 8 as options
            const pickedList = Array.isArray(selectedPoolsByTime?.[mealTime]) ? selectedPoolsByTime[mealTime] : []
            const pickedIds  = new Set(pickedList.map((m) => m?.Meal_ID).filter(Boolean))

            return (
              <Card key={mealTime} sx={{ mb: 4, borderRadius: 4, overflow: 'hidden', border: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ bgcolor: 'rgba(46, 125, 50, 0.04)', px: 3, py: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Stack direction="row" alignItems="center" spacing={2}>
                      <Typography variant="h2" sx={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span style={{ fontSize: '1.5rem' }}>{MEAL_TIME_EMOJI[mealTime]}</span> {MEAL_TIME_LABELS[mealTime]}
                      </Typography>
                      {pickedList.length > 0 && (
                        <Chip 
                          icon={<CheckCircle style={{ color: '#fff', fontSize: 16 }} />}
                          label={`${pickedList.length} ready`} 
                          size="small" 
                          sx={{ bgcolor: 'primary.main', color: '#fff', fontWeight: 700 }} 
                        />
                      )}
                    </Stack>
                  </Stack>
                </Box>
                
                <CardContent sx={{ p: 3 }}>
                  {pickedList.length > 0 && (
                    <>
                      <Box sx={{ mb: 3, p: 2, borderRadius: 3, bgcolor: '#F1F8E9', border: '1px solid', borderColor: 'primary.light' }}>
                        <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.dark', display: 'block', mb: 1.5, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                          Current Favorites for this Slot
                        </Typography>
                        <Stack direction="row" flexWrap="wrap" spacing={1} useFlexGap>
                          {pickedList.map((m) => (
                            <Chip 
                              key={m.Meal_ID} 
                              label={m.meal_name}
                              onDelete={() => onToggleMeal(mealTime, m)}
                              color="primary" 
                              variant="outlined" 
                              size="medium" 
                              sx={{ bgcolor: '#fff', fontWeight: 600 }} 
                            />
                          ))}
                        </Stack>
                      </Box>
                      <Divider sx={{ mb: 3 }} />
                    </>
                  )}

                  {topOptions.length === 0 ? (
                    <Box sx={{ py: 6, textAlign: 'center' }}>
                      <Typography variant="body1" sx={{ color: 'text.secondary', mb: 1, fontWeight: 500 }}>
                        No matching meals found for this slot. 🥗
                      </Typography>
                      <Typography variant="body2" sx={{ color: 'text.disabled', fontStyle: 'italic' }}>
                        Try relaxing your natural language preferences or check your allergy profile.
                      </Typography>
                    </Box>
                  ) : (
                    <Grid container spacing={3}>
                      {topOptions.map((meal) => (
                        <Grid item xs={12} sm={6} md={4} lg={3} key={meal.Meal_ID}>
                          <MealCard 
                            meal={meal} 
                            isSelected={pickedIds.has(meal.Meal_ID)}
                            onToggle={(m) => onToggleMeal(mealTime, m)} 
                          />
                        </Grid>
                      ))}
                    </Grid>
                  )}
                </CardContent>
              </Card>
            )
          })}

          <Box sx={{ 
            position: 'sticky', bottom: 24, zIndex: 10,
            display: 'flex', justifyContent: 'center', mt: 4
          }}>
            <Card sx={{ 
              p: 2, borderRadius: 10, bgcolor: 'background.paper', 
              boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
              border: '1px solid', borderColor: 'primary.main'
            }}>
              <Stack direction="row" spacing={3} alignItems="center">
                <Button variant="outlined" color="inherit" startIcon={<ArrowBack />} onClick={onBack} sx={{ borderRadius: 8 }}>
                  Back
                </Button>
                
                <Divider orientation="vertical" flexItem />
                
                <Box sx={{ textAlign: 'center', minWidth: 200 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', display: 'block' }}>
                    PROGRESS
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 800, color: isSelectionComplete ? 'primary.main' : 'text.primary' }}>
                    {isSelectionComplete ? '✅ Selection Complete' : '⚠️ Pick meals for all slots'}
                  </Typography>
                </Box>

                <Button 
                  variant="contained" 
                  color="primary" 
                  size="large"
                  endIcon={<NavigateNext />} 
                  onClick={onNext} 
                  disabled={!isSelectionComplete}
                  sx={{ borderRadius: 8, px: 4 }}
                >
                  Continue: Arrange Days
                </Button>
              </Stack>
            </Card>
          </Box>
        </>
      )}
    </Box>
  )
}
