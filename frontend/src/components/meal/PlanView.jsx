/**
 * PlanView — Phase 4
 * Organic Light Mode version.
 * Frictionless Inline Substitutions implemented.
 */
import React, { useState } from 'react'
import Box from '@mui/material/Box'
import Grid from '@mui/material/Grid'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import LinearProgress from '@mui/material/LinearProgress'
import Stack from '@mui/material/Stack'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import Chip from '@mui/material/Chip'
import Divider from '@mui/material/Divider'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Collapse from '@mui/material/Collapse'
import Tooltip from '@mui/material/Tooltip'
import { ArrowBack, SwapHoriz, ExpandMore, ExpandLess, InsertChartOutlined, Search } from '@mui/icons-material'

const MEAL_TIME_LABELS = {
  early_morning:'Early Morning', breakfast:'Breakfast',
  mid_morning:'Mid-Morning',     lunch:'Lunch',
  evening:'Evening',             dinner:'Dinner', bedtime:'Bedtime',
}
const MEAL_TIME_EMOJI = {
  early_morning:'🌅', breakfast:'🍳', mid_morning:'🍌',
  lunch:'🍱', evening:'☕', dinner:'🍽️', bedtime:'🌙',
}
const MEAL_TIME_ORDER = ['early_morning','breakfast','mid_morning','lunch','evening','dinner','bedtime']

function MacroProgress({ label, value, target, unit, color }) {
  const pct = target > 0 ? Math.min(100, Math.round((value / target) * 100)) : 0
  return (
    <Box sx={{ mb: 2.5 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 800, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 0.5, fontSize: '0.75rem' }}>
          {label}
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 800, color: color || 'text.primary' }}>
          {Math.round(value)}{unit} <span style={{ color: '#999', fontWeight: 500 }}>/ {Math.round(target)}{unit}</span> — {pct}%
        </Typography>
      </Stack>
      <LinearProgress variant="determinate" value={pct}
        sx={{ 
          height: 10,
          borderRadius: 5,
          bgcolor: `${color}15`,
          '& .MuiLinearProgress-bar': { 
            borderRadius: 5,
            background: `linear-gradient(90deg, ${color}cc, ${color})` 
          } 
        }} />
    </Box>
  )
}

