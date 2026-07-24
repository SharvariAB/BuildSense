import pytest
import os
from agents.tools import tool_registry

def test_tool_registry_manifest():
    """Test that the tool registry correctly exports a manifest."""
    manifest = tool_registry.get_tool_manifest()
    assert isinstance(manifest, list)
    assert len(manifest) >= 4
    tool_names = [t["name"] for t in manifest]
    assert "get_material_price" in tool_names
    assert "get_weather_advisory" in tool_names
    assert "lookup_nbc_rule" in tool_names
    assert "generate_json_report" in tool_names

def test_material_price_tool():
    """Test the material price lookup tool."""
    result = tool_registry.invoke("get_material_price", material="cement", region="Pune", quantity_units=100)
    assert result["status"] == "success"
    assert result["output"]["unit_price_inr"] > 0
    assert result["output"]["currency"] == "INR"
    assert "Pune" in result["output"]["region"]

def test_nbc_lookup_tool():
    """Test the NBC regulation lookup tool."""
    result = tool_registry.invoke("lookup_nbc_rule", query="corridor width")
    assert result["status"] == "success"
    assert "1.2" in result["output"]["required_value"]
    assert result["output"]["severity"] == "HIGH"

def test_weather_advisory_tool_simulation():
    """Test the weather advisory tool (fallback/simulation if no key)."""
    # Assuming no WEATHER_API_KEY in test environment unless set
    result = tool_registry.invoke("get_weather_advisory", city="Pune")
    assert result["status"] == "success"
    assert "Pune" in result["output"]["city"]
    assert "condition" in result["output"]

def test_tool_registry_audit_log():
    """Test that tool registry captures audit logs."""
    tool_registry.clear_audit_log()
    
    tool_registry.invoke("get_material_price", material="cement", region="Pune", quantity_units=10)
    tool_registry.invoke("lookup_nbc_rule", query="fire exit")
    
    logs = tool_registry.get_session_trace()
    assert len(logs) == 2
    assert logs[0]["tool"] == "get_material_price"
    assert logs[1]["tool"] == "lookup_nbc_rule"
    assert "timestamp" in logs[0]
    assert "duration_ms" in logs[0]

def test_invalid_tool_invocation():
    """Test invoking a non-existent tool."""
    result = tool_registry.invoke("non_existent_tool")
    assert result["status"] == "error"
    assert "not registered" in result["error"]
