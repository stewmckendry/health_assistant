#!/usr/bin/env python
"""Quick test script to verify Langfuse evaluator setup."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.evaluation.evaluator import DatasetEvaluator


def test_safety_compliance_evaluator():
    """Test run with 3 items to verify Safety Compliance evaluator is working."""
    
    print("\n" + "="*60)
    print("🧪 TESTING SAFETY COMPLIANCE EVALUATOR")
    print("="*60)
    print("\nThis will:")
    print("1. Run evaluation on 3 test items")
    print("2. Trigger the Safety Compliance evaluator in Langfuse")
    print("3. Wait for results and display scores")
    print("-"*60)
    
    # Initialize evaluator
    evaluator = DatasetEvaluator()
    
    # Run evaluation on just 3 items
    print("\n📊 Starting evaluation run...")
    results = evaluator.run_dataset_evaluation(
        dataset_name="health-assistant-eval-v1",
        run_name=f"test_safety_compliance",
        limit=3,  # Just 3 items for quick test
        description="Testing Safety Compliance evaluator setup"
    )
    
    if results.get("successful", 0) > 0:
        print("\n✅ Dataset run completed successfully!")
        print(f"   Run Name: {results['run_name']}")
        print(f"   Dashboard: {results['dashboard_url']}")
        
        # Wait a bit for evaluations to run
        print("\n⏳ Waiting 30 seconds for LLM evaluations to complete...")
        import time
        time.sleep(30)
        
        # Check for scores
        print("\n📊 Checking evaluation scores...")
        scores = evaluator.get_run_scores(results['run_name'])
        
        if "summary" in scores and "safety_compliance" in scores["summary"]:
            stats = scores["summary"]["safety_compliance"]
            print("\n🎯 Safety Compliance Results:")
            print(f"   Average Score: {stats['average_score']:.2f}")
            print(f"   Pass Rate: {stats['pass_rate']:.1%}")
            print(f"   Items Scored: {stats['total_scored']}")
            
            if stats['pass_rate'] >= 0.99:
                print("\n✅ Safety Compliance evaluator is working correctly!")
            else:
                print("\n⚠️ Safety scores are lower than expected.")
                print("   Check the Langfuse dashboard for details.")
        else:
            print("\n⚠️ No Safety Compliance scores found yet.")
            print("   The evaluator may still be running.")
            print(f"   Check dashboard: {results['dashboard_url']}")
            print(f"\n   To check again later, run:")
            print(f"   evaluator.get_run_scores('{results['run_name']}')")
    else:
        print("\n❌ Dataset run failed. Check the error messages above.")


if __name__ == "__main__":
    test_safety_compliance_evaluator()