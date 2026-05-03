import pytest
from unittest.mock import patch, MagicMock
from app.tools.marketplace_tool import DealerSearchTool, ProductVerificationTool, LabelScannerTool

def test_dealer_search_tool_success():
    tool = DealerSearchTool()
    with patch('httpx.Client.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "Rahim Fertilizers", "distance": "1.2km", "phone_number": "017XX"}]
        mock_get.return_value = mock_response
        
        result = tool._run("urea", 23.8, 90.4)
        assert "Rahim Fertilizers" in result
        assert "1.2km" in result

def test_product_verification_tool_green():
    tool = ProductVerificationTool()
    with patch('httpx.Client.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"verification_status": "verified", "product_name": "Premium Urea"}
        mock_post.return_value = mock_response
        
        result = tool._run("123456789")
        assert "STATUS GREEN" in result
        assert "Premium Urea" in result

def test_product_verification_tool_red():
    tool = ProductVerificationTool()
    with patch('httpx.Client.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"verification_status": "counterfeit"}
        mock_post.return_value = mock_response
        
        result = tool._run("99999999")
        assert "STATUS RED" in result

def test_label_scanner_tool_mock():
    tool = LabelScannerTool()
    # Without image, it should fallback
    result = tool._run("nonexistent_path.jpg")
    assert "Mock" in result or "fallback" in result.lower()
