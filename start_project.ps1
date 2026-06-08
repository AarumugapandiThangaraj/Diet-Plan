# Start Frontend
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PSScriptRoot\frontend'; npm run dev"
)

# Start Backend
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& '$PSScriptRoot\backend\.venv\Scripts\Activate.ps1'; cd '$PSScriptRoot\backend'; python -m uvicorn app:app --reload --port 8000"
)