# Admin Data Entry Portal

A comprehensive web-based data management system for managing diet plan database entries (cuisines, meal sessions, ingredients, foods, and meals).

## 📁 Project Structure

### Backend (Python/FastAPI)

```
server/admin/
├── __init__.py
├── router.py         # API endpoint definitions
├── schemas.py        # Pydantic data models for request/response validation
└── services.py       # Business logic for CRUD operations
```

**API Endpoints** (Base URL: `http://localhost:8000/api/admin`)

- **Cuisines**: `GET/POST /cuisines`, `GET/PUT/DELETE /cuisines/{id}`
- **Meal Sessions**: `GET/POST /meal-sessions`, `GET/PUT/DELETE /meal-sessions/{id}`
- **Ingredients**: `GET/POST /ingredients`, `GET/PUT/DELETE /ingredients/{id}`
- **Foods**: `GET/POST /foods`, `GET/PUT/DELETE /foods/{id}`
- **Meals**: `GET/POST /meals`, `GET/PUT/DELETE /meals/{id}`

### Frontend (React)

```
client/src/features/admin/
├── AdminDataEntry.jsx              # Main container component with tab navigation
├── AdminDataEntry.css              # Comprehensive styling
├── adminApi.js                     # API service wrapper for all endpoints
└── components/
    ├── CuisineManager.jsx          # CRUD UI for cuisines
    ├── MealSessionManager.jsx       # CRUD UI for meal sessions
    ├── IngredientManager.jsx        # CRUD UI for ingredients
    ├── FoodManager.jsx              # CRUD UI for foods (with ingredient composition)
    └── MealManager.jsx              # CRUD UI for meals (with food composition)
```

## 🚀 Getting Started

### Prerequisites
- Backend running on `localhost:8000`
- Python FastAPI application
- React development environment

### Installation

#### 1. Backend Setup

The admin routes are already integrated into `server/app.py`:

```python
from admin.router import router as admin_router
app.include_router(admin_router)
```

Start the backend:
```bash
cd server
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Integration

Import and use the AdminDataEntry component in your React app:

```jsx
import AdminDataEntry from './features/admin/AdminDataEntry';

// In your App.jsx or routing
<AdminDataEntry />
```

Or add a route:
```jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

<Router>
  <Routes>
    <Route path="/admin" element={<AdminDataEntry />} />
  </Routes>
</Router>
```

Start the frontend:
```bash
cd client
npm install
npm run dev
```

Access the admin portal at: `http://localhost:5173/admin` (or your dev server URL)

## 📚 Features

### 1. **Cuisine Management**
- ✅ List all cuisines with sorting and pagination
- ✅ Create new cuisines with bilingual support (English/Arabic)
- ✅ Edit existing cuisines
- ✅ Delete cuisines (hard delete)
- ✅ Toggle active status

**Fields:**
- Code (e.g., `north_indian`, `mediterranean`)
- Name (English & Arabic)
- Sort Order
- Active Status

### 2. **Meal Session Management**
- ✅ Manage meal time slots (breakfast, lunch, dinner, etc.)
- ✅ Set default times for each session
- ✅ Bilingual support
- ✅ Sort order configuration

**Fields:**
- Code (e.g., `breakfast`)
- Name (English & Arabic)
- Default Time (HH:MM:SS)
- Sort Order
- Active Status

### 3. **Ingredient Management**
- ✅ Add/edit/delete master ingredients
- ✅ Store nutritional information per 100g:
  - Calories (kcal)
  - Protein (g)
  - Carbohydrates (g)
  - Fat (g)
  - Fiber (g)
- ✅ Add micronutrients and benefits (JSON)
- ✅ Track allergens and cautions
- ✅ Soft delete (marks as inactive)

**Fields:**
- Name (English & Arabic)
- Default Unit (g, ml, cup, etc.)
- Macronutrients
- Micronutrients (JSON)
- Benefits (JSON)
- Caution/Allergen Info
- Notes

### 4. **Food Management**
- ✅ Create composite foods from ingredients
- ✅ Link ingredients with quantities
- ✅ Set food roles (base, side, snack, dessert, beverage, condiment)
- ✅ Prep time tracking
- ✅ Quantity bounds (min/max)
- ✅ Diet type and support flags
- ✅ Image URL storage

**Fields:**
- Cuisine (dropdown)
- Client Food ID
- Name (English & Arabic)
- Description & Preparation (bilingual)
- Food Role (dropdown)
- Quantity & Unit
- Min/Max Quantity bounds
- Prep Time
- Diet Types (JSON)
- Ingredients (linked via food_ingredients table)

**Ingredient Composition:**
- Select ingredients and quantities
- Set sort order
- Add/remove ingredients dynamically

### 5. **Meal Management**
- ✅ Create meals from foods
- ✅ Assign to meal sessions
- ✅ Mark foods as replaceable
- ✅ Link goal and secondary goals
- ✅ Diet type specification

**Fields:**
- Cuisine (dropdown)
- Meal Session (dropdown)
- Client Meal ID
- Name (English & Arabic)
- Description
- Goal & Secondary Goals (JSON)
- Diet Types (JSON)
- Foods (linked via meal_foods table)

**Food Composition:**
- Select foods for the meal
- Mark as replaceable
- Set sort order
- Add/remove foods dynamically

## 🎨 User Interface

