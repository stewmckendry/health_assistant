#!/usr/bin/env python3
"""
Test script for Dr. OPA OpenAI Agent

Tests the agent with various natural language prompts and records results.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.dr_opa_agent.openai_agent import create_dr_opa_agent

# Test scenarios covering different query types
TEST_SCENARIOS = [
    {
        "category": "CPSO Policy",
        "description": "Testing CPSO regulatory guidance queries",
        "queries": [
            "What are CPSO expectations for virtual care consent documentation?",
            "Can I send lab results to patients via email according to CPSO?",
            "What are the CPSO documentation requirements for prescribing controlled substances?",
            "What does CPSO require for maintaining patient confidentiality?"
        ]
    },
    {
        "category": "Ontario Health Programs", 
        "description": "Testing Ontario Health clinical program queries",
        "queries": [
            "Cervical screening recommendations for a 35-year-old patient",
            "What are the breast cancer screening guidelines for Ontario?",
            "Colorectal screening eligibility and intervals in Ontario",
            "Ontario kidney care programs for patients with diabetes"
        ]
    },
    {
        "category": "Infection Control",
        "description": "Testing PHO IPAC guidance queries",
        "queries": [
            "Infection control requirements for reusable medical devices in office practice",
            "Hand hygiene requirements in clinical settings",
            "PPE requirements for respiratory infections in clinic",
            "Sterilization requirements for surgical instruments in office"
        ]
    },
    {
        "category": "Clinical Tools",
        "description": "Testing CEP clinical decision support tools",
        "queries": [
            "CEP tools for depression assessment and management",
            "Clinical algorithms for chronic pain management",
            "CEP diabetes management tools and calculators",
            "Tools for cardiovascular risk assessment"
        ]
    },
    {
        "category": "General Guidance",
        "description": "Testing general practice guidance queries",
        "queries": [
            "Documentation requirements for telemedicine visits in Ontario",
            "Best practices for managing patient complaints in family practice",
            "Requirements for medical record retention in Ontario",
            "Guidelines for referral management in primary care"
        ]
    }
]

class AgentTester:
    """Test harness for Dr. OPA OpenAI Agent."""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        self.agent = None
    
    async def initialize_agent(self):
        """Initialize the Dr. OPA agent."""
        print("🏥 Initializing Dr. OPA OpenAI Agent...")
        print(f"📅 Test Session: {self.session_id}")
        print("=" * 60)
        
        try:
            self.agent = await create_dr_opa_agent()
            print("✅ Agent initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            return False
    
    async def run_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a test scenario with multiple queries."""
        print(f"\n🔍 Testing Category: {scenario['category']}")
        print(f"📝 Description: {scenario['description']}")
        print("-" * 40)
        
        scenario_results = {
            "category": scenario['category'],
            "description": scenario['description'],
            "timestamp": datetime.now().isoformat(),
            "queries": []
        }
        
        for i, query in enumerate(scenario['queries'], 1):
            print(f"\n📋 Query {i}: {query}")
            print("🤔 Processing...")
            
            start_time = datetime.now()
            
            try:
                response = await self.agent.query(query)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                query_result = {
                    "query": query,
                    "response": response,
                    "success": True,
                    "duration_seconds": duration,
                    "timestamp": start_time.isoformat(),
                    "response_length": len(response)
                }
                
                print(f"✅ Completed in {duration:.2f}s")
                print(f"📄 Response Preview: {response[:200]}...")
                
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                query_result = {
                    "query": query,
                    "response": f"Error: {str(e)}",
                    "success": False,
                    "duration_seconds": duration,
                    "timestamp": start_time.isoformat(),
                    "error": str(e)
                }
                
                print(f"❌ Failed after {duration:.2f}s: {e}")
            
            scenario_results["queries"].append(query_result)
            print("-" * 40)
        
        return scenario_results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test scenarios."""
        if not await self.initialize_agent():
            return {"error": "Failed to initialize agent"}
        
        print(f"\n🚀 Starting comprehensive test suite")
        print(f"📊 Total scenarios: {len(TEST_SCENARIOS)}")
        print(f"📈 Total queries: {sum(len(s['queries']) for s in TEST_SCENARIOS)}")
        
        test_results = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "scenarios": [],
            "summary": {}
        }
        
        for scenario in TEST_SCENARIOS:
            scenario_result = await self.run_test_scenario(scenario)
            test_results["scenarios"].append(scenario_result)
        
        # Calculate summary statistics
        total_queries = sum(len(s["queries"]) for s in test_results["scenarios"])
        successful_queries = sum(1 for s in test_results["scenarios"] 
                               for q in s["queries"] if q["success"])
        total_duration = sum(q["duration_seconds"] for s in test_results["scenarios"] 
                           for q in s["queries"])
        avg_duration = total_duration / total_queries if total_queries > 0 else 0
        
        test_results["summary"] = {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": total_queries - successful_queries,
            "success_rate": successful_queries / total_queries if total_queries > 0 else 0,
            "average_duration_seconds": avg_duration,
            "total_duration_seconds": total_duration
        }
        
        test_results["end_time"] = datetime.now().isoformat()
        
        return test_results
    
    def save_results(self, results: Dict[str, Any]):
        """Save test results to file."""
        # Create test results directory
        results_dir = Path("tests/dr_opa_agent")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed results as JSON
        json_file = results_dir / f"openai_agent_test_results_{self.session_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save summary report as markdown
        md_file = results_dir / f"openai_agent_test_summary_{self.session_id}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_markdown_report(results))
        
        print(f"\n📊 Results saved:")
        print(f"   JSON: {json_file}")
        print(f"   Summary: {md_file}")
    
    def generate_markdown_report(self, results: Dict[str, Any]) -> str:
        """Generate a markdown summary report."""
        summary = results["summary"]
        
        report = f"""# Dr. OPA OpenAI Agent Test Results

