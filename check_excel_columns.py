#!/usr/bin/env python3
"""
Check the column structure of the generated Excel file
"""

import pandas as pd
import glob
import os

def check_excel_columns():
    """Check the column structure of the latest Excel file"""
    
    # Find the latest Excel file
    excel_files = glob.glob("test_matched_transactions_*.xlsx")
    if not excel_files:
        print("❌ No test Excel files found")
        return
    
    latest_file = max(excel_files, key=os.path.getctime)
    print(f"📊 Checking Excel file: {latest_file}")
    print("=" * 60)
    
    # Read the Excel file
    df = pd.read_excel(latest_file)
    
    print(f"📋 Total columns: {len(df.columns)}")
    print(f"📋 Total rows: {len(df)}")
    print("\n🔍 Column Structure:")
    print("-" * 60)
    
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2d}. {col}")
    
    print("\n📊 Column Groups:")
    print("-" * 60)
    
    # Group columns by section
    lender_cols = [col for col in df.columns if col.startswith('Lender_')]
    borrower_cols = [col for col in df.columns if col.startswith('Borrower_')]
    match_cols = [col for col in df.columns if col in ['Confidence', 'Match_Type', 'Amount', 'Actions']]
    
    print(f"🏦 Lender Section ({len(lender_cols)} columns):")
    for col in lender_cols:
        print(f"   • {col}")
    
    print(f"\n💳 Borrower Section ({len(borrower_cols)} columns):")
    for col in borrower_cols:
        print(f"   • {col}")
    
    print(f"\n🔗 Match Details ({len(match_cols)} columns):")
    for col in match_cols:
        print(f"   • {col}")
    
    # Show sample data
    print(f"\n📋 Sample Data (first 2 rows):")
    print("-" * 60)
    print(df.head(2).to_string())

if __name__ == "__main__":
    check_excel_columns() 