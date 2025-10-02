"""
Health check endpoint to verify deployment status and available MCP tools.
"""
from fastapi import APIRouter
import subprocess
import json

router = APIRouter()

@router.get("/health/mcp-tools")
async def check_mcp_tools():
    """Check which MCP tools are available in the deployed servers."""
    
    tools_status = {
        "dr_off_tools": [],
        "dr_opa_tools": [],
        "quality_standards_available": False,
        "choosing_wisely_available": False
    }
    
    try:
        # Try to import and check Dr. OPA server
        from src.ai_agents.dr_opa_agent.dr_opa_mcp.server import mcp
        
        # Get registered tools
        for tool_name, tool_info in mcp._tools.items():
            tools_status["dr_opa_tools"].append(tool_name)
            
            if tool_name == "opa_quality_standards":
                tools_status["quality_standards_available"] = True
            elif tool_name == "opa_choosing_wisely":
                tools_status["choosing_wisely_available"] = True
                
    except Exception as e:
        tools_status["error"] = str(e)
    
    # Add summary
    tools_status["summary"] = {
        "total_dr_opa_tools": len(tools_status["dr_opa_tools"]),
        "expected_tools": 9,  # Should be 9 with new tools
        "deployment_status": "OK" if tools_status["quality_standards_available"] else "NEEDS_REBUILD"
    }
    
    return tools_status