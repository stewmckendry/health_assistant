#!/usr/bin/env python3
"""
Direct MCP Tool Testing Script

Test individual MCP tools directly without going through the agent layer.
This is useful for debugging retrieval issues and testing tool responses.

Usage:
    # Test Dr. OFF ODB tool
    python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "atorvastatin coverage"

    # Test Dr. OFF ADP tool with structured request
    python scripts/test_mcp_tools_direct.py --agent dr_off --tool adp_get --device "power wheelchair" --category mobility

    # Test Dr. OPA policy check
    python scripts/test_mcp_tools_direct.py --agent dr_opa --tool opa_policy_check --query "virtual care consent"

    # Run all test cases for a tool
    python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --run-all-tests
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from repo root
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def test_dr_off_tool(tool_name: str, request: Dict[str, Any]):
    """Test Dr. OFF MCP tool."""
    if tool_name == "schedule_get":
        from src.ai_agents.dr_off_agent.mcp.tools.schedule import schedule_get
        return await schedule_get(request)
    elif tool_name == "odb_get":
        from src.ai_agents.dr_off_agent.mcp.tools.odb import odb_get
        return await odb_get(request)
    elif tool_name == "adp_get":
        from src.ai_agents.dr_off_agent.mcp.tools.adp import adp_get
        return await adp_get(request)
    else:
        raise ValueError(f"Unknown Dr. OFF tool: {tool_name}")


async def test_dr_opa_tool(tool_name: str, request: Dict[str, Any]):
    """Test Dr. OPA MCP tool."""
    # Import the server module dynamically to get handler functions
    from src.ai_agents.dr_opa_agent.dr_opa_mcp import server

    # Map tool names to handler function names
    tool_handler_names = {
        "opa_policy_check": "policy_check_handler",
        "opa_clinical_tools": "clinical_tools_handler",
        "opa_quality_standards": "quality_standards_handler",
        "opa_choosing_wisely": "choosing_wisely_handler",
        "opa_ipac_guidance": "ipac_guidance_handler",
        "opa_program_lookup": "program_lookup_handler"
    }

    handler_name = tool_handler_names.get(tool_name)
    if not handler_name:
        raise ValueError(f"Unknown Dr. OPA tool: {tool_name}")

    # Get the actual handler function from the module
    handler = getattr(server, handler_name)

    # If it's a FunctionTool (from @mcp.tool decorator), get the wrapped function
    if hasattr(handler, 'fn'):
        handler = handler.fn
    elif not callable(handler):
        raise ValueError(f"Handler {handler_name} is not callable and has no 'fn' attribute")

    # Call the handler with parameters
    query = request.get("query", "")
    k = request.get("k", 5)
    filters = request.get("filters", {})

    return await handler(query=query, k=k, filters=filters)


async def test_agent_97_tool(tool_name: str, request: Dict[str, Any]):
    """Test Agent 97 MCP tool."""
    # Import the server module dynamically to get handler functions
    from src.ai_agents.agent_97.mcp import clinician_search_server as server

    # Map tool names to handler function names
    tool_handler_names = {
        "clinician_search": "clinician_search_handler",
        "clinician_search_get_domains": "clinician_search_get_domains_handler",
        "clinician_search_health_check": "clinician_search_health_check_handler"
    }

    handler_name = tool_handler_names.get(tool_name)
    if not handler_name:
        raise ValueError(f"Unknown Agent 97 tool: {tool_name}")

    # Get the actual handler function from the module
    handler = getattr(server, handler_name)

    # If it's a FunctionTool (from @mcp.tool decorator), get the wrapped function
    if hasattr(handler, 'fn'):
        handler = handler.fn
    elif not callable(handler):
        raise ValueError(f"Handler {handler_name} is not callable and has no 'fn' attribute")

    # Call the handler with parameters based on tool
    if tool_name == "clinician_search":
        query = request.get("query", "")
        session_id = request.get("session_id")
        user_id = request.get("user_id")
        max_web_search_uses = request.get("max_web_search_uses", 2)
        max_web_fetch_uses = request.get("max_web_fetch_uses", 5)

        return await handler(
            query=query,
            session_id=session_id,
            user_id=user_id,
            max_web_search_uses=max_web_search_uses,
            max_web_fetch_uses=max_web_fetch_uses
        )
    elif tool_name == "clinician_search_get_domains":
        include_categories = request.get("include_categories", False)
        return await handler(include_categories=include_categories)
    elif tool_name == "clinician_search_health_check":
        return await handler()


async def main():
    parser = argparse.ArgumentParser(
        description="Direct MCP tool testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--agent",
        required=True,
        choices=["dr_off", "dr_opa", "agent_97"],
        help="Agent to test"
    )

    parser.add_argument(
        "--tool",
        required=True,
        help="Tool name (e.g., odb_get, adp_get, schedule_get, opa_policy_check, clinician_search)"
    )

    parser.add_argument(
        "--query",
        help="Query string"
    )

    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results (default: 5)"
    )

    # Dr. OFF specific arguments
    parser.add_argument(
        "--device",
        help="Device name (for ADP queries)"
    )

    parser.add_argument(
        "--category",
        help="Device category (for ADP queries)"
    )

    parser.add_argument(
        "--patient-income",
        type=float,
        help="Patient income (for ADP CEP checks)"
    )

    parser.add_argument(
        "--drug",
        help="Drug name (for ODB queries)"
    )

    parser.add_argument(
        "--din",
        help="DIN number (for ODB queries)"
    )

    # General arguments
    parser.add_argument(
        "--filters",
        help="JSON string of filters"
    )

    parser.add_argument(
        "--run-all-tests",
        action="store_true",
        help="Run all predefined test cases for the tool"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output"
    )

    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"MCP Tool Direct Test")
    print(f"Agent: {args.agent}")
    print(f"Tool: {args.tool}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # Build request based on arguments
    if args.run_all_tests:
        # Load test cases from config
        from tests.agent_test_config import MCP_TOOL_CONFIGS

        tool_config = MCP_TOOL_CONFIGS.get(args.agent, {}).get(args.tool)
        if not tool_config:
            print(f"❌ No test cases configured for {args.agent}/{args.tool}")
            return

        test_requests = tool_config.get("test_requests", [])
        print(f"Running {len(test_requests)} test cases...\n")

        results = []
        for i, request in enumerate(test_requests, 1):
            print(f"\n{'='*80}")
            print(f"Test Case {i}/{len(test_requests)}")
            print(f"Request: {json.dumps(request, indent=2)}")
            print(f"{'='*80}\n")

            start_time = datetime.now()

            try:
                if args.agent == "dr_off":
                    result = await test_dr_off_tool(args.tool, request)
                elif args.agent == "dr_opa":
                    result = await test_dr_opa_tool(args.tool, request)
                elif args.agent == "agent_97":
                    result = await test_agent_97_tool(args.tool, request)

                elapsed = (datetime.now() - start_time).total_seconds()

                print(f"✓ Success")
                print(f"⏱️  Time: {elapsed:.2f}s")
                print(f"📊 Provenance: {result.get('provenance', [])}")
                print(f"🎯 Confidence: {result.get('confidence', 0.0):.2f}")
                print(f"📚 Citations: {len(result.get('citations', []))}")

                if args.verbose:
                    print(f"\n📄 Full Response:")
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(f"\n📄 Response Preview:")
                    print(json.dumps(result, indent=2, default=str)[:500])
                    print("...")

                results.append({
                    "request": request,
                    "status": "success",
                    "elapsed": elapsed,
                    "result": result
                })

            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()

                print(f"✗ Error: {e}")
                print(f"⏱️  Time: {elapsed:.2f}s")
                print(f"\n{traceback.format_exc()}")

                results.append({
                    "request": request,
                    "status": "error",
                    "elapsed": elapsed,
                    "error": str(e)
                })

        # Print summary
        successful = len([r for r in results if r["status"] == "success"])
        print(f"\n{'='*80}")
        print(f"Summary: {successful}/{len(results)} tests passed")
        print(f"{'='*80}\n")

        # Save results
        output_dir = Path("eval/results/mcp_tool_tests")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{args.agent}_{args.tool}_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "agent": args.agent,
                "tool": args.tool,
                "results": results
            }, f, indent=2, default=str)

        print(f"📁 Results saved to: {output_file}")

    else:
        # Single test with custom parameters
        request = {
            "query": args.query or "",
            "k": args.k,
            "filters": {}
        }

        # Parse filters from JSON if provided
        if args.filters:
            try:
                request["filters"] = json.loads(args.filters)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in --filters: {e}")
                return

        # Build tool-specific request
        if args.tool == "adp_get":
            if args.device:
                request["filters"]["device"] = {
                    "type": args.device,
                    "category": args.category or "mobility"
                }
            if args.patient_income:
                request["filters"]["patient_income"] = args.patient_income

        elif args.tool == "odb_get":
            if args.drug:
                request["filters"]["drug"] = args.drug
            if args.din:
                request["filters"]["din"] = args.din

        print(f"Request:")
        print(json.dumps(request, indent=2))
        print()

        start_time = datetime.now()

        try:
            if args.agent == "dr_off":
                result = await test_dr_off_tool(args.tool, request)
            elif args.agent == "dr_opa":
                result = await test_dr_opa_tool(args.tool, request)
            elif args.agent == "agent_97":
                result = await test_agent_97_tool(args.tool, request)

            elapsed = (datetime.now() - start_time).total_seconds()

            print(f"\n✓ Success")
            print(f"⏱️  Time: {elapsed:.2f}s")

            # Only show provenance/confidence for tools that return them
            if 'provenance' in result:
                print(f"📊 Provenance: {result.get('provenance', [])}")
            if 'confidence' in result:
                print(f"🎯 Confidence: {result.get('confidence', 0.0):.2f}")
            if 'citations' in result:
                print(f"📚 Citations: {len(result.get('citations', []))}")

            if args.verbose or True:  # Always show full response for single tests
                print(f"\n📄 Full Response:")
                print(json.dumps(result, indent=2, default=str))

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()

            print(f"\n✗ Error: {e}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"\n{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())
