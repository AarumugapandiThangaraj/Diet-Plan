import React, { useState, useEffect } from 'react';
import { adminApi } from '../adminApi';

export default function GenericReferenceManager({ title, apiName, codeLabel = "Code" }) {
  const [items, setItems] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    name_en: '',
    is_active: true
  });

  const api = adminApi[apiName];

  useEffect(() => {
    loadItems();
  }, []);

  const loadItems = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.list(1000);
      setItems(data.items);
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
      is_active: true
    });
    setEditingId(null);
  };

  const handleOpenModal = (item = null) => {
    if (item) {
      setFormData(item);
      setEditingId(item.id);
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
        await api.update(editingId, formData);
        setSuccess(`${title} updated successfully!`);
      } else {
        await api.create(formData);
        setSuccess(`${title} created successfully!`);
      }
      setShowModal(false);
      await loadItems();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, permanent = false) => {
    const warningMsg = permanent 
      ? `⚠️ WARNING: This will permanently delete this ${title.toLowerCase()} from the database! Are you absolutely sure?`
      : `Are you sure you want to deactivate (soft-delete) this ${title.toLowerCase()}?`;
    if (!window.confirm(warningMsg)) return;
    setError('');
    try {
      await api.delete(id, permanent);
      setSuccess(permanent ? `${title} permanently deleted!` : `${title} deactivated!`);
      await loadItems();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredItems = items.filter(c => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      c.id.toString().includes(query) ||
      (c.code || '').toLowerCase().includes(query) ||
      (c.name_en || '').toLowerCase().includes(query)
    );
  });

  if (loading) return <div className="loading"><div className="loading-spinner"></div></div>;

  return (
    <div className="form-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Manage {title}</h2>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          Add New {title}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: '20px', maxWidth: '400px' }}>
        <input
          type="text"
          placeholder={`🔍 Search ${title.toLowerCase()} by ID, name, or code...`}
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
        {filteredItems.length === 0 ? (
          <div className="empty-state">
            <p>{searchQuery ? 'No items match your search.' : `No ${title.toLowerCase()} found. Create one to get started!`}</p>
          </div>
        ) : (
          <table className="list-table">
            <thead>
              <tr>
                <th>S.No.</th>
                <th>System ID</th>
                <th>{codeLabel}</th>
                <th>English Name</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item, index) => (
                <tr key={item.id}>
                  <td>{index + 1}</td>
                  <td><strong>{item.id}</strong></td>
                  <td><code>{item.code}</code></td>
                  <td>{item.name_en}</td>
                  <td>{item.is_active ? '✓' : '✗'}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn btn-secondary btn-small" onClick={() => handleOpenModal(item)}>
                        Edit
                      </button>
                      {item.is_active ? (
                        <button className="btn btn-warning btn-small" onClick={() => handleDelete(item.id, false)}>
                          Deactivate
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.85rem', color: '#7f8c8d', fontStyle: 'italic', display: 'flex', alignItems: 'center', backgroundColor: '#f5f7fa', padding: '2px 8px', borderRadius: '4px' }}>Inactive</span>
                      )}
                      <button className="btn btn-danger btn-small" onClick={() => handleDelete(item.id, true)}>
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
              <h2>{editingId ? `Edit ${title}` : `Create New ${title}`}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>{codeLabel}</label>
                <input
                  type="text"
                  name="code"
                  value={formData.code}
                  onChange={handleInputChange}
                  required
                  disabled={editingId}
                />
              </div>
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
              <div className="button-group">
                <button type="submit" className="btn btn-success">
                  {editingId ? 'Update' : 'Create'}
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
