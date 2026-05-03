import pytest
from unittest.mock import patch, MagicMock
from app.tools.community_tool import CommunitySearchTool, EscalateToExpertTool

def test_community_search_tool_success():
    tool = CommunitySearchTool()
    with patch('httpx.Client.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"question_text": "How to treat aphids?", "crop_type": "Tomato", "similarity": 0.85}]
        mock_get.return_value = mock_response
        
        result = tool._run("aphids on tomato")
        assert "Found similar past questions" in result
        assert "How to treat aphids?" in result

def test_community_search_tool_no_results():
    tool = CommunitySearchTool()
    with patch('httpx.Client.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        result = tool._run("unknown disease X")
        assert "No similar questions found" in result

def test_escalate_to_expert_tool_success():
    tool = EscalateToExpertTool()
    with patch('httpx.Client.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = tool._run("q_123", 23.8, 90.4)
        assert "Successfully escalated question" in result

def test_escalate_to_expert_tool_failure():
    tool = EscalateToExpertTool()
    with patch('httpx.Client.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        result = tool._run("q_123", 23.8, 90.4)
        assert "Failed to escalate" in result
