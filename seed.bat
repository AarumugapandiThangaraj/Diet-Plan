@echo off
echo Starting Database Seeding Pipeline...

cd server
set PYTHONPATH=.
python database\etl_import.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo Seeding complete! Database is ready.
) else (
    echo.
    echo Seeding failed! Check the errors above.
)
cd ..
