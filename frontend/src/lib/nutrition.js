export const ACTIVITY_MULTIPLIERS = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  heavy: 1.725
}

// BMI-target mode constants
export const BMI_GOAL = 22

// General macro bounds (AMDR-style ranges are % of calories)
// Used as guardrails; defaults are adjusted per BMI class below.
export const FAT_PERCENT_RANGE = { min: 0.2, max: 0.35 }

export const FIBER_G_PER_1000_KCAL = 14
export const FIBER_MIN_G_PER_DAY = 25
export const WATER_ML_PER_KG_RANGE = { min: 30, max: 35 }

function toSafeNumber(value, fallback) {
  const text = String(value ?? '').trim().replace(',', '.')
  const match = text.match(/-?\d+(?:\.\d+)?/)
  const parsed = match ? Number(match[0]) : Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function clamp(value, min, max) {
  if (value < min) return min
  if (value > max) return max
  return value
}

export function normalizeActivityLevel(activityLevel) {
  const v = String(activityLevel || '').trim().toLowerCase()

  const map = {
    sedentary: 'sedentary',
    'desk job': 'sedentary',
    light: 'light',
    'light active': 'light',
    'lightly active': 'light',
    moderate: 'moderate',
    'moderate active': 'moderate',
    'moderately active': 'moderate',
    heavy: 'heavy',
    'very active': 'heavy',
    'very active worker': 'heavy',
    active: 'heavy'
  }

  return map[v] || 'sedentary'
}

export function calculateBMI(weightKg, heightCm) {
  if (!heightCm || heightCm <= 0) return 22
  const hM = heightCm / 100
  return weightKg / (hM * hM)
}

export function calculateTargetWeightKg(heightCm, targetBmi = BMI_GOAL) {
  if (!heightCm || heightCm <= 0) return 0
  const hM = heightCm / 100
  return targetBmi * hM * hM
}

export function getBmiCategory(bmi) {
  if (bmi < 18.5) return 'Underweight'
  if (bmi < 25) return 'Normal'
  if (bmi < 30) return 'Overweight'
  return 'Obese'
}

export function calculateBMR(weightKg, heightCm, age, gender) {
  // Harris-Benedict equation (as in the provided PPT)
  const g = String(gender || '').trim().toLowerCase()
  const isMale = g === 'male' || g === 'm' || g === 'man'
  if (isMale) {
    return 66 + 13.7 * weightKg + 5 * heightCm - 6.8 * age
  }
  return 655 + 9.6 * weightKg + 1.8 * heightCm - 4.7 * age
}

export function calculateTDEE(bmrKcal, activityLevel) {
  const activity = normalizeActivityLevel(activityLevel)
  const mult = ACTIVITY_MULTIPLIERS[activity] || ACTIVITY_MULTIPLIERS.sedentary
  return bmrKcal * mult
}

function getProteinGPerKgTarget(bmiCategory) {
  // There is no universal “protein by BMI class” standard.
  // These presets are product defaults that stay above the 0.8 g/kg/day minimum
  // often cited for adults, and bias higher for weight-change categories.
  const c = String(bmiCategory || '').toLowerCase()
  if (c === 'underweight') return 1.6
  if (c === 'normal') return 1.2
  if (c === 'overweight') return 1.4
  if (c === 'obese') return 1.6
  return 1.2
}

function getFatPercentPreset(bmiCategory) {
  const c = String(bmiCategory || '').toLowerCase()
  if (c === 'underweight') return { min: 0.25, max: 0.35, default: 0.32 }
  if (c === 'normal') return { min: 0.25, max: 0.35, default: 0.28 }
  if (c === 'overweight') return { min: 0.2, max: 0.3, default: 0.22 }
  if (c === 'obese') return { min: 0.2, max: 0.3, default: 0.2 }
  return { min: FAT_PERCENT_RANGE.min, max: FAT_PERCENT_RANGE.max, default: 0.25 }
}

export function calculateDailyTargets(profile) {
  const age = clamp(toSafeNumber(profile.age, 30), 1, 120)
  const heightCm = clamp(toSafeNumber(profile.heightCm, 165), 100, 250)
  const weightKg = clamp(toSafeNumber(profile.weightKg, 60), 20, 300)
  const gender = profile.gender

  const bmi = calculateBMI(weightKg, heightCm)
  const bmiCategory = getBmiCategory(bmi)
  const bmr = calculateBMR(weightKg, heightCm, age, gender)
  const tdee = calculateTDEE(bmr, profile.activityLevel)

  // Target BMI = 22 (fixed) and all macros are based on target weight.
  const targetWeightKgRaw = calculateTargetWeightKg(heightCm, BMI_GOAL)
  const targetWeightKg = Math.round(targetWeightKgRaw * 10) / 10
  const weightDeltaKg = Math.round((targetWeightKg - weightKg) * 10) / 10

  const maintenanceCalories = Math.round(tdee)
  const dailyCalories = Math.round(Math.max(1200, maintenanceCalories))

  // BMI-class macro presets (based on current BMI category, but scaled to target weight).
  const proteinPerKg = getProteinGPerKgTarget(bmiCategory)
  const proteinG = Math.round(targetWeightKg * proteinPerKg)

  const fatPreset = getFatPercentPreset(bmiCategory)
  const fatG = Math.round((dailyCalories * fatPreset.default) / 9)
  const fatGMin = Math.round((dailyCalories * fatPreset.min) / 9)
  const fatGMax = Math.round((dailyCalories * fatPreset.max) / 9)

  const remainingCalories = Math.max(0, dailyCalories - proteinG * 4 - fatG * 9)
  const carbsG = Math.round(remainingCalories / 4)

  const carbsGMin = Math.round(Math.max(0, dailyCalories - proteinG * 4 - fatGMax * 9) / 4)
  const carbsGMax = Math.round(Math.max(0, dailyCalories - proteinG * 4 - fatGMin * 9) / 4)

  // Fiber: 14g per 1000 kcal (basic minimum note: 25g/day)
  const fiberGRaw = Math.round((dailyCalories / 1000) * FIBER_G_PER_1000_KCAL)
  const fiberG = Math.max(FIBER_MIN_G_PER_DAY, fiberGRaw)

  // Water: targetWeight(kg) * 30–35 ml/day (per user requirement: base on target weight)
  const waterLMin = Math.round(targetWeightKg * (WATER_ML_PER_KG_RANGE.min / 1000) * 100) / 100
  const waterLMax = Math.round(targetWeightKg * (WATER_ML_PER_KG_RANGE.max / 1000) * 100) / 100
  // Keep a single representative value for UI/planner (midpoint-ish)
  const waterL = Math.round(targetWeightKg * 0.033 * 100) / 100

  return {
    age,
    heightCm,
    weightKg,
    targetBmi: BMI_GOAL,
    targetWeightKg,
    weightDeltaKg,
    bmi: Math.round(bmi * 10) / 10,
    bmiCategory,
    bmr: Math.round(bmr),
    tdee: Math.round(tdee),
    maintenanceCalories,
    dailyCalories,
    proteinG,
    carbsG,
    fatG,
    fatGMin,
    fatGMax,
    carbsGMin,
    carbsGMax,
    fiberG,
    fiberGRaw,
    fiberGMinimum: FIBER_MIN_G_PER_DAY,
    waterL,
    waterLMin,
    waterLMax,
    activityLevelNormalized: normalizeActivityLevel(profile.activityLevel)
  }
}