function PlanMealCard({ item, mealTime, onOpenSubstitution }) {
  const [expanded, setExpanded] = useState(false)
  const macros = item?.macros
  const ingredientsStr = item?.ingredients || ''
  const hasIngredients = !!ingredientsStr.trim()

  const ingredientTokens = React.useMemo(() => {
    return ingredientsStr.split(',').map(s => s.trim()).filter(Boolean)
  }, [ingredientsStr])

  return (
    <Card sx={{ 
      height: '100%', 
      borderRadius: 4, 
      border: '1px solid', 
      borderColor: 'divider',
      transition: 'all 0.2s',
      '&:hover': { boxShadow: '0 8px 24px rgba(0,0,0,0.08)' }
    }}>
      <CardContent sx={{ p: 3 }}>
        <Chip label={`${MEAL_TIME_EMOJI[mealTime]} ${MEAL_TIME_LABELS[mealTime]}`}
          size="small" variant="filled" sx={{ mb: 1.5, fontSize: '0.65rem', fontWeight: 800, bgcolor: 'primary.light', color: '#fff' }} />

        <Typography variant="h3" sx={{ mb: 1, lineHeight: 1.3, color: 'text.primary' }}>
          {item?.meal_name || 'No meal selected'}
        </Typography>

        {item?.time && (
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5, mb: 2, fontWeight: 600 }}>
            ⏱ {item.time}
          </Typography>
        )}

        {macros && (
          <Stack direction="row" spacing={1} sx={{
            mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider',
            justifyContent: 'space-around',
          }}>
            {[
              { label:'kcal',    value: macros.caloriesKcal, color:'secondary.main' },
              { label:'Prot',     value: macros.proteinG,     color:'primary.main' },
              { label:'Carb',       value: macros.carbsG,       color:'#1976D2' },
              { label:'Fat',         value: macros.fatG,         color:'#D84315' },
            ].map(({ label, value, color }) => (
              <Box key={label} sx={{ textAlign:'center', minWidth:42 }}>
                <Typography variant="h4" sx={{ color, lineHeight:1, fontWeight: 800 }}>
                  {value != null ? Math.round(value) : '—'}
                </Typography>
                <Typography variant="caption" sx={{ color:'text.secondary', fontSize:'0.6rem', fontWeight: 700, textTransform: 'uppercase' }}>
                  {label}
                </Typography>
              </Box>
            ))}
          </Stack>
        )}

        {item?.serving_size && (
          <Typography variant="caption" sx={{ display:'block', mt: 2, color:'text.secondary', fontWeight: 600 }}>
            📦 {item.serving_size}
          </Typography>
        )}
        
        {item?.caution && (
          <Box sx={{ mt: 2, p: 1, bgcolor: '#FFF3E0', borderRadius: 1.5 }}>
            <Typography variant="caption" sx={{ display:'block', color:'secondary.dark', fontWeight: 700, fontSize: '0.7rem' }}>
              ⚠️ {item.caution}
            </Typography>
          </Box>
        )}

        {(hasIngredients || item?.method) && (
          <>
            <Button size="small" fullWidth variant="text" color="primary" sx={{ mt: 2, fontWeight: 700 }}
              endIcon={expanded ? <ExpandLess /> : <ExpandMore />}
              onClick={() => setExpanded((p) => !p)}>
              {expanded ? 'Hide Details' : 'View Method & Ingredients'}
            </Button>
            <Collapse in={expanded}>
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                {hasIngredients && (
                  <>
                    <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main', textTransform: 'uppercase', letterSpacing: 0.5, display: 'block', mb: 1 }}>Ingredients</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                      {ingredientTokens.map((token, idx) => (
                        <Tooltip key={idx} title="Click to find healthy alternatives">
                          <Chip 
                            label={token} 
                            size="small" 
                            clickable 
                            icon={<SwapHoriz style={{ fontSize: 14 }} />}
                            onClick={() => onOpenSubstitution(token)}
                            sx={{ 
                              fontSize: '0.75rem', 
                              fontWeight: 500,
                              bgcolor: 'rgba(46, 125, 50, 0.05)',
                              borderColor: 'primary.light',
                              '&:hover': { bgcolor: 'primary.light', color: '#fff' }
                            }}
                          />
                        </Tooltip>
                      ))}
                    </Box>
                  </>
                )}
                {item?.method && (
                  <>
                    <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main', textTransform: 'uppercase', letterSpacing: 0.5 }}>Preparation</Typography>
                    <Typography variant="body2" sx={{ mt: 1, color: 'text.primary', fontWeight: 500 }}>{item.method}</Typography>
                  </>
                )}
              </Box>
            </Collapse>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function SubstitutionDialog({ open, mealName, subEditor, onClose, onSelectIngredient, onSelectSubstitute, onFoodSearch }) {
  const [searchQuery, setSearchQuery] = useState('');
  const showIntro = !subEditor.ingredientKey;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { borderRadius: 4 } }}>
      <DialogTitle sx={{ p: 3, pb: 1 }}>
        <Typography variant="h2" color="primary.dark">Easy Swaps</Typography>
        {mealName && <Typography variant="body1" sx={{ color: 'text.secondary', mt: 0.5, fontWeight: 600 }}>{mealName}</Typography>}
      </DialogTitle>
      <DialogContent sx={{ p: 3, pt: 1 }}>
        {subEditor.loading && (
          <Stack alignItems="center" py={6}>
            <CircularProgress size={32} thickness={5} />
            <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary', fontWeight: 600 }}>Finding alternatives...</Typography>
          </Stack>
        )}
        {subEditor.error  && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{subEditor.error}</Alert>}

        {!subEditor.loading && subEditor.choices.length === 0 && !subEditor.error && (
          <Typography variant="body2" sx={{ color: 'text.secondary', py: 4, textAlign: 'center' }}>
            No recommendations found for this item.
          </Typography>
        )}

        {/* STEP 1: SELECT INGREDIENT (Optional/Collapsed if pre-selected) */}
        {!subEditor.loading && subEditor.choices.length > 0 && (
          <Box sx={{ mb: showIntro ? 0 : 4 }}>
            <Typography variant="body2" sx={{ fontWeight: 800, mb: 2, color: 'text.primary', display: 'flex', alignItems: 'center', gap: 1 }}>
              <Search fontSize="small" /> Select an ingredient to swap
            </Typography>
            <Stack direction="row" flexWrap="wrap" spacing={1} useFlexGap>
              {subEditor.choices.map((c) => {
                const isActive = subEditor.ingredientToken === c.token;
                return (
                  <Chip key={`${c.key}-${c.token}`} label={c.label} clickable
                    variant={isActive ? 'filled' : 'outlined'}
                    color={isActive ? 'primary' : 'default'}
                    onClick={() => onSelectIngredient(c)}
                    sx={{ fontWeight: 700 }} />
                );
              })}
            </Stack>
          </Box>
        )}

        {/* STEP 2: PICK REPLACEMENT OR SEARCH */}
        {subEditor.ingredientKey && !subEditor.loading && (
          <>
            <Divider sx={{ my: 3 }} />
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" sx={{ fontWeight: 800, mb: 1.5, color: 'text.primary' }}>
                Quick Swaps (Nutritionally Similar)
              </Typography>
              {(() => {
                const list = Array.isArray(subEditor.substitutesByKey?.[subEditor.ingredientKey])
                  ? subEditor.substitutesByKey[subEditor.ingredientKey] : []
                if (!list.length)
                  return <Typography variant="body2" sx={{ color: 'text.secondary', py: 1 }}>No automatic recommendations.</Typography>
                return (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
                    {list.map((s) => (
                      <Card key={s.name} variant="outlined" 
                        onClick={() => onSelectSubstitute(s)}
                        sx={{ 
                          p: 1.5, minWidth: 140, cursor: 'pointer', borderRadius: 2,
                          transition: 'all 0.2s',
                          '&:hover': { borderColor: 'primary.main', bgcolor: 'primary.light', '& *': { color: '#fff' } }
                        }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{s.name}</Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>{Math.round(s.quantity)}g • {Math.round(s.macros.calories)} kcal</Typography>
                      </Card>
                    ))}
                  </Box>
                )
              })()}
            </Box>

            <Box sx={{ mt: 4 }}>
              <Typography variant="body2" sx={{ fontWeight: 800, mb: 1.5, color: 'text.primary' }}>
                Can't find what you're looking for? Search:
              </Typography>
              <TextField
                fullWidth size="small"
                placeholder="Search 12k+ food items... (e.g. Dosa, Millet, Tofu)"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  onFoodSearch(e.target.value);
                }}
                InputProps={{
                  startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment>,
                }}
                sx={{ mb: 2 }}
              />
              
              {subEditor.searchResults?.length > 0 && (
                <Paper variant="outlined" sx={{ borderRadius: 2, maxHeight: 200, overflow: 'auto' }}>
                  <List dense>
                    {subEditor.searchResults.map((res) => (
                      <ListItem key={res.name} disablePadding>
                        <ListItemButton onClick={() => onSelectSubstitute({ ...res, quantity: 100 })}>
                          <ListItemText 
                            primary={res.name} 
                            secondary={`${res.group} • ${res.macros.calories} kcal/100g`} 
                            primaryTypographyProps={{ fontWeight: 600 }}
                          />
                        </ListItemButton>
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              )}
            </Box>
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 3, pt: 1 }}>
        <Button onClick={onClose} variant="outlined" color="inherit" sx={{ fontWeight: 700, borderRadius: 2 }}>Cancel</Button>
      </DialogActions>
    </Dialog>
  )
}

