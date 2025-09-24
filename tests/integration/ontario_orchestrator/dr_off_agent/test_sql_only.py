#!/usr/bin/env python3
"""
Test SQL queries directly without vector search
"""
import sqlite3
import sys

def test_ohip_queries():
    """Test OHIP fee schedule queries."""
    print("\n" + "="*60)
    print("TESTING OHIP FEE SCHEDULE QUERIES")
    print("="*60)
    
    conn = sqlite3.connect("data/processed/dr_off/dr_off.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Test 1: Look for C124
    print("\nTest 1: Search for C124 discharge code")
    print("-" * 40)
    cursor.execute("""
        SELECT fee_code as code, description, amount, specialty, requirements, page_number
        FROM ohip_fee_schedule 
        WHERE fee_code = 'C124' OR fee_code LIKE '%C124%'
        LIMIT 5
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} results")
    for row in results:
        print(f"  Code: {row['code']}")
        print(f"  Description: {row['description']}")
        print(f"  Amount: ${row['amount']:.2f}" if row['amount'] else "  Amount: N/A")
        print(f"  Requirements: {row['requirements']}" if row['requirements'] else "  Requirements: N/A")
        print()
    
    # Test 2: Search for discharge-related codes
    print("\nTest 2: Search for discharge-related codes")
    print("-" * 40)
    cursor.execute("""
        SELECT fee_code as code, description, amount
        FROM ohip_fee_schedule 
        WHERE description LIKE '%discharge%'
        LIMIT 5
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} discharge-related codes")
    for row in results:
        print(f"  {row['code']}: {row['description'][:60]}...")
        if row['amount']:
            print(f"    Fee: ${row['amount']:.2f}")
    
    # Test 3: Search for consultation codes
    print("\nTest 3: Search for consultation codes A135, A935")
    print("-" * 40)
    cursor.execute("""
        SELECT fee_code as code, description, amount, specialty
        FROM ohip_fee_schedule 
        WHERE fee_code IN ('A135', 'A935')
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} consultation codes")
    for row in results:
        print(f"  {row['code']}: {row['description']}")
        if row['amount']:
            print(f"    Fee: ${row['amount']:.2f}")
        if row['specialty']:
            print(f"    Specialty: {row['specialty']}")
    
    conn.close()

def test_adp_queries():
    """Test ADP funding and exclusion queries."""
    print("\n" + "="*60)
    print("TESTING ADP FUNDING QUERIES")
    print("="*60)
    
    # ADP tables are in data/ohip.db, not dr_off.db
    conn = sqlite3.connect("data/ohip.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Test 1: Funding rules for purchase scenarios
    print("\nTest 1: Funding rules for purchase of mobility devices")
    print("-" * 40)
    cursor.execute("""
        SELECT scenario, client_share_percent, details, adp_doc
        FROM adp_funding_rule
        WHERE scenario = 'purchase' OR adp_doc = 'mobility'
        LIMIT 5
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} funding rules")
    for row in results:
        print(f"  Scenario: {row['scenario']} ({row['adp_doc']})")
        if row['client_share_percent']:
            print(f"  Client share: {row['client_share_percent']}%")
        if row['details']:
            print(f"  Details: {row['details'][:100]}...")
        print()
    
    # Test 2: Check exclusions for education/work/recreation
    print("\nTest 2: Exclusions for education/work/recreation and mobility")
    print("-" * 40)
    cursor.execute("""
        SELECT phrase, applies_to, adp_doc
        FROM adp_exclusion
        WHERE phrase LIKE '%education%' OR applies_to = 'mobility'
        LIMIT 5
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} exclusions")
    for row in results:
        print(f"  Exclusion: {row['phrase']}")
        print(f"  Applies to: {row['applies_to']} ({row['adp_doc']})")
        print()
    
    # Test 3: CEP and lease funding
    print("\nTest 3: Central Equipment Pool (CEP) and lease funding")
    print("-" * 40)
    cursor.execute("""
        SELECT scenario, client_share_percent, details
        FROM adp_funding_rule
        WHERE scenario = 'lease' OR details LIKE '%CEP%' OR details LIKE '%Central Equipment%'
        LIMIT 5
    """)
    results = cursor.fetchall()
    print(f"Found {len(results)} CEP/lease rules")
    for row in results:
        print(f"  Scenario: {row['scenario']}")
        print(f"  Client share: {row['client_share_percent']}%")
        print()
    
    conn.close()

def main():
    """Run all SQL tests."""
    print("\n" + "="*60)
    print("DIRECT SQL QUERY TESTS")
    print("="*60)
    
    test_ohip_queries()
    test_adp_queries()
    
    print("\n" + "="*60)
    print("SQL TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()