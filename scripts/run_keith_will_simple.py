#!/usr/bin/env python
"""
Simple evaluation runner for Keith/Will dataset.
Patient mode with web tools enabled only.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.evaluation.evaluator import DatasetEvaluator
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def main():
    # Dataset name
    dataset_name = "health-assistant-eval-keith-will-qa_20250917_153838"
    
    # Configuration
    print("="*60)
    print("KEITH/WILL EVALUATION - PATIENT MODE WITH WEB TOOLS")
    print("="*60)
    print(f"Dataset: {dataset_name}")
    print("Mode: patient")
    print("Web Tools: enabled")
    print("Items: 50")
    print()
    
    # Initialize evaluator with patient mode and web tools
    evaluator = DatasetEvaluator(
        mode='patient',
        web_tools=True,
        domain_filter=None  # All domains allowed
    )
    
    # Create run name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"keith_will_patient_web_{timestamp}"
    
    print(f"Run Name: {run_name}")
    print(f"Starting evaluation...")
    print("-"*60)
    
    # Run the evaluation
    try:
        result = evaluator.run_dataset_evaluation(
            dataset_name=dataset_name,
            run_name=run_name,
            limit=None,  # Process all 50 items
            description="Keith/Will QA - Patient mode with web tools enabled",
            user_id="keith_will_patient"
        )
        
        print("\n" + "="*60)
        print("EVALUATION COMPLETE")
        print("="*60)
        print(f"✅ Successful: {result.get('successful', 0)}")
        print(f"❌ Failed: {result.get('failed', 0)}")
        print(f"📊 Success Rate: {result.get('successful', 0)/(result.get('successful', 0) + result.get('failed', 0))*100:.1f}%")
        
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        return 1
    
    print(f"\n🔗 View results in Langfuse:")
    print(f"   https://us.cloud.langfuse.com")
    print(f"   Go to: Datasets → {dataset_name} → Runs → {run_name}")
    
    return 0

if __name__ == "__main__":
    exit(main())