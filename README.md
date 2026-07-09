# 🥗 Diet Plan Studio (NutriLLM)

An AI-powered, personalized nutrition planning, meal recommendation, and dietary swap platform. Diet Plan Studio allows users to calculate customized calorie/macronutrient targets, generate multi-day diet plans, swap meals/foods/ingredients dynamically, track daily consumption, and converse with an AI Nutrition Assistant powered by a local Ollama model.

---

## 🚀 Key Features

*   **Plan Studio**: Input body profile details (age, height, weight, activity levels, health goals) to compute BMI, BMR, TDEE, and daily target macros.
*   **Meal Recommendation & Ranking**: Automatically scores and ranks recipes/meals from the database based on how well they fit the user's macronutrient targets.
*   **Dynamic Swapping**:
    *   *Meal Swap*: Swap whole meals while keeping macros optimized.
    *   *Food Swap*: Replace specific foods within a meal.
    *   *Ingredient Swap*: Replace specific ingredients within a recipe with scaled quantities.
*   **AI Companion Chat**: A chat interface powered by Ollama (local LLM) that recognizes user preferences, suggests food substitutions, and helps build plans conversationally.
*   **Admin Data Entry Portal**: A comprehensive, tabbed CRUD system to manage cuisines, meal sessions, master ingredients (with calorie/macromicro details), foods, and meal recipes.
*   **User Dashboard**: Track consumption logs, hydration levels (ml of water logged), and daily energy/macro progress.

---

## 🛠️ Tech Stack

### Frontend
*   **Framework**: React (Vite-powered, ES Modules)
*   **Styling**: Custom CSS (responsive glassmorphism-inspired components)
*   **Utilities**: `react-select` (for multi-selection search drops), `html2pdf.js` (for PDF exports)

### Backend
*   **Framework**: FastAPI (Python 3.10+)
*   **ORM / Drivers**: SQLAlchemy (using `asyncpg` for async PostgreSQL interactions)
*   **Data Validation**: Pydantic v2
*   **LLM Integration**: Ollama (Client integration for local LLM processing)

### Database
*   **Engine**: PostgreSQL (schema `Twellr_Nutri`)

---

## 📁 Project Structure

```text
Diet-Plan/
├── client/                      # Frontend Application (React + Vite)
│   ├── src/
│   │   ├── features/            # Feature modules (planner, dashboard, admin)
│   │   ├── contexts/           # Profile and Planner Contexts
│   │   ├── App.jsx              # Hash-based routing & base UI layout
│   │   └── styles.css           # Global core styles & design tokens
│   ├── package.json
│   └── vite.config.js
│
├── server/                      # Backend API Service (FastAPI)
│   ├── admin/                   # Admin portal API endpoints & services
│   ├── ai/                      # AI LLM orchestration and chat logic
│   ├── config/                  # Server configuration, loggers, and env settings
│   ├── database/                # DB Session setup, schema models, & ETL pipeline
│   ├── domain/                  # Math formulas, nutrition compilers, scaling & swap engines
│   ├── repositories/            # Data-access layers for DB tables and models
│   ├── services/                # Business logic services (swaps, planner, ranking)
│   ├── studio/                  # Plan Studio endpoint routers
│   ├── app.py                   # Main FastAPI application entry point
│   └── requirements.txt         # Core backend python dependencies
│
├── database/                    # Schema design diagrams and documentations
│   └── nutri_schema_design_v2/
│
├── seed.sh / seed.bat           # Database ETL and seeding pipeline script files
├── apply_migrations.py          # Database column migrations and setups
└── ADMIN_DATA_ENTRY_README.md   # Specific guide for the Admin Portal
```

---

## 🏁 Getting Started

### Prerequisites
1.  **Node.js** (v18+) & **npm**
2.  **Python** (3.10+)
3.  **PostgreSQL** instance running locally or remotely
4.  **Ollama** running locally (e.g., with `gemma3:4b` downloaded)

---

### Step 1: Configure Environment Variables

Create a `.env` file in the root directory by copying the `.env.example` template:

```bash
cp .env.example .env
```

Edit the `.env` file with your PostgreSQL database credentials and Ollama configuration:
```env
DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/<database_name>
NUTRI_OLLAMA_MODEL=gemma3:4b
```

---

### Step 2: Database Setup & Seeding

1.  Create the database in PostgreSQL matching your `DATABASE_URL`.
2.  Run column migrations to prepare database schemas:
    ```bash
    python server/apply_migrations.py
    ```
3.  Seed initial database tables and recipe collections using the ETL pipeline importer:
    *   **Windows**:
        ```cmd
        seed.bat
        ```
    *   **Mac/Linux**:
        ```bash
        chmod +x seed.sh
        ./seed.sh
        ```

---

### Step 3: Run the Backend

1.  Navigate into the `server` folder:
    ```bash
    cd server
    ```
2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Start the FastAPI application development server:
    ```bash
    python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
    ```
    *The API documentation is accessible at: `http://localhost:8000/docs`*

---

### Step 4: Run the Frontend

1.  Navigate into the `client` folder:
    ```bash
    cd ../client
    ```
2.  Install frontend npm packages:
    ```bash
    npm install
    ```
3.  Start the Vite dev server:
    ```bash
    npm run dev
    ```
    *The client application runs at: `http://localhost:5173`*

---

## 🔗 Application Navigation

The client application utilizes hash-based routing. Once the frontend is running, access specific modules via:

*   **Plan Studio**: `http://localhost:5173/#studio`
*   **Dashboard**: `http://localhost:5173/#dashboard`
*   **Admin Portal**: `http://localhost:5173/#admin` (or click the green **📋 Admin Panel** floating button on the bottom right of the Studio interface)

---

## ⚙️ Development & Customizations

*   To modify user target calculation metrics, check [nutrition_formulas.py](file:///e:/IAgami/Bioart/NutriLLM/Code/July/Diet-Plan/server/domain/nutrition_formulas.py).
*   To refine ingredient/meal replacements, check [swap_engine.py](file:///e:/IAgami/Bioart/NutriLLM/Code/July/Diet-Plan/server/domain/swap_engine.py).
*   Detailed administrative database structures and CRUD endpoints can be reviewed in [ADMIN_DATA_ENTRY_README.md](file:///e:/IAgami/Bioart/NutriLLM/Code/July/Diet-Plan/ADMIN_DATA_ENTRY_README.md).
