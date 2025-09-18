#!/usr/bin/env python
"""
Extract all test prompts from evaluation_test_cases.yaml and create a markdown file.
Organizes prompts by category and subcategory.
"""

import yaml
from pathlib import Path
from collections import defaultdict

def load_test_cases():
    """Load test cases from YAML file."""
    yaml_path = Path(__file__).parent.parent / "src/config/evaluation_test_cases.yaml"
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['test_cases']

def organize_prompts(test_cases):
    """Organize prompts by category and subcategory."""
    organized = defaultdict(lambda: defaultdict(list))
    
    for category, items in test_cases.items():
        for item in items:
            subcategory = item.get('subcategory', 'general')
            query = item['input']['query']
            mode = item['input'].get('mode', 'patient')
            
            organized[category][subcategory].append({
                'query': query,
                'mode': mode
            })
    
    return organized

def create_markdown(organized_prompts):
    """Create markdown content from organized prompts."""
    lines = []
    
    # Header
    lines.append("# Health Assistant Evaluation Test Prompts")
    lines.append("")
    lines.append("This document contains all test prompts from `evaluation_test_cases.yaml` organized by category and subcategory.")
    lines.append("")
    
    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    
    category_order = ['basic', 'emergency', 'mental_health_crisis', 'guardrails', 
                      'adversarial', 'real_world', 'provider_clinical']
    
    for category in category_order:
        if category in organized_prompts:
            display_name = category.replace('_', ' ').title()
            lines.append(f"- [{display_name}](#{category.replace('_', '-')})")
    lines.append("")
    
    # Statistics
    lines.append("## Statistics")
    lines.append("")
    total_prompts = sum(
        len(prompts) 
        for subcats in organized_prompts.values() 
        for prompts in subcats.values()
    )
    lines.append(f"- **Total prompts:** {total_prompts}")
    lines.append(f"- **Categories:** {len(organized_prompts)}")
    lines.append("")
    
    # Category breakdown
    lines.append("| Category | Count | Subcategories |")
    lines.append("|----------|-------|---------------|")
    
    for category in category_order:
        if category in organized_prompts:
            count = sum(len(prompts) for prompts in organized_prompts[category].values())
            num_subcats = len(organized_prompts[category])
            display_name = category.replace('_', ' ').title()
            lines.append(f"| {display_name} | {count} | {num_subcats} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Detailed prompts by category
    for category in category_order:
        if category not in organized_prompts:
            continue
            
        # Category header
        display_name = category.replace('_', ' ').title()
        lines.append(f"## {display_name}")
        lines.append("")
        
        # Category statistics
        total_in_category = sum(len(prompts) for prompts in organized_prompts[category].values())
        lines.append(f"**Total prompts in category:** {total_in_category}")
        lines.append("")
        
        # Subcategories
        subcategories = sorted(organized_prompts[category].keys())
        
        for subcategory in subcategories:
            prompts = organized_prompts[category][subcategory]
            
            # Subcategory header
            subcat_display = subcategory.replace('_', ' ').title()
            lines.append(f"### {subcat_display}")
            lines.append(f"*({len(prompts)} prompts)*")
            lines.append("")
            
            # List prompts
            for i, prompt_data in enumerate(prompts, 1):
                query = prompt_data['query']
                mode = prompt_data['mode']
                
                # Truncate very long prompts for readability in the list
                if len(query) > 200:
                    display_query = query[:197] + "..."
                else:
                    display_query = query
                
                # Add mode indicator if not patient
                mode_indicator = f" `[{mode}]`" if mode != 'patient' else ""
                
                lines.append(f"{i}. {display_query}{mode_indicator}")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)

def main():
    """Main function to extract prompts and create markdown."""
    print("Loading test cases from YAML...")
    test_cases = load_test_cases()
    
    print("Organizing prompts by category and subcategory...")
    organized = organize_prompts(test_cases)
    
    print("Creating markdown document...")
    markdown_content = create_markdown(organized)
    
    # Save to file
    output_path = Path(__file__).parent.parent / "docs" / "test_prompts_catalog.md"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(markdown_content)
    
    print(f"\n✅ Successfully created: {output_path}")
    
    # Print summary statistics
    total_prompts = sum(
        len(prompts) 
        for subcats in organized.values() 
        for prompts in subcats.values()
    )
    
    print(f"\n📊 Summary:")
    print(f"   Total prompts: {total_prompts}")
    print(f"   Categories: {len(organized)}")
    
    for category, subcats in organized.items():
        count = sum(len(prompts) for prompts in subcats.values())
        print(f"   - {category}: {count} prompts across {len(subcats)} subcategories")

if __name__ == "__main__":
    main()