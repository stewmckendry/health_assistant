#!/usr/bin/env python
"""
Create Keith/Will QA dataset with specific category mix.
50 items total for human evaluation.
"""

import sys
from pathlib import Path
from datetime import datetime
sys.path.append(str(Path(__file__).parent.parent))

from src.evaluation.dataset_creator import DatasetCreator, DatasetConfig
from dotenv import load_dotenv

load_dotenv()

def main():
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_name = f"health-assistant-eval-keith-will-qa_{timestamp}"
    
    # Define the configuration per requirements
    config = DatasetConfig(
        name=dataset_name,
        description="Keith/Will QA evaluation dataset - 50 items for human review",
        categories={
            "basic": 5,
            "emergency": 3,
            "mental_health_crisis": 2,  # Note: using full category name
            "guardrails": 5,
            "adversarial": 5,
            "real_world": 25,
            "provider_clinical": 5  # Note: using full category name
        },
        total_limit=50,
        random_seed=42  # For reproducibility
    )
    
    print("=" * 60)
    print("CREATING KEITH/WILL QA DATASET")
    print("=" * 60)
    print(f"Dataset name: {dataset_name}")
    print(f"Timestamp: {timestamp}")
    print(f"Total items: 50")
    print("\nCategory breakdown:")
    for category, count in config.categories.items():
        print(f"  - {category}: {count}")
    
    # Create the dataset
    creator = DatasetCreator()
    creator.create_dataset(config, overwrite=True)
    
    print("\n" + "=" * 60)
    print("✅ DATASET CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nDataset name: {dataset_name}")
    print("\nNext steps:")
    print("1. Go to Langfuse: https://us.cloud.langfuse.com")
    print("2. Navigate to Datasets section")
    print(f"3. Find dataset: {dataset_name}")
    print("4. Click on the dataset to view items")
    print("5. Use the 'Runs' tab to execute evaluations")
    
    # Save the dataset name to a file for easy reference
    output_file = Path("evaluation_results") / f"dataset_name_{timestamp}.txt"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(dataset_name)
    print(f"\n📝 Dataset name saved to: {output_file}")
    
    return dataset_name

if __name__ == "__main__":
    dataset_name = main()