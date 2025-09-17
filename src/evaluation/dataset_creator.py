#!/usr/bin/env python
"""Create Langfuse datasets from YAML test cases with configurable sampling."""

import os
import yaml
import random
from typing import List, Dict, Any, Optional
from pathlib import Path
from langfuse import Langfuse
from dotenv import load_dotenv
from dataclasses import dataclass
from collections import defaultdict

# Load environment variables
load_dotenv()


@dataclass
class DatasetConfig:
    """Configuration for dataset creation."""
    name: str
    description: str
    categories: Dict[str, int]  # category -> number of samples
    total_limit: Optional[int] = None  # Optional total limit
    random_seed: Optional[int] = None  # For reproducibility
    include_subcategories: Optional[List[str]] = None  # Specific subcategories to include
    exclude_subcategories: Optional[List[str]] = None  # Specific subcategories to exclude


class DatasetCreator:
    """Creates and manages Langfuse datasets for evaluation."""
    
    def __init__(self, test_cases_path: Optional[str] = None):
        """
        Initialize Langfuse client and load test cases.
        
        Args:
            test_cases_path: Path to YAML file with test cases. 
                           Defaults to src/config/evaluation_test_cases.yaml
        """
        self.langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )
        
        # Load test cases from YAML
        if test_cases_path is None:
            test_cases_path = Path(__file__).parent.parent / "config" / "evaluation_test_cases.yaml"
        
        with open(test_cases_path, 'r') as f:
            self.test_cases_data = yaml.safe_load(f)
        
        self.test_cases = self.test_cases_data.get('test_cases', {})
        
        # Organize test cases by category and subcategory
        self._organize_test_cases()
        
    def _organize_test_cases(self):
        """Organize test cases by category and subcategory for easy filtering."""
        self.cases_by_category = defaultdict(list)
        self.cases_by_subcategory = defaultdict(list)
        
        for category_name, cases in self.test_cases.items():
            for case in cases:
                # Add category if not present
                if 'category' not in case:
                    case['category'] = category_name
                
                self.cases_by_category[case['category']].append(case)
                
                if 'subcategory' in case:
                    self.cases_by_subcategory[case['subcategory']].append(case)
    
    def get_available_categories(self) -> Dict[str, int]:
        """Get all available categories and their counts."""
        return {cat: len(cases) for cat, cases in self.cases_by_category.items()}
    
    def get_available_subcategories(self) -> Dict[str, int]:
        """Get all available subcategories and their counts."""
        return {subcat: len(cases) for subcat, cases in self.cases_by_subcategory.items()}
    
    def sample_test_cases(self, config: DatasetConfig) -> List[Dict[str, Any]]:
        """
        Sample test cases based on configuration.
        
        Args:
            config: DatasetConfig specifying sampling parameters
            
        Returns:
            List of sampled test cases
        """
        if config.random_seed is not None:
            random.seed(config.random_seed)
        
        sampled_cases = []
        
        # Sample from each specified category
        for category, num_samples in config.categories.items():
            if category not in self.cases_by_category:
                print(f"Warning: Category '{category}' not found in test cases")
                continue
            
            available_cases = self.cases_by_category[category].copy()
            
            # Apply subcategory filters if specified
            if config.include_subcategories:
                available_cases = [
                    case for case in available_cases 
                    if case.get('subcategory') in config.include_subcategories
                ]
            
            if config.exclude_subcategories:
                available_cases = [
                    case for case in available_cases 
                    if case.get('subcategory') not in config.exclude_subcategories
                ]
            
            # Sample the requested number of cases
            num_to_sample = min(num_samples, len(available_cases))
            if num_to_sample < num_samples:
                print(f"Warning: Only {num_to_sample} cases available for category '{category}' (requested {num_samples})")
            
            sampled = random.sample(available_cases, num_to_sample)
            sampled_cases.extend(sampled)
        
        # Apply total limit if specified
        if config.total_limit and len(sampled_cases) > config.total_limit:
            sampled_cases = random.sample(sampled_cases, config.total_limit)
        
        # Shuffle the final list to mix categories
        random.shuffle(sampled_cases)
        
        return sampled_cases
    
    def create_dataset(self, config: DatasetConfig, overwrite: bool = False) -> str:
        """
        Create or update a Langfuse dataset with sampled test cases.
        
        Args:
            config: DatasetConfig for dataset creation
            overwrite: Whether to overwrite existing dataset
            
        Returns:
            Dataset name
        """
        dataset_name = config.name
        
        try:
            # Check if dataset exists
            existing = self.langfuse.get_dataset(name=dataset_name)
            if existing and not overwrite:
                print(f"Dataset '{dataset_name}' already exists")
                return dataset_name
            elif existing and overwrite:
                print(f"Overwriting existing dataset '{dataset_name}'")
        except Exception:
            pass
        
        # Create new dataset
        dataset = self.langfuse.create_dataset(
            name=dataset_name,
            description=config.description,
            metadata={
                "config": {
                    "categories": config.categories,
                    "total_limit": config.total_limit,
                    "random_seed": config.random_seed,
                    "include_subcategories": config.include_subcategories,
                    "exclude_subcategories": config.exclude_subcategories
                },
                "version": "2.0"
            }
        )
        print(f"Created dataset: {dataset_name}")
        
        # Sample test cases
        sampled_cases = self.sample_test_cases(config)
        print(f"Sampled {len(sampled_cases)} test cases")
        
        # Add sampled cases to dataset
        success_count = 0
        error_count = 0
        
        for case in sampled_cases:
            try:
                # Prepare metadata
                metadata = {
                    "category": case.get("category"),
                    "subcategory": case.get("subcategory"),
                    "severity": case.get("severity")
                }
                # Remove None values
                metadata = {k: v for k, v in metadata.items() if v is not None}
                
                self.langfuse.create_dataset_item(
                    dataset_name=dataset_name,
                    input=case.get("input", {}),
                    expected_output=case.get("expected_output", {}),
                    metadata=metadata
                )
                success_count += 1
            except Exception as e:
                print(f"Error adding item: {e}")
                error_count += 1
        
        print(f"Successfully added {success_count} items to dataset")
        if error_count > 0:
            print(f"Failed to add {error_count} items")
        
        # Print category distribution
        category_counts = defaultdict(int)
        for case in sampled_cases:
            category_counts[case.get("category", "unknown")] += 1
        
        print("\nDataset composition:")
        for category, count in sorted(category_counts.items()):
            print(f"  {category}: {count} items")
        
        return dataset_name
    
    def create_predefined_datasets(self):
        """Create several predefined dataset configurations for common use cases."""
        
        configs = [
            # Comprehensive baseline dataset
            DatasetConfig(
                name="health-assistant-eval-comprehensive",
                description="Comprehensive evaluation across all categories",
                categories={
                    "basic": 10,
                    "emergency": 5,
                    "mental_health_crisis": 3,
                    "guardrails": 8,
                    "adversarial": 10,
                    "real_world": 30,
                    "provider_clinical": 15
                },
                total_limit=100,
                random_seed=42
            ),
            
            # Safety-focused dataset
            DatasetConfig(
                name="health-assistant-eval-safety",
                description="Focus on safety, emergencies, and guardrails",
                categories={
                    "emergency": 10,
                    "mental_health_crisis": 10,
                    "guardrails": 15,
                    "adversarial": 15
                },
                random_seed=42
            ),
            
            # Real-world patient scenarios
            DatasetConfig(
                name="health-assistant-eval-patient-real",
                description="Real-world patient scenarios with diverse demographics",
                categories={
                    "real_world": 50,
                    "basic": 10
                },
                include_subcategories=None,  # Include all subcategories
                random_seed=42
            ),
            
            # Provider-specific evaluation
            DatasetConfig(
                name="health-assistant-eval-provider",
                description="Provider and clinical scenarios",
                categories={
                    "provider_clinical": 40,
                    "real_world": 10  # Some real-world for context
                },
                random_seed=42
            ),
            
            # Quick smoke test dataset
            DatasetConfig(
                name="health-assistant-eval-smoke-test",
                description="Quick smoke test with 5 items from each category",
                categories={
                    "basic": 2,
                    "emergency": 1,
                    "mental_health_crisis": 1,
                    "guardrails": 2,
                    "adversarial": 2,
                    "real_world": 3,
                    "provider_clinical": 2
                },
                total_limit=15,
                random_seed=42
            ),
            
            # Vulnerable populations focus
            DatasetConfig(
                name="health-assistant-eval-vulnerable",
                description="Focus on vulnerable populations and health equity",
                categories={
                    "real_world": 40
                },
                include_subcategories=[
                    "homeless_health", "veteran_ptsd", "disability_access",
                    "lgbtq_health", "immigrant_language_barrier", "rural_access_issues",
                    "uninsured_cost_concerns", "elder_abuse_signs", "teen_acne_mental_health",
                    "incarceration_medical_neglect", "detention_center_outbreak"
                ],
                random_seed=42
            ),
            
            # Chronic disease management
            DatasetConfig(
                name="health-assistant-eval-chronic",
                description="Chronic disease management scenarios",
                categories={
                    "real_world": 30,
                    "basic": 5
                },
                include_subcategories=[
                    "diabetes_complications", "hypertension_uncontrolled", "asthma_worsening",
                    "copd_exacerbation", "heart_failure", "chronic_pain", "autoimmune"
                ],
                random_seed=42
            )
        ]
        
        return configs
    
    def print_dataset_summary(self):
        """Print a summary of available test cases."""
        print("=" * 60)
        print("AVAILABLE TEST CASES SUMMARY")
        print("=" * 60)
        
        # Categories
        print("\nCategories:")
        categories = self.get_available_categories()
        total = sum(categories.values())
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count} cases")
        print(f"\nTotal: {total} test cases")
        
        # Subcategories (top 20)
        print("\nTop 20 Subcategories:")
        subcategories = self.get_available_subcategories()
        for subcat, count in sorted(subcategories.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {subcat}: {count} cases")
        
        print("\n" + "=" * 60)


def main():
    """Main function to demonstrate dataset creation."""
    creator = DatasetCreator()
    
    # Print summary
    creator.print_dataset_summary()
    
    # Example: Create a custom dataset
    custom_config = DatasetConfig(
        name="health-assistant-eval-custom-demo",
        description="Custom demo dataset with specific sampling",
        categories={
            "basic": 5,
            "emergency": 3,
            "real_world": 10,
            "adversarial": 5
        },
        total_limit=20,
        random_seed=123
    )
    
    print("\nCreating custom dataset...")
    creator.create_dataset(custom_config, overwrite=True)
    
    # Show predefined configs
    print("\n" + "=" * 60)
    print("PREDEFINED DATASET CONFIGURATIONS")
    print("=" * 60)
    
    for config in creator.create_predefined_datasets():
        print(f"\n{config.name}:")
        print(f"  Description: {config.description}")
        print(f"  Categories: {config.categories}")
        if config.total_limit:
            print(f"  Total limit: {config.total_limit}")
        if config.include_subcategories:
            print(f"  Include subcategories: {config.include_subcategories[:3]}...")
    

if __name__ == "__main__":
    main()