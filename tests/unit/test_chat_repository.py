import pytest
from repositories.chat_repository import load_preferences, save_preferences

def test_chat_repository_save_and_load():
    # Save test preferences
    test_prefs = {
        "likes": ["apple", "banana"],
        "dislikes": ["onion"],
        "allergies": ["peanut"],
        "notes": ["prefers organic foods"]
    }
    
    save_preferences(test_prefs)
    
    # Load them back and verify
    loaded = load_preferences()
    assert loaded["likes"] == ["apple", "banana"]
    assert loaded["dislikes"] == ["onion"]
    assert loaded["allergies"] == ["peanut"]
    assert loaded["notes"] == ["prefers organic foods"]
