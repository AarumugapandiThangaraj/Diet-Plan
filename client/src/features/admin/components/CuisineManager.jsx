import React, { useState, useEffect } from 'react';
import { adminApi } from '../adminApi';

export default function CuisineManager() {
  const [cuisines, setCuisines] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    name_en: '',
    name_ar: '',
    sort_order: 0,
    is_active: true
  });

  useEffect(() => {
    loadCuisines();
  }, []);

  const loadCuisines = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await adminApi.cuisines.list(1000);
      setCuisines(data.items);
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

  const resetForm = () => {
    setFormData({
      code: '',
      name_en: '',
      name_ar: '',
      sort_order: 0,
      is_active: true
    });
    setEditingId(null);
  };

  const handleOpenModal = (cuisine = null) => {
    if (cuisine) {
      setFormData(cuisine);
      setEditingId(cuisine.id);
    } else {
      resetForm();
    }
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      if (editingId) {
        await adminApi.cuisines.update(editingId, formData);
        setSuccess('Cuisine updated successfully!');
      } else {
        await adminApi.cuisines.create(formData);
        setSuccess('Cuisine created successfully!');
      }
      setShowModal(false);
      await loadCuisines();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, permanent = false) => {
    const warningMsg = permanent 
      ? "⚠️ WARNING: This will permanently delete this cuisine from the database! Any foods or meals using it may break. Are you absolutely sure?"
      : "Are you sure you want to deactivate (soft-delete) this cuisine?";
    if (!confirm(warningMsg)) return;
    setError('');
    try {
      await adminApi.cuisines.delete(id, permanent);
      setSuccess(permanent ? 'Cuisine permanently deleted successfully!' : 'Cuisine deactivated successfully!');
      await loadCuisines();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredCuisines = cuisines.filter(c => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      c.id.toString().includes(query) ||
      (c.code || '').toLowerCase().includes(query) ||
      (c.name_en || '').toLowerCase().includes(query) ||
      (c.name_ar || '').toLowerCase().includes(query)
    );
  });

  if (loading) return <div className="loading"><div className="loading-spinner"></div></div>;

  return (
    <div className="form-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Manage Cuisines</h2>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          Add New Cuisine
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: '20px', maxWidth: '400px' }}>
        <input
          type="text"
          placeholder="🔍 Search cuisine by ID, name, or code..."
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
        {filteredCuisines.length === 0 ? (
          <div className="empty-state">
            <p>{searchQuery ? 'No cuisines match your search.' : 'No cuisines found. Create one to get started!'}</p>
          </div>
        ) : (
          <table className="list-table">
            <thead>
              <tr>
                <th>S.No.</th>
                <th>System ID</th>
                <th>Code</th>
                <th>English Name</th>
                <th>Arabic Name</th>
                <th>Order</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCuisines.map((cuisine, index) => (
                <tr key={cuisine.id}>
                  <td>{index + 1}</td>
                  <td><strong>{cuisine.id}</strong></td>
                  <td><code>{cuisine.code}</code></td>
                  <td>{cuisine.name_en}</td>
                  <td>{cuisine.name_ar || '-'}</td>
                  <td>{cuisine.sort_order}</td>
                  <td>{cuisine.is_active ? '✓' : '✗'}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn btn-secondary btn-small" onClick={() => handleOpenModal(cuisine)}>
                        Edit
                      </button>
                      {cuisine.is_active ? (
                        <button className="btn btn-warning btn-small" onClick={() => handleDelete(cuisine.id, false)}>
                          Deactivate
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.85rem', color: '#7f8c8d', fontStyle: 'italic', display: 'flex', alignItems: 'center', backgroundColor: '#f5f7fa', padding: '2px 8px', borderRadius: '4px' }}>Inactive</span>
                      )}
                      <button className="btn btn-danger btn-small" onClick={() => handleDelete(cuisine.id, true)}>
                        Delete Permanently
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => !editingId && setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingId ? 'Edit Cuisine' : 'Create New Cuisine'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Code (e.g., north_indian)</label>
                <input
                  type="text"
                  name="code"
                  value={formData.code}
                  onChange={handleInputChange}
                  required
                  disabled={editingId}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>English Name</label>
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
              <div className="form-row">
                <div className="form-group">
                  <label>Sort Order</label>
                  <input
                    type="number"
                    name="sort_order"
                    value={formData.sort_order}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginTop: '24px' }}>
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
              </div>
              <div className="button-group">
                <button type="submit" className="btn btn-success">
                  {editingId ? 'Update Cuisine' : 'Create Cuisine'}
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
