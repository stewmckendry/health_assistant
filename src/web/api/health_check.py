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
        
        # FastMCP stores tools differently
        # Try to get tool list through the tool decorator registry
        tool_names = []
        
        # Check if tools were registered via decorator
        try:
            # FastMCP may store tools in different ways
            if hasattr(mcp, 'list_tools'):
                tools_list = mcp.list_tools()
                for tool in tools_list:
                    tool_names.append(tool.name)
            elif hasattr(mcp, 'tools'):
                tool_names = list(mcp.tools.keys())
            else:
                # Fallback: check for decorated functions in the module
                from src.ai_agents.dr_opa_agent.dr_opa_mcp import server
                for attr_name in dir(server):
                    if attr_name.startswith('opa_') or attr_name.endswith('_handler'):
                        tool_names.append(attr_name.replace('_handler', ''))
        except Exception as e:
            tools_status["tools_error"] = str(e)
        
        tools_status["dr_opa_tools"] = tool_names
        
        # Check for our specific tools
        for tool_name in tool_names:
            if "quality_standards" in tool_name:
                tools_status["quality_standards_available"] = True
            elif "choosing_wisely" in tool_name:
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