### Design Features
- **Responsive Layout**: Works on desktop and tablet
- **Tab Navigation**: Switch between different data types
- **Modal Forms**: Clean, focused editing experience
- **List Views**: Table with pagination support
- **Search/Filter**: Filter by cuisine for foods and meals
- **Validation**: Required field indicators and error messages
- **Success Alerts**: Feedback on CRUD operations
- **Soft Deletes**: Ingredients, foods, and meals use soft delete (is_active flag)

### Color Scheme
- Primary: Purple gradient (#667eea → #764ba2)
- Success: Green (#27ae60)
- Danger: Red (#e74c3c)
- Warning: Orange (#f39c12)
- Neutral: Gray (#ecf0f1)

## 🔌 API Documentation

### Create Cuisine

```bash
POST /api/admin/cuisines
Content-Type: application/json

{
  "code": "north_indian",
  "name_en": "North Indian",
  "name_ar": "الهند الشمالية",
  "sort_order": 1,
  "is_active": true
}
```

### Create Ingredient

```bash
POST /api/admin/ingredients
Content-Type: application/json

{
  "name_en": "Basmati Rice",
  "name_ar": "أرز بسمتي",
  "default_unit": "g",
  "calories_kcal": 130,
  "protein_g": 2.7,
  "carbs_g": 28,
  "fat_g": 0.3,
  "fiber_g": 0.4,
  "micronutrients": {
    "iron": "0.8mg",
    "magnesium": "25mg"
  },
  "benefits": {
    "energy": "Rich in carbohydrates",
    "digestion": "Contains fiber"
  },
  "caution": "May contain allergens",
  "is_active": true
}
```

### Create Food with Ingredients

```bash
POST /api/admin/foods
Content-Type: application/json

{
  "cuisine_id": 1,
  "client_food_id": "FOOD_001",
  "name_en": "Chicken Curry",
  "name_ar": "كاري الدجاج",
  "description_en": "Spiced chicken in gravy",
  "food_role": "base",
  "quantity": 250,
  "unit": "g",
  "is_active": true,
  "food_ingredients": [
    {
      "ingredient_id": 1,
      "quantity": 200,
      "sort_order": 0
    },
    {
      "ingredient_id": 2,
      "quantity": 50,
      "sort_order": 1
    }
  ]
}
```

### Create Meal with Foods

```bash
POST /api/admin/meals
Content-Type: application/json

{
  "cuisine_id": 1,
  "client_meal_id": "MEAL_001",
  "name_en": "Chicken Curry Rice",
  "meal_session_id": 3,
  "is_active": true,
  "meal_foods": [
    {
      "food_id": 1,
      "is_replaceable": true,
      "sort_order": 0
    },
    {
      "food_id": 2,
      "is_replaceable": false,
      "sort_order": 1
    }
  ]
}
```

## 📊 Database Integration

The system connects to your PostgreSQL database via the backend. All tables are in the `Twellr_Nutri` schema:

- `cuisines` - Cuisine reference data
- `meal_sessions` - Meal time slots
- `ingredients_master` - Master ingredients
- `foods` - Composite foods
- `food_ingredients` - Food-to-ingredient mapping
- `meals` - Meal recipes
- `meal_foods` - Meal-to-food mapping

## 🔒 Soft Deletes

Ingredients, foods, and meals use soft deletion:
- **Hard Delete**: Cuisines and Meal Sessions
- **Soft Delete**: Ingredients, Foods, Meals (sets `is_active = false` and `deleted_at = now()`)

Active-only queries are available via the `active_only` parameter.

## 🛠️ Development

### Adding New Entities

To add management for a new entity:

1. **Create Schema** in `server/admin/schemas.py`:
   ```python
   class MyEntityCreate(BaseModel):
       field1: str
       field2: int
   ```

2. **Create Service** in `server/admin/services.py`:
   ```python
   class MyEntityService:
       @staticmethod
       async def list_entities(session):
           # Implementation
       # ... other CRUD methods
   ```

3. **Create Routes** in `server/admin/router.py`:
   ```python
   @router.get("/my-entities")
   async def list_entities():
       # Implementation
   ```

4. **Create React Component** in `client/src/features/admin/components/`:
   ```jsx
   export default function MyEntityManager() {
       // Component code
   }
   ```

5. **Update Main Component** in `AdminDataEntry.jsx`:
   ```jsx
   import MyEntityManager from './components/MyEntityManager';
   ```

## 📝 Notes

- All bilingual fields (English/Arabic) are stored as separate columns
- JSON fields (micronutrients, benefits, diet_types, etc.) are stored in JSONB format
- Normalized text arrays are indexed for efficient filtering
- Timestamps are automatically managed (created_at, updated_at)
- All numeric fields support decimal values
- Modal forms prevent accidental closure while editing

## 🚨 Error Handling

- Comprehensive error messages for validation failures
- Network error handling with retry suggestions
- Database constraint violation messages
- Duplicate key detection
- Foreign key constraint warnings

## ✨ Future Enhancements

- Bulk import/export (CSV, JSON)
- Advanced search and filtering
- Meal plan templates
- Nutritional analysis dashboard
- Image upload integration
- Audit logs
- User permissions/roles
- Nutritional macro validation
- Recipe cloning
- Batch operations

---

**Need Help?** Check the database schema files in `database/nutri_schema_design_v2/` for detailed table documentation.
