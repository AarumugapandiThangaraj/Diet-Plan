/**
 * Admin API Service
 * Handles all admin data entry API calls
 */

const API_BASE = 'http://localhost:8000/api/admin';

const createGenericApi = (endpoint) => ({
  list: async (limit = 100, offset = 0) => {
    const response = await fetch(`${API_BASE}/${endpoint}?limit=${limit}&offset=${offset}`);
    if (!response.ok) throw new Error(`Failed to fetch ${endpoint}`);
    return response.json();
  },
  get: async (id) => {
    const response = await fetch(`${API_BASE}/${endpoint}/${id}`);
    if (!response.ok) throw new Error(`${endpoint} not found`);
    return response.json();
  },
  create: async (data) => {
    const response = await fetch(`${API_BASE}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`Failed to create ${endpoint}`);
    return response.json();
  },
  update: async (id, data) => {
    const response = await fetch(`${API_BASE}/${endpoint}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`Failed to update ${endpoint}`);
    return response.json();
  },
  delete: async (id, permanent = false) => {
    const response = await fetch(`${API_BASE}/${endpoint}/${id}?permanent=${permanent}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error(`Failed to delete ${endpoint}`);
    return response.json();
  }
});

export const adminApi = {
  // ================ CUISINES ================
  cuisines: {
    list: async (limit = 100, offset = 0) => {
      const response = await fetch(`${API_BASE}/cuisines?limit=${limit}&offset=${offset}`);
      if (!response.ok) throw new Error('Failed to fetch cuisines');
      return response.json();
    },
    get: async (id) => {
      const response = await fetch(`${API_BASE}/cuisines/${id}`);
      if (!response.ok) throw new Error('Cuisine not found');
      return response.json();
    },
    create: async (data) => {
      const response = await fetch(`${API_BASE}/cuisines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to create cuisine');
      return response.json();
    },
    update: async (id, data) => {
      const response = await fetch(`${API_BASE}/cuisines/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to update cuisine');
      return response.json();
    },
    delete: async (id, permanent = false) => {
      const response = await fetch(`${API_BASE}/cuisines/${id}?permanent=${permanent}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete cuisine');
      return response.json();
    }
  },

  // ================ MEAL SESSIONS ================
  mealSessions: {
    list: async (limit = 100, offset = 0) => {
      const response = await fetch(`${API_BASE}/meal-sessions?limit=${limit}&offset=${offset}`);
      if (!response.ok) throw new Error('Failed to fetch meal sessions');
      return response.json();
    },
    get: async (id) => {
      const response = await fetch(`${API_BASE}/meal-sessions/${id}`);
      if (!response.ok) throw new Error('Meal session not found');
      return response.json();
    },
    create: async (data) => {
      const response = await fetch(`${API_BASE}/meal-sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to create meal session');
      return response.json();
    },
    update: async (id, data) => {
      const response = await fetch(`${API_BASE}/meal-sessions/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to update meal session');
      return response.json();
    },
    delete: async (id, permanent = false) => {
      const response = await fetch(`${API_BASE}/meal-sessions/${id}?permanent=${permanent}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete meal session');
      return response.json();
    }
  },

  // ================ INGREDIENTS ================
  ingredients: {
    list: async (limit = 100, offset = 0, activeOnly = true) => {
      const response = await fetch(`${API_BASE}/ingredients?limit=${limit}&offset=${offset}&active_only=${activeOnly}`);
      if (!response.ok) throw new Error('Failed to fetch ingredients');
      return response.json();
    },
    get: async (id) => {
      const response = await fetch(`${API_BASE}/ingredients/${id}`);
      if (!response.ok) throw new Error('Ingredient not found');
      return response.json();
    },
    create: async (data) => {
      const response = await fetch(`${API_BASE}/ingredients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) {
        let errMsg = 'Failed to create ingredient';
        try {
          const errData = await response.json();
          if (errData && errData.detail) errMsg = errData.detail;
        } catch (_) {}
        throw new Error(errMsg);
      }
      return response.json();
    },
    update: async (id, data) => {
      const response = await fetch(`${API_BASE}/ingredients/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) {
        let errMsg = 'Failed to update ingredient';
        try {
          const errData = await response.json();
          if (errData && errData.detail) errMsg = errData.detail;
        } catch (_) {}
        throw new Error(errMsg);
      }
      return response.json();
    },
    delete: async (id, permanent = false) => {
      const response = await fetch(`${API_BASE}/ingredients/${id}?permanent=${permanent}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete ingredient');
      return response.json();
    }
  },

  // ================ FOODS ================
  foods: {
    list: async (cuisineId = null, limit = 100, offset = 0, activeOnly = true, search = '') => {
      let url = `${API_BASE}/foods?limit=${limit}&offset=${offset}&active_only=${activeOnly}`;
      if (cuisineId) url += `&cuisine_id=${cuisineId}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch foods');
      return response.json();
    },
    get: async (id) => {
      const response = await fetch(`${API_BASE}/foods/${id}`);
      if (!response.ok) throw new Error('Food not found');
      return response.json();
    },
    create: async (data) => {
      const response = await fetch(`${API_BASE}/foods`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to create food');
      return response.json();
    },
    update: async (id, data) => {
      const response = await fetch(`${API_BASE}/foods/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to update food');
      return response.json();
    },
    delete: async (id, permanent = false) => {
      const response = await fetch(`${API_BASE}/foods/${id}?permanent=${permanent}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete food');
      return response.json();
    }
  },

  // ================ MEALS ================
  meals: {
    list: async (cuisineId = null, limit = 100, offset = 0, activeOnly = true, search = '') => {
      let url = `${API_BASE}/meals?limit=${limit}&offset=${offset}&active_only=${activeOnly}`;
      if (cuisineId) url += `&cuisine_id=${cuisineId}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch meals');
      return response.json();
    },
    get: async (id) => {
      const response = await fetch(`${API_BASE}/meals/${id}`);
      if (!response.ok) throw new Error('Meal not found');
      return response.json();
    },
    create: async (data) => {
      const response = await fetch(`${API_BASE}/meals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to create meal');
      return response.json();
    },
    update: async (id, data) => {
      const response = await fetch(`${API_BASE}/meals/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error('Failed to update meal');
      return response.json();
    },
    delete: async (id, permanent = false) => {
      const response = await fetch(`${API_BASE}/meals/${id}?permanent=${permanent}`, {
        method: 'DELETE'
      });
      if (!response.ok) throw new Error('Failed to delete meal');
      return response.json();
    }
  },

  // ================ REFERENCE TABLES ================
  foodRoles: createGenericApi('food-roles'),
  primaryGoals: createGenericApi('primary-goals'),
  secondaryGoals: createGenericApi('secondary-goals')
};