const MACRO_CONFIG = [
  { key:'caloriesKcal', targetKey:'dailyCalories', label:'Daily Calories 🔥', unit:'kcal', color:'#F57C00' },
  { key:'proteinG',     targetKey:'proteinG',      label:'Protein 💪',  unit:'g',    color:'#2E7D32' },
  { key:'carbsG',       targetKey:'carbsG',        label:'Carbs 🍞',    unit:'g',    color:'#1976D2' },
  { key:'fatG',         targetKey:'fatG',          label:'Total Fats 🥑', unit:'g',    color:'#D84315' },
]

export default function PlanView({
  dayPlans, daysCount, totalsByDay, targets, result,
  subEditor, onBack, onOpenSubstitution,
  onSelectIngredient, onSelectSubstitute, onFoodSearch, onCloseSubstitution,
}) {
  const [dialogCtx, setDialogCtx] = useState(null)

  function openDialog(dayIndex, mealTime, item, initialToken = '') {
    onOpenSubstitution(`${dayIndex}-${mealTime}`, item?.ingredients || '', initialToken)
    setDialogCtx({ dayIndex, mealTime, mealName: item?.meal_name })
  }
  function closeDialog() { setDialogCtx(null); onCloseSubstitution() }

  return (
    <Box sx={{ px: { xs: 2, md: 6 }, py: 6, maxWidth: 1400, mx: 'auto' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 5 }}>
        <Box>
          <Typography variant="h2" color="primary.dark">Your Personalized Plan ✅</Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', mt: 0.5, fontWeight: 500 }}>
            Curated for {daysCount} days based on your unique nutritional profile.
          </Typography>
        </Box>
        <Button variant="outlined" color="inherit" size="large" startIcon={<ArrowBack />} onClick={onBack} sx={{ borderRadius: 8 }}>
          Back
        </Button>
      </Stack>

      {dayPlans.map((dayPlan, dayIndex) => {
        const dayTotals = totalsByDay?.[dayIndex]
        return (
          <Box key={`day-${dayIndex}`} sx={{ mb: 8 }}>
            <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 4 }}>
              <Typography variant="h2" sx={{ bgcolor: 'primary.main', color: '#fff', px: 2, py: 0.5, borderRadius: 2 }}>
                Day {dayIndex + 1}
              </Typography>
              <Divider sx={{ flex: 1 }} />
            </Stack>

            {dayTotals && targets && (
              <Card sx={{ borderRadius: 4, mb: 4, border: '1px solid', borderColor: 'divider', bgcolor: '#F1F8E980' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h4" sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1, color: 'primary.dark' }}>
                    <InsertChartOutlined fontSize="small" /> Day {dayIndex + 1} Nutritional Summary
                  </Typography>
                  <Grid container spacing={3}>
                    {MACRO_CONFIG.map(({ key, targetKey, label, unit, color }) => (
                      <Grid item xs={12} sm={6} md={3} key={key}>
                        <MacroProgress label={label}
                          value={dayTotals[key] || 0}
                          target={targets?.[targetKey] || 0}
                          unit={unit} color={color} />
                      </Grid>
                    ))}
                  </Grid>
                </CardContent>
              </Card>
            )}

            <Grid container spacing={3}>
              {(result?.mealTimes || MEAL_TIME_ORDER).map((mealTime) => {
                const item = dayPlan?.[mealTime]
                if (!item) return null
                return (
                  <Grid item xs={12} sm={6} md={4} xl={3} key={`${dayIndex}-${mealTime}`}>
                    <PlanMealCard item={item} mealTime={mealTime}
                      onOpenSubstitution={(token) => openDialog(dayIndex, mealTime, item, token || '')} />
                  </Grid>
                )
              })}
            </Grid>
          </Box>
        )
      })}

      <SubstitutionDialog 
        open={!!dialogCtx} 
        mealName={dialogCtx?.mealName}
        subEditor={subEditor} 
        onClose={closeDialog}
        onSelectIngredient={onSelectIngredient}
        onFoodSearch={onFoodSearch}
        onSelectSubstitute={(s) => {
          if (dialogCtx) {
            onSelectSubstitute(dialogCtx.dayIndex, dialogCtx.mealTime, s)
          }
          closeDialog()
        }} 
      />
    </Box>
  )
}
