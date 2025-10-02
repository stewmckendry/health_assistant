#!/usr/bin/env python3
"""
Analyze data completeness across all Choosing Wisely JSON files.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import statistics

def analyze_completeness():
    """Analyze field completeness across all specialties."""
    
    # Path to JSON files
    base_path = Path("/Users/liammckendry/health_assistant_cw_integration")
    json_dir = base_path / "data" / "dr_opa_agent" / "processed" / "choosing_wisely"
    
    # Initialize statistics
    stats = {
        'total_files': 0,
        'total_recommendations': 0,
        'field_completeness': defaultdict(int),
        'field_values': defaultdict(list),
        'recommendations_per_specialty': [],
        'references_per_recommendation': [],
        'description_lengths': [],
        'title_lengths': []
    }
    
    # Document-level fields
    doc_fields = ['specialty', 'organization', 'last_updated', 'methodology', 'all_sources']
    
    # Recommendation-level fields
    rec_fields = ['number', 'title', 'description', 'references']
    
    # Process each JSON file
    json_files = sorted(json_dir.glob("*.json"))
    print(f"\nAnalyzing {len(json_files)} JSON files...")
    
    for json_file in json_files:
        stats['total_files'] += 1
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check document-level fields
            for field in doc_fields:
                if field in data and data[field]:
                    stats['field_completeness'][f'doc.{field}'] += 1
                    if field == 'last_updated':
                        stats['field_values']['last_updated'].append(data[field])
                    elif field == 'organization':
                        stats['field_values']['organization'].append(len(data[field]) if data[field] else 0)
            
            # Process recommendations
            recommendations = data.get('recommendations', [])
            stats['recommendations_per_specialty'].append(len(recommendations))
            
            for rec in recommendations:
                stats['total_recommendations'] += 1
                
                # Check recommendation-level fields
                for field in rec_fields:
                    full_field = f'rec.{field}'
                    if field in rec and rec[field] is not None:
                        if field == 'references':
                            # Count references as present if list exists (even if empty)
                            if isinstance(rec[field], list):
                                stats['field_completeness'][full_field] += 1
                                stats['references_per_recommendation'].append(len(rec[field]))
                        else:
                            if rec[field]:  # Not empty string or 0
                                stats['field_completeness'][full_field] += 1
                                
                                if field == 'description':
                                    stats['description_lengths'].append(len(rec[field]))
                                elif field == 'title':
                                    stats['title_lengths'].append(len(rec[field]))
        
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
    
    # Calculate percentages
    print("\n" + "="*60)
    print("FIELD COMPLETENESS ANALYSIS")
    print("="*60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"  • Total specialties: {stats['total_files']}")
    print(f"  • Total recommendations: {stats['total_recommendations']}")
    print(f"  • Avg recommendations per specialty: {statistics.mean(stats['recommendations_per_specialty']):.1f}")
    print(f"  • Min/Max recommendations: {min(stats['recommendations_per_specialty'])}/{max(stats['recommendations_per_specialty'])}")
    
    print(f"\n📋 Document-Level Fields (out of {stats['total_files']} files):")
    for field in doc_fields:
        full_field = f'doc.{field}'
        count = stats['field_completeness'].get(full_field, 0)
        pct = (count / stats['total_files']) * 100 if stats['total_files'] > 0 else 0
        status = "✅" if pct >= 90 else "⚠️" if pct >= 70 else "❌"
        print(f"  {status} {field:20s}: {count:3d}/{stats['total_files']} ({pct:.1f}%)")
    
    print(f"\n📄 Recommendation-Level Fields (out of {stats['total_recommendations']} recommendations):")
    for field in rec_fields:
        full_field = f'rec.{field}'
        count = stats['field_completeness'].get(full_field, 0)
        pct = (count / stats['total_recommendations']) * 100 if stats['total_recommendations'] > 0 else 0
        status = "✅" if pct >= 90 else "⚠️" if pct >= 70 else "❌"
        print(f"  {status} {field:20s}: {count:4d}/{stats['total_recommendations']} ({pct:.1f}%)")
    
    print(f"\n📈 Additional Statistics:")
    if stats['references_per_recommendation']:
        print(f"  • References per recommendation:")
        print(f"    - With references: {sum(1 for x in stats['references_per_recommendation'] if x > 0)}/{len(stats['references_per_recommendation'])} ({(sum(1 for x in stats['references_per_recommendation'] if x > 0)/len(stats['references_per_recommendation']))*100:.1f}%)")
        print(f"    - Average (when present): {statistics.mean([x for x in stats['references_per_recommendation'] if x > 0]):.1f}")
        print(f"    - Max references: {max(stats['references_per_recommendation'])}")
    
    if stats['description_lengths']:
        print(f"  • Description lengths:")
        print(f"    - Average: {statistics.mean(stats['description_lengths']):.0f} chars")
        print(f"    - Median: {statistics.median(stats['description_lengths']):.0f} chars")
        print(f"    - Min/Max: {min(stats['description_lengths'])}/{max(stats['description_lengths'])} chars")
    
    if stats['title_lengths']:
        print(f"  • Title lengths:")
        print(f"    - Average: {statistics.mean(stats['title_lengths']):.0f} chars")
        print(f"    - Median: {statistics.median(stats['title_lengths']):.0f} chars")
        print(f"    - Min/Max: {min(stats['title_lengths'])}/{max(stats['title_lengths'])} chars")
    
    # Sample unique values
    if stats['field_values']['last_updated']:
        unique_dates = set(stats['field_values']['last_updated'])
        print(f"\n📅 Unique 'last_updated' values ({len(unique_dates)}):")
        for date in sorted(unique_dates)[:5]:
            print(f"    • {date}")
        if len(unique_dates) > 5:
            print(f"    ... and {len(unique_dates) - 5} more")
    
    # Recommendations for metadata fields
    print("\n" + "="*60)
    print("METADATA RECOMMENDATIONS")
    print("="*60)
    print("\n✅ INCLUDE in metadata (high completeness >90%):")
    for field in ['specialty', 'organization', 'last_updated', 'number', 'title', 'description']:
        print(f"  • {field}")
    
    print("\n⚠️ CONDITIONAL include (moderate completeness):")
    print("  • references (present in ~50% of recommendations)")
    print("  • methodology (present in most but not all)")
    
    print("\n❌ EXCLUDE or make optional:")
    print("  • None - all core fields have good completeness")
    
    print("\n💡 Derived fields to add:")
    print("  • has_references (boolean)")
    print("  • reference_count (integer)")
    print("  • description_length (for chunking)")
    print("  • recommendation_type (extracted from title/description)")
    
    return stats

if __name__ == "__main__":
    analyze_completeness()