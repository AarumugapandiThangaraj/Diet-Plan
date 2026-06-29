import React, { useState, useEffect } from 'react';
import CuisineManager from './components/CuisineManager';
import MealSessionManager from './components/MealSessionManager';
import IngredientManager from './components/IngredientManager';
import FoodManager from './components/FoodManager';
import MealManager from './components/MealManager';
import './AdminDataEntry.css';

export default function AdminDataEntry() {
  const getActiveTabFromHash = () => {
    const hash = window.location.hash || '';
    if (hash.startsWith('#admin')) {
      const parts = hash.split('/');
      return parts[1] || 'cuisines';
    }
    return 'cuisines';
  };

  const [activeTab, setActiveTab] = useState(getActiveTabFromHash);

  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getActiveTabFromHash());
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleTabChange = (tabId) => {
    window.location.hash = `#admin/${tabId}`;
  };

  const tabs = [
    { id: 'cuisines', label: 'Cuisines', component: CuisineManager },
    { id: 'sessions', label: 'Meal Sessions', component: MealSessionManager },
    { id: 'ingredients', label: 'Ingredients', component: IngredientManager },
    { id: 'foods', label: 'Foods', component: FoodManager },
    { id: 'meals', label: 'Meals', component: MealManager }
  ];

  const ActiveComponent = tabs.find(t => t.id === activeTab)?.component;

  return (
    <div className="admin-data-entry">
      <div className="admin-header">
        <h1>Admin Data Entry Portal</h1>
        <p>Manage cuisines, meals, ingredients, and foods</p>
      </div>

      <div className="admin-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => handleTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="admin-content">
        {ActiveComponent && <ActiveComponent />}
      </div>
    </div>
  );
}
