import React, { useState, useEffect } from 'react';
import { adminApi } from '../adminApi';

const formatTimeAMPM = (timeStr) => {
  if (!timeStr) return '-';
  const parts = timeStr.split(':');
  if (parts.length < 2) return timeStr;
  
  let hours = parseInt(parts[0], 10);
  const minutes = parts[1];
  const ampm = hours >= 12 ? 'PM' : 'AM';
  
  hours = hours % 12;
  hours = hours ? hours : 12; // the hour '0' should be '12'
  const strHours = hours < 10 ? `0${hours}` : hours;
  
  return `${strHours}:${minutes} ${ampm}`;
};

export default function MealSessionManager() {
  const [sessions, setSessions] = useState([]);
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
    start_time: '',
    end_time: '',
    sort_order: 0,
    is_active: true
  });

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await adminApi.mealSessions.list(1000);
      setSessions(data.items);
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
      start_time: '',
      end_time: '',
      sort_order: 0,
      is_active: true
    });
    setEditingId(null);
  };

  const handleOpenModal = (session = null) => {
    if (session) {
      setFormData(session);
      setEditingId(session.id);
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
      const submissionData = {
        ...formData,
        start_time: formData.start_time || null,
        end_time: formData.end_time || null
      };
      if (editingId) {
        await adminApi.mealSessions.update(editingId, submissionData);
        setSuccess('Meal session updated successfully!');
      } else {
        await adminApi.mealSessions.create(submissionData);
        setSuccess('Meal session created successfully!');
      }
      setShowModal(false);
      await loadSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id, permanent = false) => {
    const warningMsg = permanent 
      ? "⚠️ WARNING: This will permanently delete this meal session from the database! Any meals using it may break. Are you absolutely sure?"
      : "Are you sure you want to deactivate (soft-delete) this meal session?";
    if (!confirm(warningMsg)) return;
    setError('');
    try {
      await adminApi.mealSessions.delete(id, permanent);
      setSuccess(permanent ? 'Meal session permanently deleted successfully!' : 'Meal session deactivated successfully!');
      await loadSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredSessions = sessions.filter(s => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      s.id.toString().includes(query) ||
      (s.code || '').toLowerCase().includes(query) ||
      (s.name_en || '').toLowerCase().includes(query) ||
      (s.name_ar || '').toLowerCase().includes(query) ||
      (formatTimeAMPM(s.start_time) || '').toLowerCase().includes(query) ||
      (formatTimeAMPM(s.end_time) || '').toLowerCase().includes(query)
    );
  });

  if (loading) return <div className="loading"><div className="loading-spinner"></div></div>;

  return (
    <div className="form-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Manage Meal Sessions</h2>
        <button className="btn btn-primary" onClick={() => handleOpenModal()}>
          Add New Session
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div style={{ marginBottom: '20px', maxWidth: '400px' }}>
        <input
          type="text"
          placeholder="🔍 Search session by ID, name, time, or code..."
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
        {filteredSessions.length === 0 ? (
          <div className="empty-state">
            <p>{searchQuery ? 'No meal sessions match your search.' : 'No meal sessions found. Create one to get started!'}</p>
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
                <th>Start Time</th>
                <th>End Time</th>
                <th>Order</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.map((session, index) => (
                <tr key={session.id}>
                  <td>{index + 1}</td>
                  <td><strong>{session.id}</strong></td>
                  <td><code>{session.code}</code></td>
                  <td>{session.name_en}</td>
                  <td>{session.name_ar || '-'}</td>
                  <td>{formatTimeAMPM(session.start_time)}</td>
                  <td>{formatTimeAMPM(session.end_time)}</td>
                  <td>{session.sort_order}</td>
                  <td>{session.is_active ? '✓' : '✗'}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn btn-secondary btn-small" onClick={() => handleOpenModal(session)}>
                        Edit
                      </button>
                      {session.is_active ? (
                        <button className="btn btn-warning btn-small" onClick={() => handleDelete(session.id, false)}>
                          Deactivate
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.85rem', color: '#7f8c8d', fontStyle: 'italic', display: 'flex', alignItems: 'center', backgroundColor: '#f5f7fa', padding: '2px 8px', borderRadius: '4px' }}>Inactive</span>
                      )}
                      <button className="btn btn-danger btn-small" onClick={() => handleDelete(session.id, true)}>
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
              <h2>{editingId ? 'Edit Meal Session' : 'Create New Meal Session'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Code (e.g., breakfast)</label>
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
                  <label>Start Time</label>
                  <input
                    type="time"
                    name="start_time"
                    value={formData.start_time || ''}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="form-group">
                  <label>End Time</label>
                  <input
                    type="time"
                    name="end_time"
                    value={formData.end_time || ''}
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
              </div>
              <div className="form-group">
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
                  {editingId ? 'Update Session' : 'Create Session'}
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
