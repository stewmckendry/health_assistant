"""
Analyze front matter extraction quality across all Quality Standards PDFs.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

def analyze_front_matter_completeness():
    """Analyze the completeness of front matter extraction across all PDFs."""
    
    extraction_dir = Path("data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304")
    
    # Front matter fields to check
    fm_fields = [
        'executive_summary',
        'scope', 
        'why_needed',
        'how_measured',
        'definitions',
        'principles',
        'for_patients',
        'for_clinicians',
        'system_support'
    ]
    
    # Store results
    results = []
    
    # Get all JSON files (excluding error and summary files)
    json_files = [f for f in extraction_dir.glob("qs-*.json") 
                  if not f.name.endswith("_error.json") 
                  and not f.name.startswith("extraction_")]
    
    for json_file in sorted(json_files):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        title = data.get('title', 'Unknown')
        front_matter = data.get('front_matter', {})
        
        # Check each field
        field_status = {}
        populated_count = 0
        total_chars = 0
        
        for field in fm_fields:
            content = front_matter.get(field, '')
            is_populated = len(content) > 20  # Consider populated if > 20 chars
            char_count = len(content)
            
            field_status[field] = {
                'populated': is_populated,
                'char_count': char_count
            }
            
            if is_populated:
                populated_count += 1
                total_chars += char_count
        
        results.append({
            'file': json_file.name,
            'title': title,
            'populated_fields': populated_count,
            'total_fields': len(fm_fields),
            'completeness_pct': (populated_count / len(fm_fields)) * 100,
            'total_chars': total_chars,
            'field_details': field_status
        })
    
    return results, fm_fields

def print_analysis_report():
    """Print a detailed analysis report."""
    
    results, fm_fields = analyze_front_matter_completeness()
    
    print("=" * 80)
    print("FRONT MATTER EXTRACTION QUALITY ANALYSIS")
    print("=" * 80)
    print(f"Total PDFs analyzed: {len(results)}")
    print()
    
    # Sort by completeness
    results.sort(key=lambda x: x['completeness_pct'], reverse=True)
    
    # Categories
    excellent = []  # 80%+ fields populated
    good = []       # 60-79% fields populated
    moderate = []   # 40-59% fields populated  
    poor = []       # <40% fields populated
    
    for r in results:
        pct = r['completeness_pct']
        if pct >= 80:
            excellent.append(r)
        elif pct >= 60:
            good.append(r)
        elif pct >= 40:
            moderate.append(r)
        else:
            poor.append(r)
    
    # Print summary
    print("SUMMARY BY QUALITY:")
    print(f"  Excellent (80%+): {len(excellent)} PDFs")
    print(f"  Good (60-79%): {len(good)} PDFs")
    print(f"  Moderate (40-59%): {len(moderate)} PDFs")
    print(f"  Poor (<40%): {len(poor)} PDFs")
    print()
    
    # Print detailed lists
    if poor:
        print("=" * 80)
        print("POOR QUALITY EXTRACTIONS (<40% fields):")
        print("-" * 80)
        for r in poor:
            print(f"\n{r['title']} ({r['file']})")
            print(f"  Populated: {r['populated_fields']}/{r['total_fields']} fields ({r['completeness_pct']:.1f}%)")
            print(f"  Total content: {r['total_chars']} characters")
            print("  Missing fields:")
            for field in fm_fields:
                if not r['field_details'][field]['populated']:
                    print(f"    - {field}")
    
    if moderate:
        print("\n" + "=" * 80)
        print("MODERATE QUALITY EXTRACTIONS (40-59% fields):")
        print("-" * 80)
        for r in moderate:
            print(f"\n{r['title']} ({r['file']})")
            print(f"  Populated: {r['populated_fields']}/{r['total_fields']} fields ({r['completeness_pct']:.1f}%)")
            print(f"  Total content: {r['total_chars']} characters")
    
    # Field-level analysis
    print("\n" + "=" * 80)
    print("FIELD-LEVEL ANALYSIS:")
    print("-" * 80)
    
    field_stats = {field: {'populated': 0, 'total_chars': 0} for field in fm_fields}
    
    for r in results:
        for field in fm_fields:
            if r['field_details'][field]['populated']:
                field_stats[field]['populated'] += 1
                field_stats[field]['total_chars'] += r['field_details'][field]['char_count']
    
    print("\nField population rates:")
    for field in fm_fields:
        pct = (field_stats[field]['populated'] / len(results)) * 100
        avg_chars = field_stats[field]['total_chars'] / max(field_stats[field]['populated'], 1)
        print(f"  {field:20s}: {field_stats[field]['populated']:2d}/{len(results)} ({pct:5.1f}%) - Avg {avg_chars:.0f} chars")
    
    # Identify consistently missing fields
    print("\n" + "=" * 80)
    print("CONSISTENTLY MISSING/WEAK FIELDS:")
    print("-" * 80)
    
    for field in fm_fields:
        pct = (field_stats[field]['populated'] / len(results)) * 100
        if pct < 50:
            print(f"  ⚠️  {field}: Only {pct:.1f}% of PDFs have this field")
    
    print("\n" + "=" * 80)
    
    # Save detailed report
    report_path = Path("data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304/front_matter_analysis.json")
    with open(report_path, 'w') as f:
        json.dump({
            'summary': {
                'total_pdfs': len(results),
                'excellent': len(excellent),
                'good': len(good),
                'moderate': len(moderate),
                'poor': len(poor)
            },
            'field_stats': field_stats,
            'detailed_results': results
        }, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    print_analysis_report()