**Session ID**: {results["session_id"]}  
**Test Period**: {results["start_time"]} to {results["end_time"]}

## Summary Statistics

- **Total Queries**: {summary["total_queries"]}
- **Successful**: {summary["successful_queries"]} ({summary["success_rate"]:.1%})
- **Failed**: {summary["failed_queries"]}
- **Average Response Time**: {summary["average_duration_seconds"]:.2f} seconds
- **Total Test Duration**: {summary["total_duration_seconds"]:.2f} seconds

## Test Scenarios

"""
        
        for scenario in results["scenarios"]:
            scenario_success = sum(1 for q in scenario["queries"] if q["success"])
            scenario_total = len(scenario["queries"])
            
            report += f"""### {scenario["category"]}

**Description**: {scenario["description"]}  
**Success Rate**: {scenario_success}/{scenario_total} ({scenario_success/scenario_total:.1%})

| Query | Status | Duration | Response Preview |
|-------|--------|----------|------------------|
"""
            
            for query in scenario["queries"]:
                status = "✅ Success" if query["success"] else "❌ Failed"
                duration = f"{query['duration_seconds']:.2f}s"
                preview = query["response"][:100].replace('\n', ' ').replace('|', '\\|') + "..."
                
                report += f"| {query['query'][:50]}... | {status} | {duration} | {preview} |\n"
            
            report += "\n"
        
        report += f"""## Detailed Results

Full detailed results with complete responses are available in: `openai_agent_test_results_{results["session_id"]}.json`

---
*Generated by Dr. OPA Agent Test Suite*
"""
        
        return report
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results."""
        summary = results["summary"]
        
        print(f"\n📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Successful queries: {summary['successful_queries']}/{summary['total_queries']} ({summary['success_rate']:.1%})")
        print(f"⏱️  Average response time: {summary['average_duration_seconds']:.2f} seconds")
        print(f"🕒 Total test duration: {summary['total_duration_seconds']:.2f} seconds")
        
        if summary["failed_queries"] > 0:
            print(f"❌ Failed queries: {summary['failed_queries']}")
            print("\nFailed Query Details:")
            for scenario in results["scenarios"]:
                for query in scenario["queries"]:
                    if not query["success"]:
                        print(f"  - {query['query'][:60]}... → {query.get('error', 'Unknown error')}")


async def run_interactive_test():
    """Run interactive testing mode."""
    print("🏥 Dr. OPA Agent - Interactive Test Mode")
    print("Type your queries or 'quit' to exit")
    print("=" * 60)
    
    agent = await create_dr_opa_agent()
    
    while True:
        try:
            query = input("\n🔍 Your query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            print("🤔 Processing...")
            start_time = datetime.now()
            
            response = await agent.query(query)
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"\n📄 Response ({duration:.2f}s):")
            print("-" * 40)
            print(response)
            print("-" * 40)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main function - choose test mode."""
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        await run_interactive_test()
    else:
        # Run comprehensive test suite
        tester = AgentTester()
        results = await tester.run_all_tests()
        
        if "error" in results:
            print(f"❌ Test suite failed: {results['error']}")
            sys.exit(1)
        
        # Display and save results
        tester.print_summary(results)
        tester.save_results(results)


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())