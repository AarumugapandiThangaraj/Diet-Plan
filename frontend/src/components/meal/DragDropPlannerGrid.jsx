/**
 * DragDropPlannerGrid — Phase 4
 * Organic Light Mode version.
 * Day-First structural redesign (requested).
 */
import React, { useMemo, useRef } from 'react'
import {
  DndContext, DragOverlay, PointerSensor,
  useSensor, useSensors, closestCenter,
} from '@dnd-kit/core'
import { useDraggable, useDroppable } from '@dnd-kit/core'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Alert from '@mui/material/Alert'
import Chip from '@mui/material/Chip'
import Divider from '@mui/material/Divider'
import Tooltip from '@mui/material/Tooltip'
import Grid from '@mui/material/Grid'
import { NavigateNext, ArrowBack, DragIndicator, Info } from '@mui/icons-material'

const MEAL_TIME_LABELS = {
  early_morning: 'Early Morning', breakfast: 'Breakfast',
  mid_morning: 'Mid-Morning',     lunch: 'Lunch',
  evening: 'Evening',             dinner: 'Dinner', bedtime: 'Bedtime',
}
const MEAL_TIME_EMOJI = {
  early_morning:'🌅', breakfast:'🍳', mid_morning:'🍌',
  lunch:'🍱', evening:'☕', dinner:'🍽️', bedtime:'🌙',
}

function DraggableMealChip({ mealId, mealName, mealTime, dayIndex, inPool }) {
  const id = inPool ? `pool::${mealTime}::${mealId}` : `slot::${mealTime}::${dayIndex}::${mealId}`
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id })
  
  return (
    <Box ref={setNodeRef} {...listeners} {...attributes} sx={{ 
      width: '100%', 
      opacity: isDragging ? 0.3 : 1,
      cursor: isDragging ? 'grabbing' : 'grab',
    }}>
      <Card variant="outlined" sx={{ 
        p: 1, 
        border: '1px solid', 
        borderColor: inPool ? 'secondary.light' : 'primary.light',
        bgcolor: '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        display: 'flex', 
        alignItems: 'center', 
        gap: 1 
      }}>
        <DragIndicator sx={{ fontSize: 16, color: 'text.secondary' }} />
        <Typography variant="body2" noWrap sx={{ fontWeight: 700, flex: 1, fontSize: '0.8rem' }}>
          {mealName}
        </Typography>
      </Card>
    </Box>
  )
}

function DroppableSlot({ id, mealTime, children, isEmpty }) {
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <Box ref={setNodeRef} sx={{
      minHeight: 48,
      p: 0.5,
      borderRadius: 2,
      border: '2px dashed',
      borderColor: isOver ? 'primary.main' : 'rgba(0,0,0,0.06)',
      bgcolor: isOver ? 'primary.light' : 'transparent',
      transition: 'all 0.2s',
      display: 'flex',
      alignItems: 'center',
    }}>
      {children || (
        <Typography variant="caption" sx={{ color: 'text.secondary', pl: 1, fontStyle: 'italic', opacity: 0.6 }}>
           Empty Slot
        </Typography>
      )}
    </Box>
  )
}

function DayCard({ dayIndex, mealTimes, assignment, mealLookup }) {
  return (
    <Card sx={{ 
      minWidth: 260, 
      maxWidth: 300, 
      flexShrink: 0,
      borderRadius: 4, 
      border: '1px solid', 
      borderColor: 'divider',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
      height: 'fit-content'
    }}>
      <Box sx={{ bgcolor: 'primary.main', py: 1, px: 2, color: '#fff', textAlign: 'center' }}>
        <Typography variant="h3" sx={{ fontSize: '1.1rem', color: '#fff' }}>Day {dayIndex + 1}</Typography>
      </Box>
      <CardContent sx={{ p: 2 }}>
        {mealTimes.map(mt => {
          const mealId = assignment?.[mt]?.[dayIndex]
          const meal = mealId ? mealLookup?.[mt]?.[mealId] : null
          const droppableId = `slot::${mt}::${dayIndex}`

          return (
            <Box key={mt} sx={{ mb: 2, '&:last-child': { mb: 0 } }}>
              <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5, textTransform: 'uppercase' }}>
                {MEAL_TIME_EMOJI[mt]} {MEAL_TIME_LABELS[mt]}
              </Typography>
              <DroppableSlot id={droppableId} mealTime={mt} isEmpty={!meal}>
                {meal ? (
                  <DraggableMealChip 
                    mealId={meal.Meal_ID} 
                    mealName={meal.meal_name} 
                    mealTime={mt} 
                    dayIndex={dayIndex} 
                  />
                ) : null}
              </DroppableSlot>
            </Box>
          )
        })}
      </CardContent>
    </Card>
  )
}

