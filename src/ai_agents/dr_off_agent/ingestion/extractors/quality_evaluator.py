#!/usr/bin/env python3
"""Evaluate quality of OHIP data extraction."""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class QualityMetrics:
    """Quality metrics for extraction evaluation."""
    total_subsections: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    total_fee_codes: int = 0
    codes_with_fees: int = 0
    codes_missing_fees: int = 0
    codes_with_multi_column: int = 0
    tables_detected: int = 0
    time_requirements_found: int = 0
    average_codes_per_subsection: float = 0.0
    subsections_with_no_codes: List[str] = None
    duplicate_codes: Dict[str, int] = None
    malformed_codes: List[str] = None
    fee_validation_errors: List[str] = None
    coverage_by_section: Dict[str, Dict] = None

def validate_fee_code(code: str) -> bool:
    """Validate fee code format."""
    # Standard format: Letter(s) + 3-4 digits + optional letter
    pattern = r'^[A-Z]{1,2}\d{3,4}[A-Z]?$'
    return bool(re.match(pattern, code))

def validate_fee_amount(fee) -> Tuple[bool, str]:
    """Validate fee amount format."""
    if fee is None:
        return False, "Missing fee"
    
    # Convert to string if it's a number
    if isinstance(fee, (int, float)):
        return True, f"Valid numeric fee: ${fee}"
    
    if not fee:
        return False, "Missing fee"
    
    # Check for placeholder text
    if "single amount" in str(fee).lower() or "if only one column" in str(fee).lower():
        return False, "Placeholder text instead of actual fee"
    
    # Check for percentage increases
    if "%" in fee:
        if re.match(r'\d+%', fee):
            return True, "Percentage increase"
        return False, "Invalid percentage format"
    
    # Check for dollar amounts
    try:
        # Remove $ and commas
        cleaned = fee.replace('$', '').replace(',', '').strip()
        float(cleaned)
        return True, "Valid dollar amount"
    except:
        return False, f"Invalid fee format: {fee}"

def evaluate_extraction(json_file: str) -> QualityMetrics:
    """Evaluate extraction quality from JSON output."""
    
    with open(json_file) as f:
        data = json.load(f)
    
    metrics = QualityMetrics()
    metrics.subsections_with_no_codes = []
    metrics.duplicate_codes = defaultdict(int)
    metrics.malformed_codes = []
    metrics.fee_validation_errors = []
    metrics.coverage_by_section = defaultdict(lambda: {
        'subsections': 0,
        'fee_codes': 0,
        'codes_with_fees': 0,
        'tables_detected': 0
    })
    
    seen_codes = defaultdict(int)
    
    # Process each subsection
    subsections = data.get('subsections', [])
    metrics.total_subsections = len(subsections)
    
    for sub in subsections:
        parent = sub.get('parent_section', 'Unknown')
        metrics.coverage_by_section[parent]['subsections'] += 1
        
        # Check for extraction errors
        if 'error' in sub:
            metrics.failed_extractions += 1
            continue
        
        metrics.successful_extractions += 1
        
        # Check table detection
        table_info = sub.get('table_structures_detected', {})
        if table_info.get('multi_column'):
            metrics.tables_detected += 1
            metrics.coverage_by_section[parent]['tables_detected'] += 1
        
        # Process fee codes
        fee_codes = sub.get('fee_codes', [])
        
        if not fee_codes:
            metrics.subsections_with_no_codes.append(f"{parent}/{sub.get('page_ref')} - {sub.get('subsection_title')}")
        
        for fc in fee_codes:
            code = fc.get('code')
            if not code:
                continue
            
            metrics.total_fee_codes += 1
            metrics.coverage_by_section[parent]['fee_codes'] += 1
            
            # Validate code format
            if not validate_fee_code(code):
                metrics.malformed_codes.append(code)
            
            # Track duplicates
            seen_codes[code] += 1
            if seen_codes[code] > 1:
                metrics.duplicate_codes[code] = seen_codes[code]
            
            # Check fee extraction
            has_valid_fee = False
            
            # Check single fee
            if fc.get('fee'):
                is_valid, msg = validate_fee_amount(fc['fee'])
                if is_valid:
                    has_valid_fee = True
                else:
                    metrics.fee_validation_errors.append(f"{code}: {msg}")
            
            # Check H/P fees
            if fc.get('h_fee') or fc.get('p_fee'):
                metrics.codes_with_multi_column += 1
                if fc.get('h_fee'):
                    is_valid, _ = validate_fee_amount(fc['h_fee'])
                    if is_valid:
                        has_valid_fee = True
                if fc.get('p_fee'):
                    is_valid, _ = validate_fee_amount(fc['p_fee'])
                    if is_valid:
                        has_valid_fee = True
            
            # Check Asst/Surg/Anae fees
            if fc.get('asst_fee') or fc.get('surg_fee') or fc.get('anae_fee'):
                metrics.codes_with_multi_column += 1
                for fee_type in ['asst_fee', 'surg_fee', 'anae_fee']:
                    if fc.get(fee_type):
                        is_valid, _ = validate_fee_amount(fc[fee_type])
                        if is_valid:
                            has_valid_fee = True
            
            if has_valid_fee:
                metrics.codes_with_fees += 1
                metrics.coverage_by_section[parent]['codes_with_fees'] += 1
            else:
                metrics.codes_missing_fees += 1
            
            # Check time requirements
            if fc.get('conditions') and 'minute' in fc.get('conditions', '').lower():
                metrics.time_requirements_found += 1
    
    # Calculate averages
    if metrics.successful_extractions > 0:
        metrics.average_codes_per_subsection = metrics.total_fee_codes / metrics.successful_extractions
    
    return metrics

