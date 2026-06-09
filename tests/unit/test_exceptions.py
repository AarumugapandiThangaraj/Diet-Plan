import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from exceptions.handlers import register_global_handlers
from exceptions.base import ValidationException, ResourceNotFoundException
from exceptions.service import DatabaseException
from exceptions.domain import NutritionCalculationException

@pytest.fixture
def error_client():
    app = FastAPI()
    register_global_handlers(app)
    
    @app.get("/raise/validation")
    def raise_validation():
        raise ValidationException("Validation failed")
        
    @app.get("/raise/not-found")
    def raise_not_found():
        raise ResourceNotFoundException("Item not found")
        
    @app.get("/raise/database")
    def raise_database():
        raise DatabaseException("DB error")
        
    @app.get("/raise/nutrition")
    def raise_nutrition():
        raise NutritionCalculationException("Nutrition error")
        
    @app.get("/raise/http")
    def raise_http():
        raise HTTPException(status_code=400, detail="HTTP Bad Request")

    return TestClient(app)

def test_validation_exception(error_client):
    res = error_client.get("/raise/validation")
    assert res.status_code == 400
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "Validation failed" in data["error"]["message"]

def test_resource_not_found_exception(error_client):
    res = error_client.get("/raise/not-found")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"

def test_database_exception(error_client):
    res = error_client.get("/raise/database")
    assert res.status_code == 500
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DATABASE_ERROR"

def test_nutrition_exception(error_client):
    res = error_client.get("/raise/nutrition")
    assert res.status_code == 400
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NUTRITION_CALCULATION_ERROR"
