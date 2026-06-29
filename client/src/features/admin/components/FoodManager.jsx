import React, { useState, useEffect } from 'react';
import { adminApi } from '../adminApi';

export default function FoodManager() {
  const [foods, setFoods] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [initialLoading, setInitialLoading] = useState(true);
  const [cuisines, setCuisines] = useState([]);
  const [ingredients, setIngredients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    cuisine_id: '',
    client_food_id: '',
    name_en: '',
    name_ar: '',
    description_en: '',
    description_ar: '',
    preparation_en: '',
    preparation_ar: '',
    notes: '',
    food_role: 'base',
    prep_time_minutes: null,
    quantity: 1,
    min_quantity: null,
    max_quantity: null,
    unit: 'g',
    diet_types: {},
    supports: {},
    image_url: null,
    is_active: true,
    food_ingredients: []
  });
  const [rowInputValues, setRowInputValues] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [totalFoods, setTotalFoods] = useState(0);
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

  const handleRowInputChange = (index, value) => {
    setRowInputValues(prev => ({
      ...prev,
      [index]: value
    }));
    const matchedIng = ingredients.find(ing => ing.name_en.toLowerCase() === value.toLowerCase().trim());
    if (matchedIng) {
      handleIngredientChange(index, 'ingredient_id', matchedIng.id.toString());
    } else {
      handleIngredientChange(index, 'ingredient_id', '');
    }
  };

  useEffect(() => {
    loadReferenceData();
  }, []);

  useEffect(() => {
    fetchFoods();
  }, [currentPage, searchQuery]);

  const loadReferenceData = async () => {
    setLoading(true);
    setInitialLoading(true);
    setError('');
    try {
      const [cuisinesData, ingredientsData] = await Promise.all([
        adminApi.cuisines.list(1000),
        adminApi.ingredients.list(50000, 0, false)
      ]);
      setCuisines(cuisinesData.items);
      setIngredients(ingredientsData.items);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  };

  const fetchFoods = async () => {
    setLoading(true);
    setError('');
    try {
      const offset = (currentPage - 1) * itemsPerPage;
      const response = await adminApi.foods.list(null, itemsPerPage, offset, false, searchQuery);
      setFoods(response.items);
      setTotalFoods(response.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleAddIngredient = () => {
    setFormData(prev => ({
      ...prev,
      food_ingredients: [...prev.food_ingredients, { ingredient_id: '', quantity: 1, sort_order: prev.food_ingredients.length }]
    }));
  };

  const handleRemoveIngredient = (index) => {
    setFormData(prev => ({
      ...prev,
      food_ingredients: prev.food_ingredients.filter((_, i) => i !== index)
    }));
    setRowInputValues(prev => {
      const newValues = {};
      Object.keys(prev).forEach(k => {
        const currentIdx = parseInt(k);
        if (currentIdx < index) {
          newValues[currentIdx] = prev[k];
        } else if (currentIdx > index) {
          newValues[currentIdx - 1] = prev[k];
        }
      });
      return newValues;
    });
  };

  const handleIngredientChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      food_ingredients: prev.food_ingredients.map((fi, i) => i === index ? { ...fi, [field]: value } : fi)
    }));
  };

  const resetForm = () => {
    setFormData({
      cuisine_id: '',
      client_food_id: '',
      name_en: '',
      name_ar: '',
      description_en: '',
      description_ar: '',
      preparation_en: '',
      preparation_ar: '',
      notes: '',
      food_role: 'base',
      prep_time_minutes: null,
      quantity: 1,
      min_quantity: null,
      max_quantity: null,
      unit: 'g',
      diet_types: {},
      supports: {},
      image_url: null,
      is_active: true,
      food_ingredients: []
    });
    setEditingId(null);
    setRowInputValues({});
  };

  const handleOpenModal = (food = null) => {
    if (food) {
      setFormData(food);
      setEditingId(food.id);
      
      const initialInputValues = {};
      if (food.food_ingredients) {
        food.food_ingredients.forEach((fi, index) => {
          const ing = ingredients.find(i => i.id === parseInt(fi.ingredient_id));
          if (ing) {
            initialInputValues[index] = ing.name_en;
          }
        });
      }
      setRowInputValues(initialInputValues);
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

    if (formData.food_ingredients.length === 0) {
      setError('Add at least one ingredient to the food');
      return;
    }

    for (let i = 0; i < formData.food_ingredients.length; i++) {
      const fi = formData.food_ingredients[i];
      if (!fi.ingredient_id) {
        setError(`Row ${i + 1}: Please select a valid ingredient from the recommendations list.`);
        return;
      }
    }

    const submitData = {
      ...formData,
      cuisine_id: parseInt(formData.cuisine_id),
      food_ingredients: formData.food_ingredients.map((fi, idx) => ({
        ingredient_id: parseInt(fi.ingredient_id),
        quantity: parseFloat(fi.quantity),
        sort_order: idx
      }))
    };

    try {
      if (editingId) {
        await adminApi.foods.update(editingId, submitData);
        setSuccess('Food updated successfully!');
      } else {
        await adminApi.foods.create(submitData);
        setSuccess('Food created successfully!');
      }
      setShowModal(false);
      await fetchFoods();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, permanent = false) => {
    const warningMsg = permanent 
      ? "⚠️ WARNING: This will permanently delete this food from the database! Any meals using it may break. Are you absolutely sure?"
      : "Are you sure you want to deactivate (soft-delete) this food?";
    if (!confirm(warningMsg)) return;
    setError('');
    try {
      await adminApi.foods.delete(id, permanent);
      setSuccess(permanent ? 'Food permanently deleted successfully!' : 'Food deactivated successfully!');
      await fetchFoods();
    } catch (err) {
      setError(err.message);
    }
  };

  const totalPages = Math.ceil(totalFoods / itemsPerPage);

  if (initialLoading) return <div className="loading"><div className="loading-spinner"></div></div>;

  return (
    <div className="form-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Manage Foods</h2>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          Add New Food
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: '20px', maxWidth: '400px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <input
          type="text"
          placeholder="🔍 Search food by ID, code, name, cuisine, or role..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          style={{
            padding: '10px 15px',
            border: '2px solid #ecf0f1',
            borderRadius: '6px',
            width: '100%',
            fontSize: '0.95rem'
          }}
        />
        {loading && <span style={{ fontSize: '0.85rem', color: '#7f8c8d' }}>Loading...</span>}
      </div>

      <div className="list-container">
        {foods.length === 0 ? (
          <div className="empty-state">
            <p>{searchQuery ? 'No foods match your search.' : 'No foods found. Create one to get started!'}</p>
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
                  <th>Role</th>
                  <th>Quantity</th>
                  <th>Ingredients</th>
                  <th>Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {foods.map((food, index) => (
                  <tr key={food.id}>
                    <td>{(currentPage - 1) * itemsPerPage + index + 1}</td>
                    <td><strong>{food.id}</strong></td>
                    <td><code>{food.client_food_id}</code></td>
                    <td>{cuisines.find(c => c.id === food.cuisine_id)?.name_en || food.cuisine_id}</td>
                    <td>{food.name_en}</td>
                    <td>{food.name_ar || '-'}</td>
                    <td><span className="food-role-badge">{food.food_role || '-'}</span></td>
                    <td>{food.quantity} {food.unit}</td>
                    <td>{food.food_ingredients?.length || 0}</td>
                    <td>{food.is_active ? '✓' : '✗'}</td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn btn-secondary btn-small" onClick={() => handleOpenModal(food)}>
                          Edit
                        </button>
                        {food.is_active ? (
                          <button className="btn btn-warning btn-small" onClick={() => handleDelete(food.id, false)}>
                            Deactivate
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.85rem', color: '#7f8c8d', fontStyle: 'italic', display: 'flex', alignItems: 'center', backgroundColor: '#f5f7fa', padding: '2px 8px', borderRadius: '4px' }}>Inactive</span>
                        )}
                        <button className="btn btn-danger btn-small" onClick={() => handleDelete(food.id, true)}>
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
                  Page {currentPage} of {totalPages} ({totalFoods} items)
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
              <h2>{editingId ? 'Edit Food' : 'Create New Food'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Cuisine *</label>
                <select
                  name="cuisine_id"
                  value={formData.cuisine_id}
                  onChange={handleInputChange}
                  required
                >
                  <option value="">-- Select Cuisine --</option>
                  {cuisines.map(c => (
                    <option key={c.id} value={c.id}>{c.name_en}</option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Client Food ID *</label>
                  <input
                    type="text"
                    name="client_food_id"
                    value={formData.client_food_id}
                    onChange={handleInputChange}
                    required
                    disabled={editingId}
                  />
                </div>
                <div className="form-group">
                  <label>Role</label>
                  <select name="food_role" value={formData.food_role} onChange={handleInputChange}>
                    <option value="base">Base</option>
                    <option value="side">Side</option>
                    <option value="snack">Snack</option>
                    <option value="dessert">Dessert</option>
                    <option value="beverage">Beverage</option>
                    <option value="condiment">Condiment</option>
                    <option value="other">Other</option>
                  </select>
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

              <div className="form-group">
                <label>Preparation (English)</label>
                <textarea
                  name="preparation_en"
                  value={formData.preparation_en}
                  onChange={handleInputChange}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Quantity</label>
                  <input
                    type="number"
                    name="quantity"
                    value={formData.quantity}
                    onChange={handleInputChange}
                    step="0.1"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Unit *</label>
                  <input
                    type="text"
                    name="unit"
                    value={formData.unit}
                    onChange={handleInputChange}
                    list="food-units-datalist"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Min Quantity</label>
                  <input
                    type="number"
                    name="min_quantity"
                    value={formData.min_quantity || ''}
                    onChange={handleInputChange}
                    step="0.1"
                  />
                </div>
                <div className="form-group">
                  <label>Max Quantity</label>
                  <input
                    type="number"
                    name="max_quantity"
                    value={formData.max_quantity || ''}
                    onChange={handleInputChange}
                    step="0.1"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Prep Time (minutes)</label>
                <input
                  type="number"
                  name="prep_time_minutes"
                  value={formData.prep_time_minutes || ''}
                  onChange={handleInputChange}
                  min="0"
                />
              </div>

              <h3 style={{ marginTop: '20px', marginBottom: '15px' }}>Ingredients *</h3>
              <div className="ingredient-list">
                {formData.food_ingredients.length > 0 && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1.5fr 100px 80px 40px',
                    gap: '10px',
                    marginBottom: '10px',
                    padding: '0 10px 5px 10px',
                    fontWeight: '600',
                    fontSize: '0.85rem',
                    color: '#7f8c8d',
                    borderBottom: '2px solid #ecf0f1'
                  }}>
                    <div>Search & Select Ingredient</div>
                    <div>Quantity</div>
                    <div>Unit</div>
                    <div></div>
                  </div>
                )}
                {formData.food_ingredients.map((fi, index) => {
                  const selectedIng = ingredients.find(ing => ing.id === parseInt(fi.ingredient_id));
                  return (
                    <div key={index} className="ingredient-item" style={{ display: 'grid', gridTemplateColumns: '1.5fr 100px 80px 40px', gap: '10px', alignItems: 'center' }}>
                      <input
                        type="text"
                        list="all-ingredients-datalist"
                        placeholder="Search or type ingredient..."
                        value={rowInputValues[index] || ''}
                        onChange={(e) => handleRowInputChange(index, e.target.value)}
                        style={{ padding: '8px', fontSize: '0.85rem', width: '100%', boxSizing: 'border-box' }}
                        required
                      />
                      <input
                        type="number"
                        value={fi.quantity}
                        onChange={(e) => handleIngredientChange(index, 'quantity', e.target.value)}
                        step="0.0001"
                        min="0"
                        placeholder="Qty"
                        style={{ padding: '8px', fontSize: '0.85rem', width: '100%', boxSizing: 'border-box' }}
                        required
                      />
                      <input
                        type="text"
                        list="food-units-datalist"
                        placeholder="Unit"
                        value={fi.unit || selectedIng?.default_unit || ''}
                        onChange={(e) => handleIngredientChange(index, 'unit', e.target.value)}
                        style={{
                          padding: '8px',
                          fontSize: '0.85rem',
                          border: '1px solid #ddd',
                          textAlign: 'center',
                          borderRadius: '4px',
                          width: '100%',
                          boxSizing: 'border-box'
                        }}
                      />
                      <button
                        type="button"
                        className="btn btn-danger btn-small"
                        onClick={() => handleRemoveIngredient(index)}
                        style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}
              </div>
              <button type="button" className="btn btn-secondary btn-small" onClick={handleAddIngredient} style={{ marginTop: '10px' }}>
                + Add Ingredient
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
                  {editingId ? 'Update Food' : 'Create Food'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Global Datalists for Modal Inputs */}
      <datalist id="all-ingredients-datalist">
        {ingredients.map(ing => (
          <option key={ing.id} value={ing.name_en} />
        ))}
      </datalist>

      <datalist id="food-units-datalist">
        {Array.from(new Set([
          'g', 'ml', 'pcs', 'cup', 'tbsp', 'tsp', 'portion', 'slice',
          ...ingredients.map(ing => ing.default_unit).filter(Boolean)
        ])).map(unit => (
          <option key={unit} value={unit} />
        ))}
      </datalist>
    </div>
  );
}
