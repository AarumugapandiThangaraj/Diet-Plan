import pytest
from unittest.mock import patch
from database.session import AsyncSessionLocal
from database.models.substitute import Substitute
from repositories.substitute_repository import SubstituteRepository, normalize_key, extract_ingredient_name
from domain.substitutes import suggest_for_ingredients_text, build_substitute_index

def test_normalization_and_extraction():
    assert normalize_key("Almond Milk") == "almond milk"
    assert normalize_key("Wheat (whole)") == "wheat whole"
    
    assert extract_ingredient_name("Milk 200ml") == "Milk 200ml"
    assert extract_ingredient_name("Almond (soaked)") == "Almond"

def test_suggest_for_ingredients_text_with_mocked_cache():
    repo = SubstituteRepository()
    repo.names_by_norm = {
        "milk": "Milk",
        "lactose free milk": "Lactose-free milk",
        "soy milk": "Soy milk"
    }
    repo.details_by_norm = {
        "lactose free milk": {"name": "Lactose-free milk", "energy_kcal": "66"},
        "soy milk": {"name": "Soy milk", "energy_kcal": "45"}
    }
    repo.neighbors_by_norm = {
        "milk": {"lactose free milk", "soy milk"},
        "lactose free milk": {"milk"},
        "soy milk": {"milk"}
    }
    repo.initialized = True
    
    with patch("domain.substitutes.substitute_repository", repo):
        res = suggest_for_ingredients_text("milk, unknown_ingredient")
        
        # Should have found 1 choice (milk)
        assert len(res["choices"]) == 1
        assert res["choices"][0]["key"] == "milk"
        assert res["choices"][0]["label"] == "Milk"
        
        # Should have substitutes for 'milk'
        subs = res["substitutesByKey"]["milk"]
        assert len(subs) == 2
        assert any(s["norm"] == "soy milk" for s in subs)
        assert any(s["norm"] == "lactose free milk" for s in subs)

@pytest.mark.anyio
async def test_repository_refresh_cache():
    # Insert mock records directly into our in-memory SQLite database
    async with AsyncSessionLocal() as session:
        sub = Substitute(
            id="SUB_1",
            allergen_category="dairy",
            allergen_name="milk",
            substitutes=[
                {"name": "Lactose-free milk", "energy_kcal": "66"},
                {"name": "Soy milk", "energy_kcal": "45"}
            ]
        )
        session.add(sub)
        await session.commit()
        
    repo = SubstituteRepository()
    await repo.refresh_cache()
    
    assert repo.initialized is True
    assert "milk" in repo.neighbors_by_norm
    assert repo.names_by_norm["soy milk"] == "Soy milk"
    assert repo.details_by_norm["lactose free milk"]["energy_kcal"] == "66"
