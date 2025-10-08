#!/usr/bin/env python3
"""
Unified Test Framework for Doctor Agents (Dr. OPA, Dr. OFF, Agent 97, Chief)

This script provides a comprehensive testing framework for:
1. Agent-level testing (run agents with queries)
2. MCP tool-level testing (call MCP tools directly)
3. Web API testing (test endpoints)

Usage:
    # Test all agents with default test set
    python scripts/test_agents.py

    # Test specific agent
    python scripts/test_agents.py --agent dr_opa

    # Test specific MCP tools
    python scripts/test_agents.py --mode tools --agent dr_off --tools odb_get,adp_get

    # Test with custom queries
    python scripts/test_agents.py --agent dr_opa --queries "CPSO virtual care policy" "CEP tools for diabetes"

    # Test web API
    python scripts/test_agents.py --mode api --agent dr_opa

    # Run all tests
    python scripts/test_agents.py --mode all
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from repo root
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Import test configurations
from tests.agent_test_config import (
    AGENT_CONFIGS,
    DEFAULT_TEST_QUERIES,
    MCP_TOOL_CONFIGS,
    API_CONFIGS
)


class AgentTester:
    """Test framework for agent-level testing."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.agent_config = AGENT_CONFIGS.get(agent_name)
        if not self.agent_config:
            raise ValueError(f"Unknown agent: {agent_name}")

        self.results = []

    async def test_query(self, query: str, expected_tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Test a single query against the agent.

        Args:
            query: Query string
            expected_tools: Optional list of expected tool calls

        Returns:
            Test result dict
        """
        print(f"\n{'='*80}")
        print(f"Testing Query: {query}")
        print(f"{'='*80}\n")

        start_time = datetime.now()

        try:
            # Import agent dynamically
            agent_module = self.agent_config["import_path"]
            create_func = self.agent_config["create_function"]

            # Import the module
            module_parts = agent_module.rsplit(".", 1)
            module = __import__(module_parts[0], fromlist=[module_parts[1]])
            agent_creator = getattr(module, create_func)

            # Create agent
            agent = await agent_creator()

            # Run query
            result = await agent.query(query)

            elapsed = (datetime.now() - start_time).total_seconds()

            # Extract key metrics
            test_result = {
                "query": query,
                "status": "success",
                "elapsed_seconds": elapsed,
                "response": result.get("response", ""),
                "tools_used": result.get("tools_used", []),
                "citations": result.get("citations", []),
                "confidence": result.get("confidence", 0.0),
                "expected_tools": expected_tools,
                "tools_match": self._check_tools_match(result.get("tools_used", []), expected_tools) if expected_tools else None
            }

            # Print summary
            print(f"✓ Success")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"🔧 Tools: {', '.join(result.get('tools_used', ['None']))}")
            print(f"📚 Citations: {len(result.get('citations', []))}")
            print(f"🎯 Confidence: {result.get('confidence', 0.0):.2f}")

            if expected_tools:
                match_status = "✓" if test_result["tools_match"] else "✗"
                print(f"{match_status} Tool Match: Expected {expected_tools}, Got {result.get('tools_used', [])}")

            print(f"\n📄 Response Preview:")
            preview = result.get("response", "")[:300]
            print(f"{preview}{'...' if len(result.get('response', '')) > 300 else ''}\n")

            return test_result

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()

            test_result = {
                "query": query,
                "status": "error",
                "elapsed_seconds": elapsed,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

            print(f"✗ Error: {e}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"\n{traceback.format_exc()}")

            return test_result

    def _check_tools_match(self, actual_tools: List[str], expected_tools: List[str]) -> bool:
        """Check if actual tools match expected tools."""
        if not expected_tools:
            return True

        # Check if any expected tool is in actual tools
        return any(exp in str(actual_tools) for exp in expected_tools)

    async def run_test_suite(self, queries: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run full test suite for this agent.

        Args:
            queries: Optional custom queries. If None, uses default test set.

        Returns:
            Summary of test results
        """
        print(f"\n{'#'*80}")
        print(f"# Agent Test Suite: {self.agent_name.upper()}")
        print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}\n")

        # Use custom queries or default test set
        test_queries = queries or DEFAULT_TEST_QUERIES.get(self.agent_name, [])

        results = []
        for query_config in test_queries:
            if isinstance(query_config, dict):
                query = query_config["query"]
                expected_tools = query_config.get("expected_tools")
            else:
                query = query_config
                expected_tools = None

            result = await self.test_query(query, expected_tools)
            results.append(result)

        # Generate summary
        summary = self._generate_summary(results)

        # Save results
        self._save_results(results, summary)

        return summary

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate test summary."""
        total = len(results)
        successful = len([r for r in results if r["status"] == "success"])
        failed = total - successful

        avg_time = sum(r["elapsed_seconds"] for r in results) / total if total > 0 else 0
        avg_confidence = sum(r.get("confidence", 0) for r in results if r["status"] == "success") / successful if successful > 0 else 0
        total_citations = sum(len(r.get("citations", [])) for r in results if r["status"] == "success")

        tool_matches = [r for r in results if r.get("tools_match") is True]
        tool_match_rate = len(tool_matches) / len([r for r in results if r.get("expected_tools")]) if any(r.get("expected_tools") for r in results) else None

        summary = {
            "agent": self.agent_name,
            "total_tests": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "avg_time_seconds": avg_time,
            "avg_confidence": avg_confidence,
            "total_citations": total_citations,
            "tool_match_rate": tool_match_rate
        }

        print(f"\n{'='*80}")
        print(f"SUMMARY: {self.agent_name.upper()}")
        print(f"{'='*80}")
        print(f"Total Tests: {total}")
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        print(f"Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"Avg Time: {avg_time:.2f}s")
        print(f"Avg Confidence: {avg_confidence:.2f}")
        print(f"Total Citations: {total_citations}")
        if tool_match_rate is not None:
            print(f"Tool Match Rate: {tool_match_rate*100:.1f}%")
        print(f"{'='*80}\n")

        return summary

    def _save_results(self, results: List[Dict[str, Any]], summary: Dict[str, Any]):
        """Save test results to file."""
        output_dir = Path("eval/results/agent_tests")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{self.agent_name}_{timestamp}.json"

        data = {
            "timestamp": timestamp,
            "agent": self.agent_name,
            "summary": summary,
            "results": results
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"📁 Results saved to: {output_file}")


class MCPToolTester:
    """Test framework for MCP tool-level testing."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.tool_configs = MCP_TOOL_CONFIGS.get(agent_name, {})
        if not self.tool_configs:
            raise ValueError(f"No MCP tools configured for agent: {agent_name}")

    async def test_tool(self, tool_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a single MCP tool call.

        Args:
            tool_name: Name of the MCP tool
            request: Tool request parameters

        Returns:
            Test result dict
        """
        print(f"\n{'='*80}")
        print(f"Testing MCP Tool: {tool_name}")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"{'='*80}\n")

        start_time = datetime.now()

        try:
            # Get tool config
            tool_config = self.tool_configs.get(tool_name)
            if not tool_config:
                raise ValueError(f"Unknown tool: {tool_name}")

            # Import tool function dynamically
            tool_module = tool_config["import_path"]
            tool_func_name = tool_config["function_name"]

            module_parts = tool_module.rsplit(".", 1)
            module = __import__(module_parts[0], fromlist=[module_parts[1]])
            tool_func = getattr(module, tool_func_name)

            # Call tool
            result = await tool_func(request)

            elapsed = (datetime.now() - start_time).total_seconds()

            test_result = {
                "tool": tool_name,
                "request": request,
                "status": "success",
                "elapsed_seconds": elapsed,
                "response": result,
                "provenance": result.get("provenance", []),
                "confidence": result.get("confidence", 0.0),
                "citations": result.get("citations", [])
            }

            # Print summary
            print(f"✓ Success")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"📊 Provenance: {result.get('provenance', [])}")
            print(f"🎯 Confidence: {result.get('confidence', 0.0):.2f}")
            print(f"📚 Citations: {len(result.get('citations', []))}")
            print(f"\n📄 Response:")
            print(json.dumps(result, indent=2, default=str)[:500])
            print("...\n" if len(json.dumps(result, default=str)) > 500 else "\n")

            return test_result

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()

            test_result = {
                "tool": tool_name,
                "request": request,
                "status": "error",
                "elapsed_seconds": elapsed,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

            print(f"✗ Error: {e}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"\n{traceback.format_exc()}")

            return test_result

    async def run_tool_suite(self, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run test suite for MCP tools.

        Args:
            tools: Optional list of specific tools to test. If None, tests all.

        Returns:
            Summary of test results
        """
        print(f"\n{'#'*80}")
        print(f"# MCP Tool Test Suite: {self.agent_name.upper()}")
        print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}\n")

        # Determine which tools to test
        tools_to_test = tools or list(self.tool_configs.keys())

        results = []
        for tool_name in tools_to_test:
            if tool_name not in self.tool_configs:
                print(f"⚠️  Warning: Unknown tool {tool_name}, skipping")
                continue

            # Get test requests for this tool
            tool_config = self.tool_configs[tool_name]
            test_requests = tool_config.get("test_requests", [])

            for request in test_requests:
                result = await self.test_tool(tool_name, request)
                results.append(result)

        # Generate summary
        summary = self._generate_summary(results)

        # Save results
        self._save_results(results, summary)

        return summary

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate test summary."""
        total = len(results)
        successful = len([r for r in results if r["status"] == "success"])
        failed = total - successful

        avg_time = sum(r["elapsed_seconds"] for r in results) / total if total > 0 else 0
        avg_confidence = sum(r.get("confidence", 0) for r in results if r["status"] == "success") / successful if successful > 0 else 0

        # Count provenance sources
        sql_count = len([r for r in results if "sql" in r.get("provenance", [])])
        vector_count = len([r for r in results if "vector" in r.get("provenance", [])])

        summary = {
            "agent": self.agent_name,
            "total_tests": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "avg_time_seconds": avg_time,
            "avg_confidence": avg_confidence,
            "sql_sources": sql_count,
            "vector_sources": vector_count
        }

        print(f"\n{'='*80}")
        print(f"SUMMARY: {self.agent_name.upper()} MCP TOOLS")
        print(f"{'='*80}")
        print(f"Total Tests: {total}")
        print(f"✓ Successful: {successful}")
        print(f"✗ Failed: {failed}")
        print(f"Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"Avg Time: {avg_time:.2f}s")
        print(f"Avg Confidence: {avg_confidence:.2f}")
        print(f"SQL Sources: {sql_count}")
        print(f"Vector Sources: {vector_count}")
        print(f"{'='*80}\n")

        return summary

    def _save_results(self, results: List[Dict[str, Any]], summary: Dict[str, Any]):
        """Save test results to file."""
        output_dir = Path("eval/results/mcp_tool_tests")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{self.agent_name}_tools_{timestamp}.json"

        data = {
            "timestamp": timestamp,
            "agent": self.agent_name,
            "summary": summary,
            "results": results
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"📁 Results saved to: {output_file}")


class APITester:
    """Test framework for API endpoint testing."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.api_config = API_CONFIGS.get(agent_name)
        if not self.api_config:
            raise ValueError(f"No API configured for agent: {agent_name}")

    async def test_endpoint(self, query: str) -> Dict[str, Any]:
        """
        Test API endpoint with a query.

        Args:
            query: Query string

        Returns:
            Test result dict
        """
        import aiohttp

        print(f"\n{'='*80}")
        print(f"Testing API: {self.api_config['url']}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")

        start_time = datetime.now()

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"query": query}

                async with session.post(
                    self.api_config["url"],
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()

                    status_code = response.status
                    result = await response.json()

                    test_result = {
                        "query": query,
                        "status": "success" if status_code == 200 else "error",
                        "status_code": status_code,
                        "elapsed_seconds": elapsed,
                        "response": result
                    }

                    print(f"✓ Status: {status_code}")
                    print(f"⏱️  Time: {elapsed:.2f}s")
                    print(f"\n📄 Response Preview:")
                    print(json.dumps(result, indent=2, default=str)[:300])
                    print("...\n" if len(json.dumps(result, default=str)) > 300 else "\n")

                    return test_result

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()

            test_result = {
                "query": query,
                "status": "error",
                "elapsed_seconds": elapsed,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

            print(f"✗ Error: {e}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            print(f"\n{traceback.format_exc()}")

            return test_result

    async def run_api_suite(self, queries: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run API test suite."""
        print(f"\n{'#'*80}")
        print(f"# API Test Suite: {self.agent_name.upper()}")
        print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}\n")

        # Use custom queries or default
        test_queries = queries or DEFAULT_TEST_QUERIES.get(self.agent_name, [])
        if isinstance(test_queries[0], dict):
            test_queries = [q["query"] for q in test_queries]

        results = []
        for query in test_queries[:3]:  # Limit API tests
            result = await self.test_endpoint(query)
            results.append(result)

        # Generate summary
        summary = self._generate_summary(results)

        # Save results
        self._save_results(results, summary)

        return summary

    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary."""
        total = len(results)
        successful = len([r for r in results if r["status"] == "success"])

        summary = {
            "agent": self.agent_name,
            "total_tests": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_time_seconds": sum(r["elapsed_seconds"] for r in results) / total if total > 0 else 0
        }

        print(f"\n{'='*80}")
        print(f"SUMMARY: {self.agent_name.upper()} API")
        print(f"{'='*80}")
        print(f"Total Tests: {total}")
        print(f"✓ Successful: {successful}")
        print(f"Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"Avg Time: {summary['avg_time_seconds']:.2f}s")
        print(f"{'='*80}\n")

        return summary

    def _save_results(self, results: List[Dict[str, Any]], summary: Dict[str, Any]):
        """Save results."""
        output_dir = Path("eval/results/api_tests")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{self.agent_name}_api_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "agent": self.agent_name,
                "summary": summary,
                "results": results
            }, f, indent=2, default=str)

        print(f"📁 Results saved to: {output_file}")


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Unified test framework for doctor agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--agent",
        choices=["dr_opa", "dr_off", "agent_97", "chief", "all"],
        default="all",
        help="Agent to test (default: all)"
    )

    parser.add_argument(
        "--mode",
        choices=["agents", "tools", "api", "all"],
        default="agents",
        help="Test mode (default: agents)"
    )

    parser.add_argument(
        "--tools",
        help="Comma-separated list of specific MCP tools to test"
    )

    parser.add_argument(
        "--queries",
        nargs="+",
        help="Custom queries to test"
    )

    parser.add_argument(
        "--output",
        help="Output file for results (default: auto-generated)"
    )

    args = parser.parse_args()

    # Determine which agents to test
    agents = ["dr_opa", "dr_off", "agent_97", "chief"] if args.agent == "all" else [args.agent]

    # Filter agents that exist in configs
    available_agents = [a for a in agents if a in AGENT_CONFIGS]

    if not available_agents:
        print(f"❌ No valid agents to test")
        return

    print(f"\n{'#'*80}")
    print(f"# Unified Agent Test Framework")
    print(f"# Mode: {args.mode}")
    print(f"# Agents: {', '.join(available_agents)}")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")

    all_summaries = []

    for agent in available_agents:
        try:
            if args.mode in ["agents", "all"]:
                print(f"\n{'='*80}")
                print(f"Testing Agent: {agent.upper()}")
                print(f"{'='*80}\n")

                tester = AgentTester(agent)
                summary = await tester.run_test_suite(args.queries)
                all_summaries.append({"type": "agent", **summary})

            if args.mode in ["tools", "all"] and agent in MCP_TOOL_CONFIGS:
                print(f"\n{'='*80}")
                print(f"Testing MCP Tools: {agent.upper()}")
                print(f"{'='*80}\n")

                tester = MCPToolTester(agent)
                tools_list = args.tools.split(",") if args.tools else None
                summary = await tester.run_tool_suite(tools_list)
                all_summaries.append({"type": "tools", **summary})

            if args.mode in ["api", "all"] and agent in API_CONFIGS:
                print(f"\n{'='*80}")
                print(f"Testing API: {agent.upper()}")
                print(f"{'='*80}\n")

                tester = APITester(agent)
                summary = await tester.run_api_suite(args.queries)
                all_summaries.append({"type": "api", **summary})

        except Exception as e:
            print(f"❌ Error testing {agent}: {e}")
            print(traceback.format_exc())

    # Print overall summary
    print(f"\n{'#'*80}")
    print(f"# OVERALL SUMMARY")
    print(f"{'#'*80}\n")

    for summary in all_summaries:
        print(f"{summary['type'].upper()}: {summary['agent']}")
        print(f"  Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"  Avg Time: {summary.get('avg_time_seconds', 0):.2f}s")
        if "avg_confidence" in summary:
            print(f"  Avg Confidence: {summary['avg_confidence']:.2f}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
