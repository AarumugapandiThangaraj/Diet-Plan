import React, { useState, useEffect } from 'react';
import Select from 'react-select';
import { adminApi } from '../adminApi';

export default function MealManager() {
  const [meals, setMeals] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [cuisineFilter, setCuisineFilter] = useState('');
  const [initialLoading, setInitialLoading] = useState(true);
  const [cuisines, setCuisines] = useState([]);
  const [foods, setFoods] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [primaryGoalsList, setPrimaryGoalsList] = useState([]);
  const [secondaryGoalsList, setSecondaryGoalsList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalMeals, setTotalMeals] = useState(0);
  const itemsPerPage = 50;

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  useEffect(() => {
    const handler = setTimeout(() => {
      setSearchQuery(searchInput);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchInput]);
  const [formData, setFormData] = useState({
    cuisine_id: '',
    client_meal_id: '',
    name_en: '',
    name_ar: '',
    description_en: '',
    description_ar: '',
    meal_session_id: '',
    primary_goal_ids: [],
    secondary_goal_ids: [],
    diet_types: {},
    is_active: true,
    meal_foods: []
  });

  useEffect(() => {
    loadReferenceData();
  }, []);

  useEffect(() => {
    fetchMeals();
  }, [currentPage, searchQuery, cuisineFilter]);

  const loadReferenceData = async () => {
    setLoading(true);
    setInitialLoading(true);
    setError('');
    try {
      const [cuisinesData, foodsData, sessionsData, primaryData, secondaryData] = await Promise.all([
        adminApi.cuisines.list(1000),
        adminApi.foods.list(null, 50000),
        adminApi.mealSessions.list(1000),
        adminApi.primaryGoals.list(1000),
        adminApi.secondaryGoals.list(1000)
      ]);
      setCuisines(cuisinesData.items);
      setFoods(foodsData.items);
      setSessions(sessionsData.items);
      setPrimaryGoalsList(primaryData.items);
      setSecondaryGoalsList(secondaryData.items);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  };

  const fetchMeals = async () => {
    setLoading(true);
    setError('');
    try {
      const offset = (currentPage - 1) * itemsPerPage;
      const response = await adminApi.meals.list(cuisineFilter || null, itemsPerPage, offset, false, searchQuery);
      setMeals(response.items);
      setTotalMeals(response.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked, options } = e.target;
    if (type === 'select-multiple') {
      const selectedValues = Array.from(options)
        .filter(option => option.selected)
        .map(option => parseInt(option.value));
      setFormData(prev => ({ ...prev, [name]: selectedValues }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value
      }));
    }
  };

  const handleAddFood = () => {
    setFormData(prev => ({
      ...prev,
      meal_foods: [...prev.meal_foods, { food_id: '', is_replaceable: false, sort_order: prev.meal_foods.length }]
    }));
  };

  const handleRemoveFood = (index) => {
    setFormData(prev => ({
      ...prev,
      meal_foods: prev.meal_foods.filter((_, i) => i !== index)
    }));
  };

  const handleFoodChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      meal_foods: prev.meal_foods.map((mf, i) => 
        i === index ? { ...mf, [field]: field === 'is_replaceable' ? value === 'true' : value } : mf
      )
    }));
  };

  const resetForm = () => {
    setFormData({
      cuisine_id: '',
      client_meal_id: '',
      name_en: '',
      name_ar: '',
      description_en: '',
      description_ar: '',
      meal_session_id: '',
      primary_goal_ids: [],
      secondary_goal_ids: [],
      diet_types: {},
      is_active: true,
      meal_foods: []
    });
    setEditingId(null);
  };

  const handleOpenModal = (meal = null) => {
    if (meal) {
      setFormData(meal);
      setEditingId(meal.id);
    } else {
      resetForm();
    }
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.cuisine_id) {
      setError('Cuisine is required');
      return;
    }

    if (!formData.meal_session_id) {
      setError('Meal session is required');
      return;
    }

    if (formData.meal_foods.length === 0) {
      setError('Add at least one food to the meal');
      return;
    }

    const submitData = {
      ...formData,
      cuisine_id: parseInt(formData.cuisine_id),
      meal_session_id: parseInt(formData.meal_session_id),
      meal_foods: formData.meal_foods.map((mf, idx) => ({
        food_id: parseInt(mf.food_id),
        is_replaceable: mf.is_replaceable,
        sort_order: idx
      }))
    };

    try {
      if (editingId) {
        await adminApi.meals.update(editingId, submitData);
        setSuccess('Meal updated successfully!');
      } else {
        await adminApi.meals.create(submitData);
        setSuccess('Meal created successfully!');
      }
      setShowModal(false);
      await fetchMeals();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, permanent = false) => {
    const warningMsg = permanent 
      ? "⚠️ WARNING: This will permanently delete this meal from the database! Are you absolutely sure?"
      : "Are you sure you want to deactivate (soft-delete) this meal?";
    if (!confirm(warningMsg)) return;
    setError('');
    try {
      await adminApi.meals.delete(id, permanent);
      setSuccess(permanent ? 'Meal permanently deleted successfully!' : 'Meal deactivated successfully!');
      await fetchMeals();
    } catch (err) {
      setError(err.message);
    }
  };

  const totalPages = Math.ceil(totalMeals / itemsPerPage);

  if (initialLoading) return <div className="loading"><div className="loading-spinner"></div></div>;

  return (
    <div className="form-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Manage Meals</h2>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          Add New Meal
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="🔍 Search meal by ID, code, name, cuisine, or session..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          style={{
            padding: '10px 15px',
            border: '2px solid #ecf0f1',
            borderRadius: '6px',
            width: '100%',
            maxWidth: '400px',
            fontSize: '1rem'
          }}
        />
        <select
          value={cuisineFilter}
          onChange={(e) => setCuisineFilter(e.target.value)}
          style={{
            padding: '10px 15px',
            border: '2px solid #ecf0f1',
            borderRadius: '6px',
            minWidth: '200px',
            fontSize: '1rem'
          }}
        >
          <option value="">All Cuisines</option>
          {cuisines.map(c => (
            <option key={c.id} value={c.id}>{c.name_en}</option>
          ))}
        </select>
        {loading && <span className="loading-spinner" style={{ width: '20px', height: '20px', marginLeft: '10px' }}></span>}
      </div>

      <div className="list-container">
        {meals.length === 0 ? (
          <div className="empty-state">
            <p>{searchQuery ? 'No meals match your search.' : 'No meals found. Create one to get started!'}</p>
          </div>
        ) : (
          <>
            <table className="list-table">
              <thead>
                <tr>
                  <th>S.No.</th>
                  <th>System ID</th>
                  <th>Client ID</th>
                  <th>Cuisine</th>
                  <th>English Name</th>
                  <th>Arabic Name</th>
                  <th>Session</th>
                  <th>Nutrition</th>
                  <th>Foods</th>
                  <th>Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {meals.map((meal, index) => (
                  <tr key={meal.id}>
                    <td>{(currentPage - 1) * itemsPerPage + index + 1}</td>
                    <td><strong>{meal.id}</strong></td>
                    <td><code>{meal.client_meal_id}</code></td>
                    <td>{cuisines.find(c => c.id === meal.cuisine_id)?.name_en || meal.cuisine_id}</td>
                    <td>{meal.name_en}</td>
                    <td>{meal.name_ar || '-'}</td>
                    <td>{sessions.find(s => s.id === meal.meal_session_id)?.name_en || meal.meal_session_id}</td>
                    <td>
                      <div style={{ fontSize: '0.85rem' }}>
                        <strong>{Math.round(meal.calories_kcal || 0)} kcal</strong>
                        <div style={{ color: '#7f8c8d', fontSize: '0.75rem' }}>
                          P: {Math.round(meal.protein_g || 0)}g | C: {Math.round(meal.carbs_g || 0)}g | F: {Math.round(meal.fat_g || 0)}g
                        </div>
                      </div>
                    </td>
                    <td>{meal.meal_foods?.length || 0}</td>
                    <td>{meal.is_active ? '✓' : '✗'}</td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn btn-secondary btn-small" onClick={() => handleOpenModal(meal)}>
                          Edit
                        </button>
                        {meal.is_active ? (
                          <button className="btn btn-warning btn-small" onClick={() => handleDelete(meal.id, false)}>
                            Deactivate
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.85rem', color: '#7f8c8d', fontStyle: 'italic', display: 'flex', alignItems: 'center', backgroundColor: '#f5f7fa', padding: '2px 8px', borderRadius: '4px' }}>Inactive</span>
                        )}
                        <button className="btn btn-danger btn-small" onClick={() => handleDelete(meal.id, true)}>
                          Delete Permanently
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {totalPages > 1 && (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '15px',
                marginTop: '25px',
                padding: '10px',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #ecf0f1'
              }}>
                <button
                  className="btn btn-secondary btn-small"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  style={{ margin: 0 }}
                  type="button"
                >
                  ◀ Previous
                </button>
                <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '0.95rem' }}>
                  Page {currentPage} of {totalPages} ({totalMeals} items)
                </span>
                <button
                  className="btn btn-secondary btn-small"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  style={{ margin: 0 }}
                  type="button"
                >
                  Next ▶
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => !editingId && setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxHeight: '90vh', overflowY: 'auto', maxWidth: '700px' }}>
            <div className="modal-header">
              <h2>{editingId ? 'Edit Meal' : 'Create New Meal'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Cuisine *</label>
                  <Select
                    options={cuisines.map(c => ({ value: c.id, label: c.name_en }))}
                    value={cuisines.filter(c => c.id === formData.cuisine_id).map(c => ({ value: c.id, label: c.name_en }))}
                    onChange={(option) => handleInputChange({ target: { name: 'cuisine_id', value: option ? option.value : '' }})}
                    isClearable
                    placeholder="-- Select Cuisine --"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Meal Session *</label>
                  <Select
                    options={sessions.map(s => ({ value: s.id, label: s.name_en }))}
                    value={sessions.filter(s => s.id === formData.meal_session_id).map(s => ({ value: s.id, label: s.name_en }))}
                    onChange={(option) => handleInputChange({ target: { name: 'meal_session_id', value: option ? option.value : '' }})}
                    isClearable
                    placeholder="-- Select Session --"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Client Meal ID *</label>
                  <input
                    type="text"
                    name="client_meal_id"
                    value={formData.client_meal_id}
                    onChange={handleInputChange}
                    required
                    disabled={editingId}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>English Name *</label>
                  <input
                    type="text"
                    name="name_en"
                    value={formData.name_en}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Arabic Name</label>
                  <input
                    type="text"
                    name="name_ar"
                    value={formData.name_ar}
                    onChange={handleInputChange}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Description (English)</label>
                <textarea
                  name="description_en"
                  value={formData.description_en}
                  onChange={handleInputChange}
                />
              </div>

              <div className="form-group">
                <label>Description (Arabic)</label>
                <textarea
                  name="description_ar"
                  value={formData.description_ar}
                  onChange={handleInputChange}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Primary Goals</label>
                  <Select
                    isMulti
                    options={primaryGoalsList.map(g => ({ value: g.id, label: g.name_en }))}
                    value={(formData.primary_goal_ids || []).map(id => {
                      const g = primaryGoalsList.find(x => x.id === id);
                      return g ? { value: g.id, label: g.name_en } : { value: id, label: id };
                    })}
                    onChange={(selected) => handleInputChange({
                      target: { name: 'primary_goal_ids', value: selected ? selected.map(s => s.value) : [] }
                    })}
                    placeholder="Select Primary Goals..."
                  />
                </div>
                <div className="form-group">
                  <label>Secondary Goals</label>
                  <Select
                    isMulti
                    options={secondaryGoalsList.map(g => ({ value: g.id, label: g.name_en }))}
                    value={(formData.secondary_goal_ids || []).map(id => {
                      const g = secondaryGoalsList.find(x => x.id === id);
                      return g ? { value: g.id, label: g.name_en } : { value: id, label: id };
                    })}
                    onChange={(selected) => handleInputChange({
                      target: { name: 'secondary_goal_ids', value: selected ? selected.map(s => s.value) : [] }
                    })}
                    placeholder="Select Secondary Goals..."
                  />
                </div>
              </div>

              <h3 style={{ marginTop: '20px', marginBottom: '15px' }}>Foods *</h3>
              <div className="ingredient-list">
                {formData.meal_foods.length > 0 && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 150px 40px',
                    gap: '10px',
                    marginBottom: '10px',
                    padding: '0 10px 5px 10px',
                    fontWeight: '600',
                    fontSize: '0.85rem',
                    color: '#7f8c8d',
                    borderBottom: '2px solid #ecf0f1'
                  }}>
                    <div>Food Name</div>
                    <div>Is Replaceable?</div>
                    <div></div>
                  </div>
                )}
                {formData.meal_foods.map((mf, index) => (
                  <div key={index} className="ingredient-item" style={{ display: 'grid', gridTemplateColumns: '1fr 150px 40px', gap: '10px', alignItems: 'center' }}>
                    <div style={{ width: '100%' }}>
                      <Select
                        options={foods.map(f => ({ value: f.id, label: `${f.name_en} (${f.quantity} ${f.unit})` }))}
                        value={foods.filter(f => f.id === parseInt(mf.food_id)).map(f => ({ value: f.id, label: `${f.name_en} (${f.quantity} ${f.unit})` }))}
                        onChange={(option) => handleFoodChange(index, 'food_id', option ? option.value : '')}
                        isClearable
                        placeholder="Search Food..."
                        required
                        styles={{ menuPortal: base => ({ ...base, zIndex: 9999 }) }}
                        menuPortalTarget={document.body}
                      />
                    </div>
                    <select
                      value={mf.is_replaceable ? 'true' : 'false'}
                      onChange={(e) => handleFoodChange(index, 'is_replaceable', e.target.value)}
                      style={{ width: '100%', boxSizing: 'border-box' }}
                    >
                      <option value="false">Not Replaceable</option>
                      <option value="true">Replaceable</option>
                    </select>
                    <button
                      type="button"
                      className="btn btn-danger btn-small"
                      onClick={() => handleRemoveFood(index)}
                      style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <button type="button" className="btn btn-secondary btn-small" onClick={handleAddFood} style={{ marginTop: '10px' }}>
                + Add Food
              </button>
 
              <div className="form-group" style={{ marginTop: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    name="is_active"
                    checked={formData.is_active}
                    onChange={handleInputChange}
                    style={{ width: 'auto', margin: 0 }}
                  />
                  Active
                </label>
              </div>

              <div className="button-group">
                <button type="submit" className="btn btn-success">
                  {editingId ? 'Update Meal' : 'Create Meal'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