export default function DragDropPlannerGrid({
  selectedMealTimes, selectedPoolsByTime, assignmentByTime,
  selectionDays, error, onAssign, onUnassign, onSwap, onNext, onBack,
}) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))
  const [activeDrag, setActiveDrag] = React.useState(null)
  const scrollRef = useRef(null)

  const mealLookup = useMemo(() => {
    const map = {}
    selectedMealTimes.forEach(mt => {
      map[mt] = {}
      ;(selectedPoolsByTime?.[mt] || []).forEach(m => {
        if (m?.Meal_ID) map[mt][m.Meal_ID] = m
      })
    })
    return map
  }, [selectedMealTimes, selectedPoolsByTime])

  function handleDragStart(event) { setActiveDrag(event.active.id) }

  function handleDragEnd(event) {
    setActiveDrag(null)
    const { active, over } = event
    if (!over) return

    const srcParts = String(active.id).split('::')
    const dstParts = String(over.id).split('::')
    const [srcType, srcMealTime, srcDay, srcId] = srcParts
    const [dstType, dstMealTime, dstDay] = dstParts

    // Logic: If dropped on a slot of the same meal time...
    if (dstType === 'slot' && srcMealTime === dstMealTime) {
      if (srcType === 'pool') {
        onAssign(srcMealTime, Number(dstDay), srcDay) // srcDay is mealId in pool-strings
      } else if (srcType === 'slot') {
        onSwap(srcMealTime, Number(srcDay), Number(dstDay))
      }
    }
    // Logic: Dragging back to pool area (unassign)
    if (dstType === 'pool-zone' && srcType === 'slot' && srcMealTime === dstMealTime) {
      onUnassign(srcMealTime, Number(srcDay))
    }
  }

  const activeLabel = useMemo(() => {
    if (!activeDrag) return ''
    const [type, mt, dayOrId, mId] = String(activeDrag).split('::')
    if (type === 'pool') return mealLookup?.[mt]?.[dayOrId]?.meal_name || ''
    const actualId = mId || assignmentByTime?.[mt]?.[Number(dayOrId)]
    return mealLookup?.[mt]?.[actualId]?.meal_name || ''
  }, [activeDrag, mealLookup, assignmentByTime])

  return (
    <Box sx={{ px: { xs: 2, md: 6 }, py: 4, maxWidth: '100vw', overflowX: 'hidden' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4, maxWidth: 1400, mx: 'auto' }}>
        <Box>
          <Typography variant="h2" color="primary.dark">Arrange Your Schedule 📅</Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', mt: 0.5, fontWeight: 500 }}>
            Meals are pre-filled! Drag between days to customize, or drag from the pool below.
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Tooltip title="Help: Drag meals between days to swap them. Use the pool area to find alternates.">
            <Button color="inherit" startIcon={<Info />}>How to use</Button>
          </Tooltip>
          <Button variant="outlined" color="inherit" startIcon={<ArrowBack />} onClick={onBack}>Back</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3, maxWidth: 1400, mx: 'auto', borderRadius: 3 }}>{error}</Alert>}

      <DndContext sensors={sensors} collisionDetection={closestCenter}
        onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        
        {/* DAY SCROLLER */}
        <Box 
          ref={scrollRef}
          sx={{ 
            display: 'flex', 
            gap: 3, 
            pb: 4, 
            overflowX: 'auto', 
            cursor: 'grab', 
            '&:active': { cursor: 'grabbing' },
            '&::-webkit-scrollbar': { height: 10 },
            '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0,0,0,0.1)', borderRadius: 5 }
          }}>
          {Array.from({ length: selectionDays }, (_, dayIndex) => (
            <DayCard 
              key={dayIndex} 
              dayIndex={dayIndex} 
              mealTimes={selectedMealTimes} 
              assignment={assignmentByTime}
              mealLookup={mealLookup}
            />
          ))}
        </Box>

        {/* POOL AREA */}
        <Box sx={{ mt: 6, maxWidth: 1400, mx: 'auto' }}>
          <Typography variant="h3" sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
             Selection Pool <Chip label="Optional Refinement" size="small" variant="outlined" sx={{ fontWeight: 800, fontSize: '0.6rem' }} />
          </Typography>
          <Grid container spacing={4}>
            {selectedMealTimes.map(mt => {
              const pool = selectedPoolsByTime?.[mt] || []
              const { setNodeRef, isOver } = useDroppable({ id: `pool-zone::${mt}` })
              return (
                <Grid item xs={12} md={6} lg={4} key={mt} ref={setNodeRef}>
                  <Card sx={{ 
                    bgcolor: isOver ? 'secondary.light' : '#f8fbfc', 
                    border: '1px solid', 
                    borderColor: 'divider',
                    borderRadius: 3,
                    minHeight: 120
                  }}>
                    <CardContent sx={{ p: 2 }}>
                      <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary', display: 'flex', gap: 0.5, mb: 1.5, textTransform: 'uppercase' }}>
                        {MEAL_TIME_EMOJI[mt]} {MEAL_TIME_LABELS[mt]} Pool
                      </Typography>
                      <Stack direction="row" flexWrap="wrap" spacing={1} useFlexGap>
                        {pool.map(m => (
                          <DraggableMealChip 
                            key={m.Meal_ID} 
                            mealId={m.Meal_ID} 
                            mealName={m.meal_name} 
                            mealTime={mt} 
                            inPool 
                          />
                        ))}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              )
            })}
          </Grid>
        </Box>

        <DragOverlay>
          {activeDrag ? (
            <Card sx={{ 
              p: 1.5, minWidth: 200, bgcolor: 'secondary.main', color: '#fff', 
              boxShadow: '0 12px 32px rgba(245, 124, 0, 0.4)', borderRadius: 2
            }}>
              <Typography variant="body2" sx={{ fontWeight: 800 }}>{activeLabel}</Typography>
            </Card>
          ) : null}
        </DragOverlay>
      </DndContext>

      <Box sx={{ mt: 6, display: 'flex', justifyContent: 'center', maxWidth: 1400, mx: 'auto' }}>
        <Button 
          variant="contained" 
          color="primary" 
          size="large" 
          endIcon={<NavigateNext />} 
          onClick={onNext}
          sx={{ minWidth: 260, height: 64, fontSize: '1.2rem', borderRadius: 8 }}
        >
          View Final Plan ✅
        </Button>
      </Box>
    </Box>
  )
}
