#!/usr/bin/env python3
"""Performance test script to measure query response times."""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# Load from current directory .env file
load_dotenv()

from src.assistants.patient import PatientAssistant
from src.config.settings import settings

def test_query_performance(query: str, run_name: str = "baseline"):
    """Test a single query and measure response time."""
    
    print(f"\n{'='*60}")
    print(f"Testing: {query}")
    print(f"Run: {run_name}")
    print(f"{'='*60}")
    
    # Initialize assistant
    assistant = PatientAssistant()
    
    # Measure time
    start_time = time.time()
    
    try:
        response = assistant.query(query)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Count citations and tool calls
        citations_count = len(response.get("citations", []))
        tool_calls_count = len(response.get("tool_calls", []))
        
        print(f"✓ Response received in {elapsed:.2f} seconds")
        print(f"  - Citations: {citations_count}")
        print(f"  - Tool calls: {tool_calls_count}")
        print(f"  - Model: {response.get('model', 'unknown')}")
        print(f"  - Input tokens: {response.get('usage', {}).get('input_tokens', 0)}")
        print(f"  - Output tokens: {response.get('usage', {}).get('output_tokens', 0)}")
        
        # Log to file for tracking
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "run_name": run_name,
            "query": query,
            "elapsed_seconds": elapsed,
            "citations": citations_count,
            "tool_calls": tool_calls_count,
            "model": response.get("model"),
            "usage": response.get("usage", {}),
            "trace_id": response.get("trace_id")
        }
        
        # Save to performance log
        log_file = Path(__file__).parent.parent / "logs" / "performance_tests.jsonl"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return elapsed, response
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None, None

def run_performance_suite(run_name: str = "baseline"):
    """Run a suite of performance tests."""
    
    test_queries = [
        "What are the symptoms of flu?",
        "How to manage type 2 diabetes?",
        "What are signs of a heart attack?",
    ]
    
    print(f"\n{'#'*60}")
    print(f"Performance Test Suite - {run_name}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'#'*60}")
    
    results = []
    total_time = 0
    
    for query in test_queries:
        elapsed, response = test_query_performance(query, run_name)
        if elapsed:
            results.append(elapsed)
            total_time += elapsed
            
            # Wait a bit between queries to avoid rate limiting
            time.sleep(2)
    
    if results:
        avg_time = sum(results) / len(results)
        print(f"\n{'='*60}")
        print(f"SUMMARY - {run_name}")
        print(f"{'='*60}")
        print(f"Queries tested: {len(results)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time: {avg_time:.2f}s")
        print(f"Min time: {min(results):.2f}s")
        print(f"Max time: {max(results):.2f}s")
        
        if avg_time < 5:
            print(f"✓ PASS: Average response time < 5s")
        else:
            print(f"✗ FAIL: Average response time >= 5s")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test assistant performance")
    parser.add_argument("--run-name", default="baseline", help="Name for this test run")
    parser.add_argument("--query", help="Test a single query")
    
    args = parser.parse_args()
    
    if args.query:
        test_query_performance(args.query, args.run_name)
    else:
        run_performance_suite(args.run_name)