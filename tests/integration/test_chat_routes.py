import pytest
from unittest.mock import patch

def test_chat_endpoint(client):
    req_body = {
        "message": "Hello",
        "history": [],
        "agentName": "Default Agent",
        "context": {}
    }
    
    with patch("studio.chat.process_chat_message") as mock_process:
        mock_process.return_value = {
            "reply": "Hello! I am your AI nutrition companion.",
            "preferences": None,
            "quickReplies": [{"text": "Help me plan a meal"}, {"text": "Explain calories"}],
            "action": None
        }
        
        res = client.post("/api/chat", json=req_body)
        assert res.status_code == 200
        data = res.json()
        assert data["reply"] == "Hello! I am your AI nutrition companion."
        assert len(data["quickReplies"]) == 2
