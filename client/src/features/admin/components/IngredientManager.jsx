import React, { useState, useEffect } from 'react';
import CreatableSelect from 'react-select/creatable';
import { adminApi } from '../adminApi';

export default function IngredientManager() {
  const [ingredients, setIngredients] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);
  const [formData, setFormData] = useState({
    name_en: '',
    name_ar: '',
    default_unit: '',
    calories_kcal: '',
    protein_g: '',
    carbs_g: '',
    fat_g: '',
    fiber_g: '',
    micronutrients: {},
    benefits: {},
    caution: '',
    notes: '',
    is_active: true
  });
  const [modalTab, setModalTab] = useState('basic');
  const [showCustomUnitInput, setShowCustomUnitInput] = useState(false);
  const [micronutrientsList, setMicronutrientsList] = useState([]);
  const [benefitsList, setBenefitsList] = useState([]);
  const [nameSuggestions, setNameSuggestions] = useState([]);
  const [highlightedId, setHighlightedId] = useState(null);

  // Predefined units
  const predefinedUnits = ['g', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'piece', 'slice', 'scoop'];
  // All unique units from ingredients currently in database merged with predefined
  const dbUnits = Array.from(new Set(ingredients.map(ing => ing.default_unit).filter(Boolean)));
  const allUnits = Array.from(new Set([...predefinedUnits, ...dbUnits]));

  // Get human readable labels for predefined units
  const getUnitLabel = (unit) => {
    const labels = {
      g: 'Grams',
      ml: 'Milliliters',
      l: 'Liters',
      cup: 'Cups',
      tbsp: 'Tablespoons',
      tsp: 'Teaspoons',
      piece: 'Pieces',
      slice: 'Slices',
      scoop: 'Scoops'
    };
    return labels[unit] || '';
  };

  // Compile all unique micronutrient names from the database for suggestions
  const existingMicros = Array.from(
    new Set(
      ingredients
        .map(ing => ing.micronutrients ? Object.keys(ing.micronutrients) : [])
        .flat()
    )
  ).sort();

  useEffect(() => {
    loadIngredients();
  }, []);

  useEffect(() => {
    if (highlightedId) {
      const timer = setTimeout(() => setHighlightedId(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [highlightedId]);

  const loadIngredients = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await adminApi.ingredients.list(50000, 0, false);
      setIngredients(data.items);
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

  const handleNameChange = (e) => {
    const value = e.target.value;
    setFormData(prev => ({ ...prev, name_en: value }));

    const query = value.trim().toLowerCase();
    if (query) {
      const matches = ingredients.filter(ing => 
        ing.id !== editingId && 
        ing.name_en.toLowerCase().includes(query)
      );
      setNameSuggestions(matches);
    } else {
      setNameSuggestions([]);
    }
  };

  const handleNameBlur = () => {
    setTimeout(() => setNameSuggestions([]), 200);
  };

  const resetForm = () => {
    setFormData({
      name_en: '',
      name_ar: '',
      default_unit: '',
      calories_kcal: '',
      protein_g: '',
      carbs_g: '',
      fat_g: '',
      fiber_g: '',
      micronutrients: {},
      benefits: {},
      caution: '',
      notes: '',
      is_active: true
    });
    setEditingId(null);
    setShowCustomUnitInput(false);
    setMicronutrientsList([]);
    setBenefitsList([]);
    setNameSuggestions([]);
    setModalTab('basic');
  };

  const handleOpenModal = (ingredient = null) => {
    setError('');
    setSuccess('');
    if (ingredient) {
      setFormData({
        ...ingredient,
        calories_kcal: ingredient.calories_kcal ?? '',
        protein_g: ingredient.protein_g ?? '',
        carbs_g: ingredient.carbs_g ?? '',
        fat_g: ingredient.fat_g ?? '',
        fiber_g: ingredient.fiber_g ?? '',
        micronutrients: ingredient.micronutrients || {},
        benefits: ingredient.benefits || {}
      });
      setEditingId(ingredient.id);
      
      const isKnown = allUnits.includes(ingredient.default_unit);
      setShowCustomUnitInput(!isKnown);
      
      const parsedMicros = Object.entries(ingredient.micronutrients || {}).map(([name, value]) => ({ name, value }));
      setMicronutrientsList(parsedMicros);
      
      const parsedBenefits = Object.entries(ingredient.benefits || {}).map(([name, value]) => ({ name, value }));
      setBenefitsList(parsedBenefits);
    } else {
      resetForm();
    }
    setModalTab('basic');
    setShowModal(true);
  };

  const handleMicroAdd = () => {
    setMicronutrientsList(prev => [...prev, { name: '', value: '' }]);
  };

  const handleMicroChange = (index, field, val) => {
    setMicronutrientsList(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: val };
      return updated;
    });
  };

  const handleMicroDelete = (index) => {
    setMicronutrientsList(prev => prev.filter((_, i) => i !== index));
  };

  const handleBenefitAdd = () => {
    setBenefitsList(prev => [...prev, { name: '', value: '' }]);
  };

  const handleBenefitChange = (index, field, val) => {
    setBenefitsList(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: val };
      return updated;
    });
  };

  const handleBenefitDelete = (index) => {
    setBenefitsList(prev => prev.filter((_, i) => i !== index));
  };

  const handleUnitSelectChange = (e) => {
    const val = e.target.value;
    if (val === 'custom') {
      setShowCustomUnitInput(true);
      setFormData(prev => ({ ...prev, default_unit: '' }));
    } else {
      setShowCustomUnitInput(false);
      setFormData(prev => ({ ...prev, default_unit: val }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Pre-submission duplicate check
    const isDuplicate = ingredients.some(ing => 
      ing.id !== editingId && 
      (ing.name_en || '').trim().toLowerCase() === (formData.name_en || '').trim().toLowerCase()
    );
    if (isDuplicate) {
      setError(`An ingredient named "${formData.name_en}" already exists in the database. Duplicates are not allowed.`);
      return;
    }

    try {
      const microObj = {};
      micronutrientsList.forEach(item => {
        if (item.name.trim()) {
          microObj[item.name.trim()] = item.value;
        }
      });

      const benefitObj = {};
      benefitsList.forEach(item => {
        if (item.name.trim()) {
          benefitObj[item.name.trim()] = item.value;
        }
      });

      const submissionData = {
        ...formData,
        calories_kcal: parseFloat(formData.calories_kcal) || 0.0,
        protein_g: parseFloat(formData.protein_g) || 0.0,
        carbs_g: parseFloat(formData.carbs_g) || 0.0,
        fat_g: parseFloat(formData.fat_g) || 0.0,
        fiber_g: parseFloat(formData.fiber_g) || 0.0,
        micronutrients: microObj,
        benefits: benefitObj
      };

      if (editingId) {
        await adminApi.ingredients.update(editingId, submissionData);
        setSuccess('Ingredient updated successfully!');
        setHighlightedId(editingId);
      } else {
        const newIng = await adminApi.ingredients.create(submissionData);
        setSuccess('Ingredient created successfully!');
        if (newIng && newIng.id) {
          setHighlightedId(newIng.id);
        }
      }
      setShowModal(false);
      await loadIngredients();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, permanent = false) => {
    const warningMsg = permanent 
      ? "⚠️ WARNING: This will permanently delete this ingredient from the database! Any foods or meals using it may break. Are you absolutely sure?"
      : "Are you sure you want to deactivate (soft-delete) this ingredient?";
    if (!confirm(warningMsg)) return;
    setError('');
    try {
      await adminApi.ingredients.delete(id, permanent);
      setSuccess(permanent ? 'Ingredient permanently deleted successfully!' : 'Ingredient deactivated successfully!');
      await loadIngredients();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredIngredients = ingredients.filter(ing => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      ing.id.toString().includes(query) ||
      (ing.name_en || '').toLowerCase().includes(query) ||
      (ing.name_ar || '').toLowerCase().includes(query) ||
      (ing.default_unit || '').toLowerCase().includes(query)
    );
  });

  const totalPages = Math.ceil(filteredIngredients.length / itemsPerPage);
  const paginatedIngredients = filteredIngredients.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (loading) return <div className="loading"><div className="loading-spinner"></div></div>;

  return (
    <div className="form-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Manage Ingredients</h2>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          Add New Ingredient
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: '20px', maxWidth: '400px' }}>
        <input
          type="text"
          placeholder="🔍 Search ingredient by ID, name, or unit..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            padding: '10px 15px',
            border: '2px solid #ecf0f1',
            borderRadius: '6px',
            width: '100%',
            fontSize: '0.95rem'
          }}
        />
      </div>

      <div className="list-container">
        {filteredIngredients.length === 0 ? (
          <div className="empty-state">
            <p>{searchQuery ? 'No ingredients match your search.' : 'No ingredients found. Create one to get started!'}</p>
          </div>
        ) : (
          <>
            <table className="list-table">
              <thead>
                <tr>
                  <th>S.No.</th>
                  <th>System ID</th>
                  <th>English Name</th>
                  <th>Arabic Name</th>
                  <th>Unit</th>
                  <th>Calories (kcal)</th>
                  <th>Protein (g)</th>
                  <th>Carbs (g)</th>
                  <th>Fat (g)</th>
                  <th>Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedIngredients.map((ing, index) => (
                  <tr 
                    key={ing.id}
                    style={highlightedId === ing.id ? {
                      backgroundColor: '#d4edda',
                      fontWeight: 'bold',
                      borderLeft: '4px solid #28a745',
                      transition: 'all 0.5s ease-in-out'
                    } : {
                      transition: 'all 0.5s ease-in-out'
                    }}
                  >
                    <td>{(currentPage - 1) * itemsPerPage + index + 1}</td>
                    <td><strong>{ing.id}</strong></td>
                    <td>{ing.name_en}</td>
                    <td>{ing.name_ar || '-'}</td>
                    <td><code>{ing.default_unit}</code></td>
                    <td>{ing.calories_kcal}</td>
                    <td>{ing.protein_g}</td>
                    <td>{ing.carbs_g}</td>
                    <td>{ing.fat_g}</td>
                    <td>{ing.is_active ? '✓' : '✗'}</td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn btn-secondary btn-small" onClick={() => handleOpenModal(ing)}>
                          Edit
                        </button>
                        {ing.is_active ? (
                          <button className="btn btn-warning btn-small" onClick={() => handleDelete(ing.id, false)}>
                            Deactivate
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.85rem', color: '#7f8c8d', fontStyle: 'italic', display: 'flex', alignItems: 'center', backgroundColor: '#f5f7fa', padding: '2px 8px', borderRadius: '4px' }}>Inactive</span>
                        )}
                        <button className="btn btn-danger btn-small" onClick={() => handleDelete(ing.id, true)}>
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
                  Page {currentPage} of {totalPages} ({filteredIngredients.length} items)
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
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '700px', width: '95%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h2>{editingId ? 'Edit Ingredient' : 'Create New Ingredient'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            
            {error && <div className="alert alert-error" style={{ marginBottom: '20px' }}>{error}</div>}
            
            {/* Modal Navigation Tabs */}
            <div className="modal-tabs" style={{ display: 'flex', borderBottom: '2px solid #ecf0f1', marginBottom: '20px', gap: '15px', overflowX: 'auto' }}>
              <button
                type="button"
                className={`modal-tab-btn ${modalTab === 'basic' ? 'active' : ''}`}
                onClick={() => setModalTab('basic')}
                style={{
                  padding: '10px 15px',
                  border: 'none',
                  background: 'none',
                  borderBottom: modalTab === 'basic' ? '3px solid #667eea' : '3px solid transparent',
                  fontWeight: modalTab === 'basic' ? 'bold' : 'normal',
                  color: modalTab === 'basic' ? '#667eea' : '#7f8c8d',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap'
                }}
              >
                Basic Info & Macros
              </button>
              <button
                type="button"
                className={`modal-tab-btn ${modalTab === 'micro' ? 'active' : ''}`}
                onClick={() => setModalTab('micro')}
                style={{
                  padding: '10px 15px',
                  border: 'none',
                  background: 'none',
                  borderBottom: modalTab === 'micro' ? '3px solid #667eea' : '3px solid transparent',
                  fontWeight: modalTab === 'micro' ? 'bold' : 'normal',
                  color: modalTab === 'micro' ? '#667eea' : '#7f8c8d',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap'
                }}
              >
                Micronutrients
              </button>
              <button
                type="button"
                className={`modal-tab-btn ${modalTab === 'benefits' ? 'active' : ''}`}
                onClick={() => setModalTab('benefits')}
                style={{
                  padding: '10px 15px',
                  border: 'none',
                  background: 'none',
                  borderBottom: modalTab === 'benefits' ? '3px solid #667eea' : '3px solid transparent',
                  fontWeight: modalTab === 'benefits' ? 'bold' : 'normal',
                  color: modalTab === 'benefits' ? '#667eea' : '#7f8c8d',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap'
                }}
              >
                Benefits
              </button>
              <button
                type="button"
                className={`modal-tab-btn ${modalTab === 'additional' ? 'active' : ''}`}
                onClick={() => setModalTab('additional')}
                style={{
                  padding: '10px 15px',
                  border: 'none',
                  background: 'none',
                  borderBottom: modalTab === 'additional' ? '3px solid #667eea' : '3px solid transparent',
                  fontWeight: modalTab === 'additional' ? 'bold' : 'normal',
                  color: modalTab === 'additional' ? '#667eea' : '#7f8c8d',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap'
                }}
              >
                Caution & Notes
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {/* Tab 1: Basic Info & Macros */}
              {modalTab === 'basic' && (
                <div>
                  <div className="form-row">
                    <div className="form-group" style={{ position: 'relative' }}>
                      <label>English Name *</label>
                      <input
                        type="text"
                        name="name_en"
                        value={formData.name_en}
                        onChange={handleNameChange}
                        onBlur={handleNameBlur}
                        autoComplete="off"
                        required
                      />

                      {/* Name Suggestions Dropdown */}
                      {nameSuggestions.length > 0 && (
                        <div style={{
                          position: 'absolute',
                          backgroundColor: '#ffffff',
                          border: '1px solid #bdc3c7',
                          borderRadius: '6px',
                          boxShadow: '0 4px 15px rgba(0,0,0,0.15)',
                          zIndex: 1000,
                          width: '100%',
                          maxHeight: '180px',
                          overflowY: 'auto',
                          marginTop: '4px'
                        }}>
                          <div style={{ padding: '8px 12px', fontSize: '0.8rem', color: '#7f8c8d', borderBottom: '1px solid #ecf0f1', fontWeight: 'bold' }}>
                            Existing Ingredients matching typed letters:
                          </div>
                          {nameSuggestions.map(suggestion => (
                            <div
                              key={suggestion.id}
                              onClick={() => {
                                setFormData({
                                  ...suggestion,
                                  micronutrients: suggestion.micronutrients || {},
                                  benefits: suggestion.benefits || {}
                                });
                                setEditingId(suggestion.id);
                                setMicronutrientsList(Object.entries(suggestion.micronutrients || {}).map(([name, value]) => ({ name, value })));
                                setBenefitsList(Object.entries(suggestion.benefits || {}).map(([name, value]) => ({ name, value })));
                                const isKnown = allUnits.includes(suggestion.default_unit);
                                setShowCustomUnitInput(!isKnown);
                                setNameSuggestions([]);
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = '#f8f9fa';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = '#ffffff';
                              }}
                              style={{
                                padding: '10px 12px',
                                cursor: 'pointer',
                                borderBottom: '1px solid #f0f0f0',
                                fontSize: '0.9rem',
                                color: '#2c3e50',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                transition: 'background-color 0.2s'
                              }}
                            >
                              <span>🍏 {suggestion.name_en}</span>
                              <span style={{ fontSize: '0.75rem', color: '#7f8c8d', backgroundColor: '#ecf0f1', padding: '2px 6px', borderRadius: '4px' }}>
                                ID: {suggestion.id} ({suggestion.default_unit})
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Duplicate Warning */}
                      {(() => {
                        const exactDuplicate = formData.name_en && ingredients.find(ing =>
                          ing.id !== editingId &&
                          (ing.name_en || '').trim().toLowerCase() === (formData.name_en || '').trim().toLowerCase()
                        );
                        return exactDuplicate ? (
                          <div style={{ color: '#e74c3c', fontSize: '0.85rem', marginTop: '6px', fontWeight: '600' }}>
                            ⚠️ Warning: An ingredient named "{exactDuplicate.name_en}" (ID: {exactDuplicate.id}) already exists. Duplicates cannot be saved.
                          </div>
                        ) : null;
                      })()}
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
                    <label>Default Unit *</label>
                    <select
                      value={showCustomUnitInput ? 'custom' : formData.default_unit}
                      onChange={handleUnitSelectChange}
                      required
                    >
                      <option value="">-- Select Unit --</option>
                      {allUnits.map(unit => (
                        <option key={unit} value={unit}>
                          {unit} {predefinedUnits.includes(unit) ? `(${getUnitLabel(unit)})` : ' (from DB)'}
                        </option>
                      ))}
                      <option value="custom">Other (Add new unit...)</option>
                    </select>
                    
                    {showCustomUnitInput && (
                      <div style={{ marginTop: '10px' }}>
                        <input
                          type="text"
                          name="default_unit"
                          placeholder="Enter new custom unit (e.g. pinch)"
                          value={formData.default_unit}
                          onChange={handleInputChange}
                          required
                        />
                      </div>
                    )}
                  </div>

                  <h3 style={{ marginTop: '20px', marginBottom: '15px' }}>Nutritional Information (per 100g)</h3>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Calories (kcal)</label>
                      <input
                        type="number"
                        name="calories_kcal"
                        value={formData.calories_kcal}
                        onChange={handleInputChange}
                        step="0.0001"
                        min="0"
                      />
                    </div>
                    <div className="form-group">
                      <label>Protein (g)</label>
                      <input
                        type="number"
                        name="protein_g"
                        value={formData.protein_g}
                        onChange={handleInputChange}
                        step="0.0001"
                        min="0"
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Carbs (g)</label>
                      <input
                        type="number"
                        name="carbs_g"
                        value={formData.carbs_g}
                        onChange={handleInputChange}
                        step="0.0001"
                        min="0"
                      />
                    </div>
                    <div className="form-group">
                      <label>Fat (g)</label>
                      <input
                        type="number"
                        name="fat_g"
                        value={formData.fat_g}
                        onChange={handleInputChange}
                        step="0.0001"
                        min="0"
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Fiber (g)</label>
                    <input
                      type="number"
                      name="fiber_g"
                      value={formData.fiber_g}
                      onChange={handleInputChange}
                      step="0.0001"
                      min="0"
                    />
                  </div>
                </div>
              )}

              {/* Tab 2: Micronutrients */}
              {modalTab === 'micro' && (
                <div>
                  <h3 style={{ marginBottom: '15px' }}>Micronutrients</h3>
                  <p style={{ color: '#7f8c8d', fontSize: '0.9rem', marginBottom: '15px' }}>
                    Define the micronutrients of this ingredient (e.g. Iron: 2.7mg, Calcium: 120mg).
                  </p>
                  
                  {micronutrientsList.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px dashed #bdc3c7', marginBottom: '15px' }}>
                      No micronutrients added yet.
                    </div>
                  ) : (
                    micronutrientsList.map((item, index) => (
                      <div key={index} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <CreatableSelect
                            options={existingMicros.map(m => ({ value: m, label: m }))}
                            value={item.name ? { value: item.name, label: item.name } : null}
                            onChange={(option) => handleMicroChange(index, 'name', option ? option.value : '')}
                            placeholder="Nutrient Name..."
                            isClearable
                            formatCreateLabel={(inputValue) => `Create new nutrient: "${inputValue}"`}
                            styles={{ menuPortal: base => ({ ...base, zIndex: 9999 }) }}
                            menuPortalTarget={document.body}
                          />
                        </div>
                        <input
                          type="text"
                          placeholder="Amount & Unit (e.g. 90mg)"
                          value={item.value}
                          onChange={(e) => handleMicroChange(index, 'value', e.target.value)}
                          style={{ flex: 1 }}
                          required
                        />
                        <button
                          type="button"
                          className="btn btn-danger btn-small"
                          onClick={() => handleMicroDelete(index)}
                          style={{ padding: '10px 15px' }}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                  
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={handleMicroAdd}
                  >
                    + Add Micronutrient
                  </button>
                </div>
              )}

              {/* Tab 3: Benefits */}
              {modalTab === 'benefits' && (
                <div>
                  <h3 style={{ marginBottom: '15px' }}>Benefits</h3>
                  <p style={{ color: '#7f8c8d', fontSize: '0.9rem', marginBottom: '15px' }}>
                    Define specific health benefits of this ingredient (e.g. Immunity: High in Vitamin C, Heart: Decreases LDL).
                  </p>

                  {benefitsList.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', backgroundColor: '#f8f9fa', borderRadius: '6px', border: '1px dashed #bdc3c7', marginBottom: '15px' }}>
                      No benefits added yet.
                    </div>
                  ) : (
                    benefitsList.map((item, index) => (
                      <div key={index} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
                        <input
                          type="text"
                          placeholder="Benefit Title (e.g. Digestion)"
                          value={item.name}
                          onChange={(e) => handleBenefitChange(index, 'name', e.target.value)}
                          style={{ flex: 1 }}
                          required
                        />
                        <input
                          type="text"
                          placeholder="Benefit Description (e.g. Rich in soluble fiber)"
                          value={item.value}
                          onChange={(e) => handleBenefitChange(index, 'value', e.target.value)}
                          style={{ flex: 2 }}
                          required
                        />
                        <button
                          type="button"
                          className="btn btn-danger btn-small"
                          onClick={() => handleBenefitDelete(index)}
                          style={{ padding: '10px 15px' }}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}

                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={handleBenefitAdd}
                  >
                    + Add Benefit
                  </button>
                </div>
              )}

              {/* Tab 4: Caution & Notes */}
              {modalTab === 'additional' && (
                <div>
                  <div className="form-group">
                    <label>Caution / Allergen Info</label>
                    <textarea
                      name="caution"
                      value={formData.caution}
                      onChange={handleInputChange}
                      placeholder="e.g., Contains gluten, May cause allergies"
                    />
                  </div>

                  <div className="form-group">
                    <label>Notes</label>
                    <textarea
                      name="notes"
                      value={formData.notes}
                      onChange={handleInputChange}
                      placeholder="Any additional notes about this ingredient"
                    />
                  </div>

                  <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '15px' }}>
                    <input
                      type="checkbox"
                      id="ingredient_active_checkbox"
                      name="is_active"
                      checked={formData.is_active}
                      onChange={handleInputChange}
                      style={{ width: 'auto', margin: 0, cursor: 'pointer' }}
                    />
                    <label htmlFor="ingredient_active_checkbox" style={{ margin: 0, cursor: 'pointer', fontWeight: 'normal' }}>
                      Active
                    </label>
                  </div>
                </div>
              )}

              <div className="button-group" style={{ marginTop: '30px', borderTop: '1px solid #ecf0f1', paddingTop: '20px' }}>
                <button type="submit" className="btn btn-success">
                  {editingId ? 'Update Ingredient' : 'Create Ingredient'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Micronutrients Recommendations Suggestions Datalist */}
      <datalist id="micro-suggestions">
        {existingMicros.map(micro => (
          <option key={micro} value={micro} />
        ))}
      </datalist>
    </div>
  );
}