def generate_quality_report(metrics: QualityMetrics) -> str:
    """Generate human-readable quality report."""
    
    report = []
    report.append("="*60)
    report.append("OHIP EXTRACTION QUALITY REPORT")
    report.append("="*60)
    
    # Overall statistics
    report.append("\n## OVERALL STATISTICS")
    report.append(f"Total subsections processed: {metrics.total_subsections}")
    report.append(f"Successful extractions: {metrics.successful_extractions} ({metrics.successful_extractions/max(1,metrics.total_subsections)*100:.1f}%)")
    report.append(f"Failed extractions: {metrics.failed_extractions}")
    report.append(f"Total fee codes extracted: {metrics.total_fee_codes}")
    report.append(f"Average codes per subsection: {metrics.average_codes_per_subsection:.1f}")
    
    # Fee quality
    report.append("\n## FEE EXTRACTION QUALITY")
    report.append(f"Codes with valid fees: {metrics.codes_with_fees} ({metrics.codes_with_fees/max(1,metrics.total_fee_codes)*100:.1f}%)")
    report.append(f"Codes missing fees: {metrics.codes_missing_fees}")
    report.append(f"Multi-column fee structures: {metrics.codes_with_multi_column}")
    report.append(f"Tables detected: {metrics.tables_detected}")
    report.append(f"Time requirements found: {metrics.time_requirements_found}")
    
    # Data quality issues
    report.append("\n## DATA QUALITY ISSUES")
    
    if metrics.malformed_codes:
        report.append(f"\n### Malformed fee codes ({len(metrics.malformed_codes)}):")
        for code in metrics.malformed_codes[:10]:
            report.append(f"  - {code}")
    
    if metrics.duplicate_codes:
        report.append(f"\n### Duplicate codes ({len(metrics.duplicate_codes)}):")
        for code, count in list(metrics.duplicate_codes.items())[:10]:
            report.append(f"  - {code}: appears {count} times")
    
    if metrics.fee_validation_errors:
        report.append(f"\n### Fee validation errors ({len(metrics.fee_validation_errors)}):")
        for error in metrics.fee_validation_errors[:10]:
            report.append(f"  - {error}")
    
    # Coverage by section
    report.append("\n## COVERAGE BY SECTION")
    report.append(f"{'Section':<10} {'Subsections':<12} {'Fee Codes':<10} {'With Fees':<10} {'Tables':<10}")
    report.append("-"*52)
    
    for section in sorted(metrics.coverage_by_section.keys()):
        stats = metrics.coverage_by_section[section]
        report.append(
            f"{section:<10} {stats['subsections']:<12} {stats['fee_codes']:<10} "
            f"{stats['codes_with_fees']:<10} {stats['tables_detected']:<10}"
        )
    
    # Subsections with no codes
    if metrics.subsections_with_no_codes:
        report.append(f"\n## SUBSECTIONS WITH NO CODES ({len(metrics.subsections_with_no_codes)})")
        for sub in metrics.subsections_with_no_codes[:20]:
            report.append(f"  - {sub}")
    
    # Summary assessment
    report.append("\n## QUALITY ASSESSMENT")
    
    quality_score = 0
    max_score = 5
    
    if metrics.successful_extractions / max(1, metrics.total_subsections) > 0.95:
        quality_score += 1
        report.append("✅ High extraction success rate (>95%)")
    else:
        report.append("⚠️ Low extraction success rate (<95%)")
    
    if metrics.codes_with_fees / max(1, metrics.total_fee_codes) > 0.8:
        quality_score += 1
        report.append("✅ Good fee capture rate (>80%)")
    else:
        report.append("❌ Poor fee capture rate (<80%)")
    
    if len(metrics.malformed_codes) < metrics.total_fee_codes * 0.01:
        quality_score += 1
        report.append("✅ Low malformed code rate (<1%)")
    else:
        report.append("⚠️ High malformed code rate (>1%)")
    
    if len(metrics.duplicate_codes) < metrics.total_fee_codes * 0.05:
        quality_score += 1
        report.append("✅ Low duplicate rate (<5%)")
    else:
        report.append("⚠️ High duplicate rate (>5%)")
    
    if metrics.average_codes_per_subsection > 5:
        quality_score += 1
        report.append("✅ Good code density (>5 per subsection)")
    else:
        report.append("⚠️ Low code density (<5 per subsection)")
    
    report.append(f"\n**Overall Quality Score: {quality_score}/{max_score}**")
    
    return "\n".join(report)

def main():
    """Evaluate extraction quality."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate OHIP extraction quality')
    parser.add_argument('--input', default='data/processed/subsections_enhanced.json',
                       help='Input JSON file to evaluate')
    parser.add_argument('--output', default='data/processed/extraction_quality_report.txt',
                       help='Output report file')
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Input file not found: {args.input}")
        return
    
    print(f"Evaluating extraction quality from: {args.input}")
    
    # Evaluate
    metrics = evaluate_extraction(args.input)
    
    # Generate report
    report = generate_quality_report(metrics)
    
    # Save report
    with open(args.output, 'w') as f:
        f.write(report)
    
    # Print to console
    print(report)
    print(f"\nReport saved to: {args.output}")

if __name__ == '__main__':
    main()