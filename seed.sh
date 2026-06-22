#!/bin/bash
echo "Starting Database Seeding Pipeline..."

cd server || exit 1
export PYTHONPATH="."
python3 database/etl_import.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Seeding complete! Database is ready."
else
    echo ""
    echo "Seeding failed! Check the errors above."
fi
cd ..
