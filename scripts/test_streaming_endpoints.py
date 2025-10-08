"""
Test script for agent streaming endpoints.
Tests Dr. OFF, Dr. OPA, and Chief orchestrator endpoints.
Validates response structure includes: content, citations, tools, and UI-required fields.
"""

import requests
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 120  # 2 minutes for streaming responses

# Test queries for each agent
TEST_QUERIES = {
    "dr_off": "What is the OHIP billing code for a comprehensive medical assessment?",
    "dr_opa": "What are the CPSO guidelines for prescribing controlled substances?",
    "chief": "Can I bill OHIP for a telephone consultation and what are the guidelines?"
}


class StreamingTestResult:
    """Container for test results."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.success = False
        self.error_message = None
        self.events_received = []
        self.has_text = False
        self.has_citations = False
        self.has_tools = False
        self.has_trace_id = False
        self.response_text = ""
        self.citations = []
        self.tool_calls = []
        self.trace_id = None
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "agent": self.agent_name,
            "success": self.success,
            "error_message": self.error_message,
            "events_count": len(self.events_received),
            "event_types": list(set(e.get("type") for e in self.events_received)),
            "has_text": self.has_text,
            "has_citations": self.has_citations,
            "has_tools": self.has_tools,
            "has_trace_id": self.has_trace_id,
            "response_length": len(self.response_text),
            "citations_count": len(self.citations),
            "tools_count": len(self.tool_calls),
            "trace_id": self.trace_id,
            "sample_text": self.response_text[:200] if self.response_text else None,
            "sample_citations": self.citations[:2] if self.citations else [],
            "sample_tools": self.tool_calls[:2] if self.tool_calls else []
        }


def test_streaming_endpoint(endpoint: str, query: str, agent_name: str) -> StreamingTestResult:
    """
    Test a streaming endpoint and validate response structure.

    Args:
        endpoint: API endpoint path (e.g., "/agents/dr-off/stream")
        query: Test query to send
        agent_name: Name of agent for reporting

    Returns:
        StreamingTestResult with validation results
    """
    result = StreamingTestResult(agent_name)
    session_id = str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"Testing {agent_name} - {endpoint}")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Session ID: {session_id}")

    try:
        # Prepare request
        url = f"{BASE_URL}{endpoint}"
        payload = {
            "sessionId": session_id,
            "query": query,
            "stream": True,
            "userId": "test_user"
        }

        print(f"Sending request to: {url}")

        # Make streaming request
        response = requests.post(
            url,
            json=payload,
            stream=True,
            timeout=TIMEOUT,
            headers={"Accept": "text/event-stream"}
        )

        print(f"Response status: {response.status_code}")

        if response.status_code != 200:
            result.error_message = f"HTTP {response.status_code}: {response.text}"
            print(f"❌ Error: {result.error_message}")
            return result

        # Process streaming events
        event_count = 0
        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')

            # Skip non-data lines
            if not line.startswith('data: '):
                continue

            # Parse event data
            data_str = line[6:]  # Remove 'data: ' prefix

            # Skip [DONE] marker
            if data_str.strip() == '[DONE]':
                print("Received [DONE] marker")
                continue

            try:
                event = json.loads(data_str)
                result.events_received.append(event)
                event_count += 1
                event_type = event.get("type", "unknown")

                # Print event info
                if event_count % 10 == 0:  # Print every 10th event to reduce noise
                    print(f"  Received {event_count} events...")

                # Process different event types
                if event_type == "text":
                    result.has_text = True
                    delta = event.get("data", {}).get("delta", "")
                    result.response_text += delta

                elif event_type == "citation":
                    result.has_citations = True
                    citation_data = event.get("data", {})
                    result.citations.append(citation_data)
                    print(f"  ✓ Citation: {citation_data.get('title', 'N/A')}")

                elif event_type in ["tool_call_start", "tool_use"]:
                    result.has_tools = True
                    tool_data = event.get("data", {})
                    tool_name = tool_data.get("name", "unknown")
                    result.tool_calls.append(tool_data)
                    print(f"  ✓ Tool: {tool_name}")

                elif event_type in ["response_done", "complete", "done"]:
                    # Check for trace_id in different locations
                    trace_id = (
                        event.get("data", {}).get("traceId") or
                        event.get("data", {}).get("trace_id") or
                        event.get("traceId") or
                        event.get("trace_id")
                    )
                    if trace_id:
                        result.has_trace_id = True
                        result.trace_id = trace_id
                        print(f"  ✓ Trace ID: {trace_id}")

                    # Store metadata
                    result.metadata = event.get("data", {})
                    print(f"  ✓ Complete event received")

                elif event_type == "error":
                    error_msg = event.get("data", {}).get("message") or event.get("data", {}).get("error")
                    result.error_message = error_msg
                    print(f"  ❌ Error event: {error_msg}")

            except json.JSONDecodeError as e:
                print(f"  ⚠️  Failed to parse event: {data_str[:100]}")
                continue

        # Final validation
        print(f"\nValidation Results:")
        print(f"  Events received: {event_count}")
        print(f"  Text content: {'✓' if result.has_text else '✗'} ({len(result.response_text)} chars)")
        print(f"  Citations: {'✓' if result.has_citations else '✗'} ({len(result.citations)} found)")
        print(f"  Tool calls: {'✓' if result.has_tools else '✗'} ({len(result.tool_calls)} found)")
        print(f"  Trace ID: {'✓' if result.has_trace_id else '✗'} ({result.trace_id or 'None'})")

        # Mark as success if we have required fields
        result.success = (
            result.has_text and
            len(result.response_text) > 0 and
            event_count > 0
        )

        if result.success:
            print(f"\n✅ {agent_name} test PASSED")
        else:
            print(f"\n❌ {agent_name} test FAILED")
            if not result.has_text:
                print("   Missing: text content")
            if len(result.response_text) == 0:
                print("   Missing: response text")

    except requests.exceptions.Timeout:
        result.error_message = f"Request timed out after {TIMEOUT}s"
        print(f"❌ Timeout: {result.error_message}")

    except Exception as e:
        result.error_message = str(e)
        print(f"❌ Exception: {result.error_message}")

    return result


def generate_report(results: List[StreamingTestResult]) -> Dict[str, Any]:
    """Generate a comprehensive test report."""

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success)
        },
        "results": [r.to_dict() for r in results]
    }

    return report


def main():
    """Run all streaming endpoint tests."""

    print("="*60)
    print("Agent Streaming Endpoints Test Suite")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Test endpoints
    endpoints = [
        ("/agents/dr-off/stream", TEST_QUERIES["dr_off"], "Dr. OFF"),
        ("/agents/dr-opa/stream", TEST_QUERIES["dr_opa"], "Dr. OPA"),  # Fixed: was /api/agents/dr-opa/stream
        ("/agents/orchestrator/stream", TEST_QUERIES["chief"], "Chief")
    ]

    results = []

    for endpoint, query, agent_name in endpoints:
        result = test_streaming_endpoint(endpoint, query, agent_name)
        results.append(result)

    # Generate and display report
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    report = generate_report(results)

    print(f"\nTotal Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")

    print("\n" + "-"*60)
    print("DETAILED RESULTS")
    print("-"*60)

    for result_dict in report['results']:
        status = "✅ PASS" if result_dict['success'] else "❌ FAIL"
        print(f"\n{status} - {result_dict['agent']}")
        print(f"  Events: {result_dict['events_count']}")
        print(f"  Event types: {', '.join(result_dict['event_types'])}")
        print(f"  Text: {'✓' if result_dict['has_text'] else '✗'} ({result_dict['response_length']} chars)")
        print(f"  Citations: {'✓' if result_dict['has_citations'] else '✗'} ({result_dict['citations_count']})")
        print(f"  Tools: {'✓' if result_dict['has_tools'] else '✗'} ({result_dict['tools_count']})")
        print(f"  Trace ID: {'✓' if result_dict['has_trace_id'] else '✗'}")

        if result_dict['error_message']:
            print(f"  Error: {result_dict['error_message']}")

        if result_dict['sample_text']:
            print(f"  Sample text: {result_dict['sample_text'][:100]}...")

    # Save report to file
    report_path = f"/Users/liammckendry/health_assistant_retrieval_improvements/eval/results/agent_streaming_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {report_path}")

    # Exit with appropriate code
    exit_code = 0 if report['summary']['failed'] == 0 else 1
    print(f"\nExit code: {exit_code}")

    return exit_code


if __name__ == "__main__":
    exit(main())
