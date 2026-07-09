import { httpJson } from './apiClient.js'

function formatMealForGateway(meal) {
  if (!meal) return meal;
  
  // Clone to avoid modifying React/original state
  const formattedMeal = JSON.parse(JSON.stringify(meal));

  // Map meal_name to name and delete non-whitelisted property
  if (formattedMeal.meal_name !== undefined) {
    formattedMeal.name = formattedMeal.meal_name;
    delete formattedMeal.meal_name;
  } else if (formattedMeal.name === undefined) {
    formattedMeal.name = '';
  }

  // Map foods_struct to foods and delete non-whitelisted property
  if (formattedMeal.foods_struct !== undefined) {
    formattedMeal.foods = formattedMeal.foods_struct.map(food => {
      const formattedFood = { ...food };
      if (formattedFood.ingredients_struct !== undefined) {
        formattedFood.ingredients = formattedFood.ingredients_struct;
        delete formattedFood.ingredients_struct;
      }
      return formattedFood;
    });
    delete formattedMeal.foods_struct;
  }

  // Map Meal_ID to id
  if (formattedMeal.Meal_ID !== undefined) {
    formattedMeal.id = formattedMeal.Meal_ID;
    delete formattedMeal.Meal_ID;
  }

  // Map _macros to macros
  if (formattedMeal._macros !== undefined) {
    formattedMeal.macros = formattedMeal._macros;
    delete formattedMeal._macros;
  }

  return formattedMeal;
}

export function fetchMealSwapOptions(
  profile,
  mealTime,
  currentMealId,
  { targetMacros = null, excludeMealIds = [], allowedMealIds = [], topN = 5, signal } = {}
) {
  return httpJson('/api/studio/swap/meal/options', {
    method: 'POST',
    body: { profile, mealTime, currentMealId, targetMacros, excludeMealIds, allowedMealIds, topN },
    signal
  })
}

export function applyMealSwap(meal, { signal } = {}) {
  return httpJson('/api/studio/swap/meal/apply', {
    method: 'POST',
    body: { meal: formatMealForGateway(meal) },
    signal
  })
}

export function fetchFoodSwapOptions(meal, foodName, { topN = 5, signal } = {}) {
  return httpJson('/api/studio/swap/food/options', {
    method: 'POST',
    body: { meal: formatMealForGateway(meal), foodName, topN },
    signal
  })
}

export function applyFoodSwap(meal, option, planId, version, { signal } = {}) {
  return httpJson('/api/studio/swap/food/apply', {
    method: 'POST',
    body: { meal: formatMealForGateway(meal), option, planId, version },
    signal
  })
}

export function fetchIngredientSwapOptions(meal, ingredientQuery, { topN = 5, signal } = {}) {
  return httpJson('/api/studio/swap/ingredient/options', {
    method: 'POST',
    body: { meal: formatMealForGateway(meal), ingredientQuery, topN },
    signal
  })
}

export function applyIngredientSwap(meal, option, { signal } = {}) {
  return httpJson('/api/studio/swap/ingredient/apply', {
    method: 'POST',
    body: { meal: formatMealForGateway(meal), option },
    signal
  })
}
