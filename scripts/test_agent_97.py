#!/usr/bin/env python3
"""
Test script for Agent 97
Runs sample queries to verify the agent is working correctly
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv()

from src.agents.agent_97.openai_agent import create_agent_97


# Test queries covering different scenarios
TEST_QUERIES = [
    {
        "category": "General Health Education",
        "query": "What are the symptoms of type 2 diabetes?",
        "expected": ["symptoms", "blood sugar", "Citations"]
    },
    {
        "category": "Medication Information", 
        "query": "What are the common side effects of ibuprofen?",
        "expected": ["NSAIDs", "stomach", "dosage"]
    },
    {
        "category": "Preventive Care",
        "query": "What health screenings should a 50-year-old get?",
        "expected": ["screening", "colonoscopy", "mammogram"]
    },
    {
        "category": "Emergency Detection",
        "query": "I'm having severe chest pain and shortness of breath",
        "expected": ["911", "emergency", "immediate"]
    },
    {
        "category": "Mental Health",
        "query": "How can I manage stress and anxiety?",
        "expected": ["stress", "coping", "professional help"]
    },
    {
        "category": "Source Inquiry",
        "query": "What medical sources do you use for information?",
        "expected": ["97", "trusted", "Mayo Clinic", "CDC"]
    }
]


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_subheader(text: str):
    """Print a formatted subheader"""
    print("\n" + "-"*70)
    print(f"  {text}")
    print("-"*70)


def analyze_response(response: dict, expected_terms: list) -> dict:
    """Analyze response for expected content"""
    analysis = {
        "has_content": bool(response.get('response')),
        "response_length": len(response.get('response', '')),
        "tools_used": response.get('tools_used', []),
        "tool_count": len(response.get('tool_calls', [])),
        "has_error": 'error' in response,
        "expected_terms_found": []
    }
    
    # Check for expected terms
    response_text = response.get('response', '').lower()
    for term in expected_terms:
        if term.lower() in response_text:
            analysis["expected_terms_found"].append(term)
    
    analysis["coverage"] = len(analysis["expected_terms_found"]) / len(expected_terms) if expected_terms else 1.0
    
    return analysis


async def run_tests():
    """Run all test queries"""
    print_header("Agent 97 Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check environment
    print("\n🔧 Environment Check:")
    if os.getenv("OPENAI_API_KEY"):
        print("  ✓ OPENAI_API_KEY configured")
    else:
        print("  ✗ OPENAI_API_KEY missing")
        
    if os.getenv("ANTHROPIC_API_KEY"):
        print("  ✓ ANTHROPIC_API_KEY configured")
    else:
        print("  ✗ ANTHROPIC_API_KEY missing")
        return
    
    # Initialize agent
    print("\n🚀 Initializing Agent 97...")
    try:
        agent = await create_agent_97()
        print("  ✓ Agent initialized successfully")
    except Exception as e:
        print(f"  ✗ Failed to initialize agent: {e}")
        return
    
    # Run test queries
    print_header("Running Test Queries")
    
    results = []
    for i, test in enumerate(TEST_QUERIES, 1):
        print_subheader(f"Test {i}/{len(TEST_QUERIES)}: {test['category']}")
        print(f"Query: {test['query']}")
        
        try:
            # Run query
            start_time = datetime.now()
            response = await agent.query(test['query'])
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Analyze response
            analysis = analyze_response(response, test['expected'])
            
            # Display results
            print(f"\n📊 Results:")
            print(f"  • Response time: {elapsed:.2f}s")
            print(f"  • Response length: {analysis['response_length']} chars")
            print(f"  • Tools used: {', '.join(analysis['tools_used']) if analysis['tools_used'] else 'None'}")
            print(f"  • Expected terms coverage: {analysis['coverage']:.0%}")
            
            if analysis['has_error']:
                print(f"  • ⚠️ Error: {response.get('error')}")
            
            # Show snippet of response
            if analysis['has_content']:
                snippet = response['response'][:300]
                if len(response['response']) > 300:
                    snippet += "..."
                print(f"\n📄 Response snippet:")
                print(f"  {snippet}")
            
            # Check for emergency handling
            if test['category'] == "Emergency Detection":
                if "911" in response.get('response', ''):
                    print("  ✓ Emergency detection working correctly")
                else:
                    print("  ✗ Emergency not properly detected")
            
            # Store result
            results.append({
                "test": test['category'],
                "passed": analysis['coverage'] > 0.5 and not analysis['has_error'],
                "time": elapsed,
                "analysis": analysis
            })
            
        except Exception as e:
            print(f"  ✗ Test failed with error: {e}")
            results.append({
                "test": test['category'],
                "passed": False,
                "error": str(e)
            })
        
        # Small delay between tests
        if i < len(TEST_QUERIES):
            await asyncio.sleep(1)
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for r in results if r.get('passed'))
    total = len(results)
    
    print(f"\n📈 Overall Results:")
    print(f"  • Tests passed: {passed}/{total} ({passed/total:.0%})")
    print(f"  • Average response time: {sum(r.get('time', 0) for r in results)/total:.2f}s")
    
    print(f"\n📋 Individual Results:")
    for result in results:
        status = "✓" if result['passed'] else "✗"
        print(f"  {status} {result['test']}")
        if not result['passed'] and 'error' in result:
            print(f"    Error: {result['error']}")
    
    # Save results to file
    results_file = project_root / "logs" / "agent_97" / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "tests_run": total,
            "tests_passed": passed,
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Final status
    if passed == total:
        print("\n✅ All tests passed! Agent 97 is working correctly.")
    elif passed > 0:
        print(f"\n⚠️ {passed}/{total} tests passed. Review failures above.")
    else:
        print("\n❌ All tests failed. Check configuration and logs.")


async def run_interactive():
    """Run interactive query mode"""
    print_header("Agent 97 Interactive Mode")
    print("Type 'quit' to exit, 'help' for commands")
    
    # Initialize agent
    print("\n🚀 Initializing Agent 97...")
    try:
        agent = await create_agent_97()
        print("✓ Agent ready for queries")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return
    
    while True:
        try:
            # Get user input
            print("\n" + "="*70)
            query = input("Your question: ").strip()
            
            # Check for commands
            if query.lower() == 'quit':
                break
            elif query.lower() == 'help':
                print("\nCommands:")
                print("  quit - Exit the program")
                print("  help - Show this message")
                print("  test - Run test suite")
                continue
            elif query.lower() == 'test':
                await run_tests()
                continue
            elif not query:
                continue
            
            # Process query
            print("\n🔍 Processing...")
            start_time = datetime.now()
            response = await agent.query(query)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Display response
            print(f"\n📄 Response ({elapsed:.2f}s):")
            print("-"*70)
            print(response['response'])
            
            # Show tool usage
            if response.get('tools_used'):
                print(f"\n🔧 Tools used: {', '.join(response['tools_used'])}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print("\n👋 Goodbye!")


async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            await run_tests()
        elif sys.argv[1] == '--interactive':
            await run_interactive()
        else:
            print("Usage: python test_agent_97.py [--test|--interactive]")
    else:
        # Default to test mode
        await run_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)