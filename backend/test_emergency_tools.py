import pytest
from unittest.mock import patch, MagicMock
from app.tools.emergency_tool import CropDamageAssessmentTool, DamageReportGeneratorTool, SMSShareTool

def test_crop_damage_assessment_tool_mock():
    tool = CropDamageAssessmentTool()
    result = tool._run("fake_image.jpg", "Rice")
    assert "Mock Damage Assessment" in result
    assert "65%" in result

def test_damage_report_generator_tool_success():
    tool = DamageReportGeneratorTool()
    with patch('httpx.Client.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "REP-999-XYZ"}
        mock_post.return_value = mock_response
        
        result = tool._run("farmer_123", 23.8, 90.4, "Rice", 65.0, "My field is flooded.")
        assert "Successfully generated" in result
        assert "REP-999-XYZ" in result

def test_sms_share_tool():
    tool = SMSShareTool()
    result = tool._run("REP-999-XYZ", "+8801712345678")
    assert "SMS successfully sent" in result
    assert "+8801712345678" in result
    assert "REP-999" in result
