# Diet Plan Studio 🥦🥗

Diet Plan Studio is a production-ready, full-stack, multi-cuisine personalized diet planner and companion application. It features a high-performance **FastAPI** backend integrated with a modern **React + Vite + CSS** SPA frontend. The application calculates precise daily nutrition targets and dynamically structures customized multi-day meal plans based on regional cuisines, user profiles, goals, and health constraints.

Additionally, the project integrates an **intelligent AI Diet Companion agent** powered by local LLMs (via Ollama) and robust rule-based intent parsing, allowing users to control their profile, request substitutions, swap meals, and navigate the application conversationally.

---

## 🚀 Key Feature Highlights

### 📊 1. Profile & Target Nutrition Engine
* **BMR & Macro Calculation:** Computes daily caloric requirements and macronutrient splits (Protein, Carbs, Fat, Fiber) based on age, gender, height, weight, activity level, and goals (e.g., muscle gain, fat loss, maintenance).
* **Multi-Cuisine Datasets:** Supports regional cuisine customization including North Indian, South Indian, UAE/Middle Eastern, Continental, Mediterranean, and more.

### 🍽️ 2. Dynamic Meal Planner & Rankings
* **Constraint-Based Beam Search:** Ranks and suggests meals from the database that align with the user's specific diet types (e.g., Vegetarian, Vegan, Keto), allergies, and target macros.
* **Multi-Day Meal Plans:** Distributes meal allocations across customizable daily slots (e.g., breakfast, lunch, dinner, snacks).

### 🔄 3. Three-Tier Swapping Engine
Allows granular adjustments to generated diet plans:
1. **Meal-Level Swap:** Replaces an entire meal slot with calorically and macro-similar alternatives.
2. **Food-Level Swap:** Swaps individual food items inside a meal while maintaining nutritional integrity.
3. **Ingredient-Level Swap:** Replaces specific ingredients (e.g., due to taste preferences or allergies) while automatically compiling and scaling macro-nutrients.

### 🤖 4. Conversational AI Diet Companion
An embedded chat assistant that assists the user with plan management:
* **Interactive Preferences:** Learns likes, dislikes, and allergies during conversations and updates user preference schemas dynamically.
* **Action Block Orchestration:** Executes actions on behalf of the user (e.g., updating profile parameters, navigating pages, executing meal swaps) using `<ACTION>` block JSON payloads.
* **Typo-Safety & Verification:** Intercepts ambiguous inputs (e.g., typos in views or values) to ask for verification using `<QUICK_REPLIES>` options (Yes/No).
* **Intelligent Explanations:** Explains *why* specific meals were chosen based on user goals and recipe parameters.

---

## 📁 Project Structure

```text
.
├── backend/                    # FastAPI Backend Application
│   ├── ai/
│   │   └── ai_agent.py         # AI companion: LLM integration (Ollama), intent parser & actions
│   ├── app.py                  # API entry point and routes registration
│   ├── chat_memory/            # Local JSON storage for user session preference history
│   ├── config/                 # Configurations for constants, logging, errors, and environment settings
│   ├── database/               # Database management
│   │   ├── base.py             # SQLAlchemy Base configuration
│   │   ├── etl_import.py       # Data pipeline: ingests raw JSON datasets and seeds the DB
│   │   ├── models/             # SQLAlchemy schemas (Chat, Cuisine, Food, Ingredient, Meal, Preference)
│   │   └── session.py          # Async session setup
│   ├── domain/                 # Domain logic: unit scaling, macro scaling, and nutrition compilation formulas
│   ├── repositories/           # Repository pattern wrappers for meals, foods, and chats
│   ├── schemas.py              # Pydantic validation models for endpoints
│   ├── services/               # Core business logic (planner, ranking, swap, and nutrition services)
│   ├── studio/                 # Endpoint routers (/api/studio and /api/chat)
│   └── utils/                  # Miscellaneous utility files
│
├── frontend/                   # React + Vite Frontend Application
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js          # Proxies "/api" request patterns to localhost:8000
│   └── src/
│       ├── App.jsx             # React application shell, routing, and layout
│       ├── main.jsx            # Entry point mount
│       ├── styles.css          # Core CSS design system
│       ├── components/         # Reusable UI components (wizard, planners, swap drawers, chat panels)
│       ├── hooks/              # Custom React hooks (PDF export generation, profile caches, swap state)
│       └── services/           # Axios-based API services for communication with FastAPI
│
├── Data new/                   # Raw Multi-Cuisine Datasets (JSON files)
│   ├── Indian/                 # North and South Indian recipe lists
│   ├── Others/                 # UAE, Continental, Mediterranean and shared ingredients
│   └── Images/                 # Image assets and master_image_mapping.json
│
├── tests/                      # Python pytest files
│   ├── conftest.py             # Pytest fixtures and mock database settings
│   └── unit/                   # Unit tests (nutrition calculations, macro scaling formulas)
│
├── requirements.txt            # Python dependencies
├── start_project.ps1           # Windows PowerShell script to launch backend & frontend concurrently
└── README.md                   # Project documentation
```

---

## 🛠️ Setup & Installation

### Prerequisites
* **Python 3.9+**
* **Node.js 18+**
* **Ollama** (Optional, for local LLM AI Chat support. Default model: `gemma3:4b`)

---

### 1. Backend Setup (FastAPI)

1. Navigate to the backend folder and create a virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   ```
2. Activate the virtual environment:
   * **Windows:** `.venv\Scripts\activate`
   * **Linux/Mac:** `source .venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `backend/.env` (refer to `config/settings.py` for defaults).

---

### 2. Database Ingestion (ETL Pipeline)
Before running the server, import the multi-cuisine raw data assets into the database:
```bash
# In backend virtual environment
python database/etl_import.py
```
This script:
* Initializes SQLite/PostgreSQL schemas.
* Ingests cuisines, raw ingredients, foods, meals, and default user preferences.
* Dynamically compiles and caches food-level and meal-level macronutrients from ingredient definitions.
* Maps recipe image paths to their relative static files in `Data new/Images`.

---

### 3. Frontend Setup (React)

1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install package dependencies:
   ```bash
   npm install
   ```

---

## 🏃 Running the Application

### Option A: Launch Concurrently (Windows)
You can start both frontend and backend development servers in individual PowerShell windows using the root script:
```powershell
./start_project.ps1
```

### Option B: Run Manually
* **Run FastAPI Backend:**
  ```bash
  cd backend
  uvicorn app:app --reload --port 8000
  ```
  The API docs will be interactive at `http://localhost:8000/docs`.

* **Run Vite Frontend:**
  ```bash
  cd frontend
  npm run dev
  ```
  Open `http://localhost:5173` in your browser. All frontend `/api/*` requests will be proxied to the backend at `http://localhost:8000`.

---

## 🧪 Running Tests
The project uses `pytest` for backend unit testing:
```bash
cd backend
pytest
```
* **`tests/unit/test_nutrition.py`**: Asserts core ingredient-to-food macro compile calculations.
* **`tests/unit/test_scaling.py`**: Verifies ingredient/meal quantity scaling algorithms.
