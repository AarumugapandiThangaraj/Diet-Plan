import React, { useState, useEffect } from 'react'
import { ProfileProvider } from './contexts/ProfileContext.jsx'
import { PlannerProvider } from './contexts/PlannerContext.jsx'
import PlanStudio from './features/planner/PlanStudio.jsx'
import Dashboard from './features/dashboard/Dashboard.jsx'
import AdminDataEntry from './features/admin/AdminDataEntry.jsx'

function getInitialViewAndTab() {
  const hash = window.location.hash || '';
  if (hash.startsWith('#dashboard')) {
    return { view: 'dashboard', tab: null };
  } else if (hash.startsWith('#admin')) {
    const parts = hash.split('/');
    const tab = parts[1] || 'cuisines';
    return { view: 'admin', tab };
  }
  return { view: 'studio', tab: null };
}

export default function App() {
  const [currentView, setCurrentView] = useState(() => getInitialViewAndTab().view)

  useEffect(() => {
    const handleHashChange = () => {
      const { view } = getInitialViewAndTab();
      setCurrentView(view);
    };

    // Set default hash to #studio if none is present
    if (!window.location.hash) {
      window.location.hash = '#studio';
    }

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = (view, tab = null) => {
    if (view === 'admin') {
      window.location.hash = `#admin/${tab || 'cuisines'}`;
    } else if (view === 'dashboard') {
      window.location.hash = '#dashboard';
    } else {
      window.location.hash = '#studio';
    }
  };

  return (
    <ProfileProvider>
      <PlannerProvider>
        {currentView === 'admin' ? (
          <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
            <div style={{ padding: '10px', backgroundColor: '#fff', borderBottom: '1px solid #e0e0e0' }}>
              <button onClick={() => navigateTo('studio')} style={{ padding: '8px 16px', marginRight: '8px', cursor: 'pointer' }}>
                ← Back to Studio
              </button>
            </div>
            <AdminDataEntry />
          </div>
        ) : currentView === 'dashboard' ? (
          <Dashboard onNavigateToStudio={() => navigateTo('studio')} />
        ) : (
          <div>
            <PlanStudio onNavigateToDashboard={() => navigateTo('dashboard')} />
            <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 999 }}>
              <button 
                onClick={() => navigateTo('admin')}
                style={{ 
                  padding: '10px 16px', 
                  backgroundColor: '#4CAF50', 
                  color: 'white', 
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}
              >
                📋 Admin Panel
              </button>
            </div>
          </div>
        )}
      </PlannerProvider>
    </ProfileProvider>
  )
}
