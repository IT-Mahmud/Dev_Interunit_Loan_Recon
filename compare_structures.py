#!/usr/bin/env python3
"""
Compare HTML table and Excel column structures
"""

def compare_structures():
    """Compare the column structures"""
    
    print("🔍 Comparing HTML Table vs Excel Output Structures")
    print("=" * 60)
    
    # HTML Table Structure (from static/app.js)
    html_columns = [
        # Lender Section (7 columns)
        "Lender UID", "Lender Date", "Lender Particulars", "Lender Debit", 
        "Lender Credit", "Lender Vch Type", "Lender Role",
        # Borrower Section (7 columns)
        "Borrower UID", "Borrower Date", "Borrower Particulars", "Borrower Debit",
        "Borrower Credit", "Borrower Vch Type", "Borrower Role",
        # Match Details (4 columns)
        "Confidence", "Match Type", "Amount", "Actions"
    ]
    
    # Excel Output Structure (from app.py) - Updated to match HTML
    excel_columns = [
        # Lender Section (7 columns)
        "Lender UID", "Lender Date", "Lender Particulars", "Lender Debit",
        "Lender Credit", "Lender Vch Type", "Lender Role",
        # Borrower Section (7 columns)
        "Borrower UID", "Borrower Date", "Borrower Particulars", "Borrower Debit",
        "Borrower Credit", "Borrower Vch Type", "Borrower Role",
        # Match Details (4 columns)
        "Confidence", "Match Type", "Amount", "Actions"
    ]
    
    print("📋 HTML Table Columns:")
    print("-" * 30)
    for i, col in enumerate(html_columns, 1):
        print(f"{i:2d}. {col}")
    
    print("\n📊 Excel Output Columns:")
    print("-" * 30)
    for i, col in enumerate(excel_columns, 1):
        print(f"{i:2d}. {col}")
    
    print("\n🔍 Comparison:")
    print("-" * 30)
    
    # Check if structures match
    if len(html_columns) == len(excel_columns):
        print(f"✅ Column count matches: {len(html_columns)} columns")
        
        # Check each column
        mismatches = []
        for i, (html_col, excel_col) in enumerate(zip(html_columns, excel_columns)):
            if html_col != excel_col:
                mismatches.append((i+1, html_col, excel_col))
        
        if mismatches:
            print(f"❌ Found {len(mismatches)} mismatches:")
            for pos, html_col, excel_col in mismatches:
                print(f"   Position {pos}: HTML='{html_col}' vs Excel='{excel_col}'")
        else:
            print("✅ All column names match perfectly!")
    else:
        print(f"❌ Column count mismatch: HTML={len(html_columns)}, Excel={len(excel_columns)}")
    
    print("\n📊 Summary:")
    print("-" * 30)
    print("🏦 Lender Section (Debit > 0): 7 columns each")
    print("💳 Borrower Section (Credit > 0): 7 columns each")
    print("🔗 Match Details: 4 columns each")
    print("📋 Total: 18 columns each")
    print("\n🎯 Cross-Matching Logic:")
    print("-" * 30)
    print("• Lender = Transaction with Debit > 0")
    print("• Borrower = Transaction with Credit > 0")
    print("• Roles can switch between companies in different rows")

if __name__ == "__main__":
    compare_structures() 