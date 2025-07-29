from sqlalchemy import create_engine, inspect, text
import pandas as pd
from config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB
import re

engine = create_engine(
    f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
)

def ensure_table_exists(table_name):
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        raise Exception(
            f"Table '{table_name}' does not exist. Please create it manually in MySQL before uploading."
        )

def save_data(df):
    """Save DataFrame to database, with user-friendly duplicate UID error."""
    try:
        ensure_table_exists('tally_data')
        # Replace NaN values with None before saving
        df = df.replace({pd.NA: None, pd.NaT: None})
        df = df.where(pd.notnull(df), None)
        df.to_sql('tally_data', engine, if_exists='append', index=False)
        return True, None
    except Exception as e:
        if 'Duplicate entry' in str(e) and 'uid' in str(e):
            return False, 'Duplicate data: This file (or some records) has already been uploaded.'
        print(f"Error saving data: {e}")
        return False, str(e)

def get_data(filters=None):
    """Get data from database"""
    try:
        ensure_table_exists('tally_data')
        
        # Get column order from database
        with engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM tally_data"))
            columns = [row[0] for row in result]
        
        # Build SQL with explicit column order
        column_list = ", ".join(columns)
        sql = f"SELECT {column_list} FROM tally_data"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if value:
                    conditions.append(f"{key} = %s")
                    params.append(value)
            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY Date DESC"
        
        df = pd.read_sql(sql, engine, params=params)
        
        # Convert to records and handle NaN values
        records = df.to_dict('records')
        
        # Replace any remaining NaN values with None for JSON serialization
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        return records
    except Exception as e:
        print(f"Error getting data: {e}")
        return []

def get_filters():
    """Get filter options"""
    try:
        ensure_table_exists('tally_data')
        
        filters = {}
        
        # Get owners
        df = pd.read_sql("SELECT DISTINCT owner FROM tally_data WHERE owner IS NOT NULL", engine)
        filters['owners'] = df['owner'].tolist()
        
        # Get counterparties
        df = pd.read_sql("SELECT DISTINCT counterparty FROM tally_data WHERE counterparty IS NOT NULL", engine)
        filters['counterparties'] = df['counterparty'].tolist()
        
        # Get months
        df = pd.read_sql("SELECT DISTINCT statement_month FROM tally_data WHERE statement_month IS NOT NULL", engine)
        filters['months'] = df['statement_month'].tolist()
        
        # Get years
        df = pd.read_sql("SELECT DISTINCT statement_year FROM tally_data WHERE statement_year IS NOT NULL", engine)
        filters['years'] = df['statement_year'].tolist()
        
        return filters
    except Exception as e:
        print(f"Error getting filters: {e}")
        return {}

def get_unmatched_data():
    """Get all unmatched transactions"""
    try:
        ensure_table_exists('tally_data')
        
        sql = """
        SELECT * FROM tally_data 
        WHERE match_status = 'unmatched' OR match_status IS NULL
        ORDER BY Date DESC
        """
        
        df = pd.read_sql(sql, engine)
        
        # If no data in database, return empty list
        if len(df) == 0:
            print("No data found in database. Please upload files first.")
            return []
        
        # Convert to records and handle NaN values
        records = df.to_dict('records')
        
        # Replace NaN values with None for JSON serialization
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
            
        return records
    except Exception as e:
        print(f"Error getting unmatched data: {e}")
        return []

def extract_po(particulars):
    po_pattern = r'[A-Z]+/PO/\d+/\d+/\d+'
    match = re.search(po_pattern, str(particulars))
    return match.group(0) if match else None

def extract_lc(particulars):
    lc_pattern = r'L/C-\d+(?:/\d+)+'
    match = re.search(lc_pattern, str(particulars))
    return match.group(0) if match else None

# --- OLD MATCHING LOGIC COMMENTED OUT ---
# def find_matches(data):
#     """Find matching transactions based on amount and keywords"""
#     if not data:
#         print("No data to match")
#         return []
        
#     matches = []
    
#     # Separate Steel credits and GeoTex debits
#     steel_credits = []
#     geotex_debits = []
    
#     for r in data:
#         if r.get('owner') == 'Steel':
#             credit = r.get('Credit')
#             debit = r.get('Debit')
#             # Check if Credit has a value and Debit is None/NaN
#             if credit and credit > 0 and (debit is None or pd.isna(debit) or debit == 0):
#                 steel_credits.append(r)
#         elif r.get('owner') == 'GeoTex':
#             debit = r.get('Debit')
#             credit = r.get('Credit')
#             # Check if Debit has a value and Credit is None/NaN
#             if debit and debit > 0 and (credit is None or pd.isna(credit) or credit == 0):
#                 geotex_debits.append(r)
    
#     print(f"Found {len(steel_credits)} Steel credits and {len(geotex_debits)} GeoTex debits")
    
#     # Match Steel credits with GeoTex debits
#     for steel_record in steel_credits:
#         steel_amount = float(steel_record['Credit'])  # No rounding
        
#         # Find matching amount in GeoTex debits
#         for geotex_record in geotex_debits:
#             geotex_amount = float(geotex_record['Debit'])  # No rounding
            
#             if steel_amount == geotex_amount:  # Exact match
#                 # Calculate keyword similarity
#                 similarity, keywords = calculate_keyword_similarity(
#                     steel_record.get('Particulars', ''),
#                     geotex_record.get('Particulars', '')
#                 )
                
#                 # Check if this is a PO reference match (similarity = 1.0)
#                 if similarity == 1.0:
#                     # PO reference exact match - confirmed match
#                     matches.append({
#                         'debit_id': geotex_record.get('uid'),
#                         'credit_id': steel_record.get('uid'),
#                         'similarity': similarity,
#                         'amount': str(steel_amount),
#                         'match_type': 'po_reference',
#                         'matching_keywords': keywords
#                     })
#                 elif similarity > 0.1:  # Regular keyword match
#                     matches.append({
#                         'debit_id': geotex_record.get('uid'),
#                         'credit_id': steel_record.get('uid'),
#                         'similarity': similarity,
#                         'amount': str(steel_amount),
#                         'match_type': 'keyword',
#                         'matching_keywords': keywords
#                     })
    
#     print(f"Found {len(matches)} matches")
#     return matches

# def calculate_keyword_similarity(text1, text2):
#     """Calculate similarity between two text fields and return matching keywords"""
#     if not text1 or not text2:
#         return 0, ""
    
#     # HIERARCHICAL MATCHING - Check in priority order
    
#     # 1. EXACT PARTICULARS MATCH (Highest Priority)
#     if str(text1).strip() == str(text2).strip():
#         return 1.0, "Particulars exact match"
    
#     # 2. PO REFERENCE MATCH (Second Priority)
#     import re
#     po_pattern = r'.*/PO/[^/]*/[^/]*/[^/]*'
    
#     po1_match = re.search(po_pattern, str(text1))
#     po2_match = re.search(po_pattern, str(text2))
    
#     if po1_match and po2_match:
#         po1_ref = po1_match.group(0)
#         po2_ref = po2_match.group(0)
        
#         # Extract the core PO reference (ending with a number, before any dash or extra text)
#         def extract_core_po(po_text):
#             # Match pattern like FOB/PO/2023/8/5023 or similar, ending with digits
#             m = re.search(r'([A-Z]+/PO/\d+/\d+/\d+)', po_text)
#             if m:
#                 return m.group(1)
#             # fallback: match up to last digit group
#             m = re.search(r'([A-Z]+/PO/[^/]+/[^/]+/\d+)', po_text)
#             if m:
#                 return m.group(1)
#             return po_text
        
#         core_po1 = extract_core_po(po1_ref)
#         core_po2 = extract_core_po(po2_ref)
        
#         if core_po1 == core_po2:
#             return 1.0, core_po1
    
#     # 3. L/C REFERENCE MATCH (Third Priority)
#     lc_pattern = r'L/C-([^/\s]+(?:\/[^/\s]+)*)'
#     lc1_match = re.search(lc_pattern, str(text1))
#     lc2_match = re.search(lc_pattern, str(text2))
    
#     if lc1_match and lc2_match:
#         # Extract the core L/C reference (ending with a number, before any dash or extra text)
#         def extract_core_lc(lc_text):
#             # Match pattern like L/C-187724010124/24, ending with digits
#             m = re.search(r'(L/C-\d+(?:/\d+)+)', lc_text)
#             if m:
#                 return m.group(1)
#             # fallback: match up to last digit group
#             m = re.search(r'(L/C-[^/]+(?:/[^/]+)*?/\d+)', lc_text)
#             if m:
#                 return m.group(1)
#             return lc_text
        
#         lc1_ref = extract_core_lc(lc1_match.group(0))
#         lc2_ref = extract_core_lc(lc2_match.group(0))
        
#         if lc1_ref == lc2_ref:
#             return 1.0, lc2_ref
    
#     # 4. REGULAR KEYWORD MATCH (Lowest Priority)
#     # Extract keywords (simple approach)
#     keywords1 = set(str(text1).lower().split())
#     keywords2 = set(str(text2).lower().split())
    
#     # Remove common words
#     common_words = {'the', 'and', 'or', 'to', 'from', 'for', 'of', 'in', 'on', 'at', 'by', 'as', 'a', 'an', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'payment', 'amount', 'paid'}
#     keywords1 = keywords1 - common_words
#     keywords2 = keywords2 - common_words
    
#     if not keywords1 or not keywords2:
#         return 0, ""
    
#     # Find matching keywords
#     matching_keywords = keywords1.intersection(keywords2)
    
#     # Special handling for loan-related keywords
#     loan_keywords = {'loan', 'interunit', 'inter', 'unit', 'fund', 'transfer', 'steel', 'geotex', 'geo', 'textile', 'amount', 'received', 'paid', 'given', 'received'}
    
#     # Boost similarity if loan keywords are present
#     loan_intersection = keywords1.intersection(keywords2).intersection(loan_keywords)
#     if loan_intersection:
#         # Add bonus for loan keywords
#         base_similarity = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
#         loan_bonus = len(loan_intersection) * 0.1
#         similarity = min(1.0, base_similarity + loan_bonus)
#     else:
#         intersection = keywords1.intersection(keywords2)
#         union = keywords1.union(keywords2)
#         similarity = len(intersection) / len(union) if union else 0
    
#     # Return the matching keywords separated by semicolon and space
#     matching_keywords = keywords1.intersection(keywords2)
#     return similarity, "; ".join(matching_keywords)


def find_matches(data):
    """Match only if Lender Debit == Borrower Credit AND PO or LC reference matches in Particulars."""
    if not data:
        print("No data to match")
        return []
    matches = []
    lenders = [r for r in data if r.get('Debit') and r['Debit'] > 0]
    borrowers = [r for r in data if r.get('Credit') and r['Credit'] > 0]
    for lender in lenders:
        lender_po = extract_po(lender.get('Particulars', ''))
        lender_lc = extract_lc(lender.get('Particulars', ''))
        for borrower in borrowers:
            if float(lender['Debit']) == float(borrower['Credit']):
                borrower_po = extract_po(borrower.get('Particulars', ''))
                borrower_lc = extract_lc(borrower.get('Particulars', ''))
                # PO match
                if lender_po and borrower_po and lender_po == borrower_po:
                    matches.append({
                        'lender_uid': lender['uid'],
                        'borrower_uid': borrower['uid'],
                        'amount': lender['Debit'],
                        'match_type': 'PO',
                        'po': lender_po
                    })
                # LC match
                elif lender_lc and borrower_lc and lender_lc == borrower_lc:
                    matches.append({
                        'lender_uid': lender['uid'],
                        'borrower_uid': borrower['uid'],
                        'amount': lender['Debit'],
                        'match_type': 'LC',
                        'lc': lender_lc
                    })
    print(f"Found {len(matches)} matches (Debit==Credit and PO/LC match)")
    return matches

def update_matches(matches):
    """Update database with matched records (no prefix in keywords field)"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        for match in matches:
            # Store only the PO or LC value in keywords
            if match['match_type'] == 'PO':
                keywords = match['po']
            elif match['match_type'] == 'LC':
                keywords = match['lc']
            else:
                keywords = ''
            # Update the borrower (Credit) record - point to lender
            conn.execute(text("""
                UPDATE tally_data 
                SET matched_with = :matched_with, 
                    match_status = 'matched', 
                    match_score = NULL, 
                    reconciliation_date = NOW(),
                    keywords = :keywords
                WHERE uid = :borrower_uid
            """), {
                'matched_with': match['lender_uid'],
                'keywords': keywords,
                'borrower_uid': match['borrower_uid']
            })
            # Update the lender (Debit) record - point to borrower
            conn.execute(text("""
                UPDATE tally_data 
                SET matched_with = :matched_with, 
                    match_status = 'matched', 
                    match_score = NULL, 
                    reconciliation_date = NOW(),
                    keywords = :keywords
                WHERE uid = :lender_uid
            """), {
                'matched_with': match['borrower_uid'],
                'keywords': keywords,
                'lender_uid': match['lender_uid']
            })
        conn.commit()

def get_matched_data():
    """Get matched transactions for display"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                t1.*,
                t2.owner as matched_owner, 
                t2.counterparty as matched_counterparty,
                t2.Particulars as matched_particulars, 
                t2.Date as matched_date,
                t2.Debit as matched_Debit, 
                t2.Credit as matched_Credit,
                t2.keywords as matched_keywords,
                t2.uid as matched_uid,
                t2.Vch_Type as matched_Vch_Type
            FROM tally_data t1
            LEFT JOIN tally_data t2 ON t1.matched_with = t2.uid
            WHERE (t1.match_status = 'matched' OR t1.match_status = 'confirmed')
            AND t1.matched_with IS NOT NULL
            ORDER BY t1.reconciliation_date DESC
        """))
        
        records = []
        for row in result:
            record = dict(row._mapping)
            records.append(record)
        
        return records

def update_match_status(uid, status, confirmed_by=None):
    """Update match status (accepted/rejected)"""
    try:
        with engine.connect() as conn:
            if status == 'rejected':
                # First, get the matched_with value
                sql_get_matched = """
                SELECT matched_with FROM tally_data WHERE uid = :uid
                """
                result = conn.execute(text(sql_get_matched), {'uid': uid})
                matched_record = result.fetchone()
                
                if matched_record and matched_record[0]:
                    matched_with_uid = matched_record[0]
                    
                    # Reset the main record
                    sql_reset_main = """
                    UPDATE tally_data 
                    SET match_status = 'unmatched', 
                        matched_with = NULL,
                        match_score = NULL,
                        reconciliation_date = NULL
                    WHERE uid = :uid
                    """
                    conn.execute(text(sql_reset_main), {'uid': uid})
                    
                    # Reset the matched record
                    sql_reset_matched = """
                    UPDATE tally_data 
                    SET match_status = 'unmatched', 
                        matched_with = NULL,
                        match_score = NULL,
                        reconciliation_date = NULL
                    WHERE uid = :matched_with_uid
                    """
                    conn.execute(text(sql_reset_matched), {'matched_with_uid': matched_with_uid})
                    
                else:
                    # Just reset the main record if no match found
                    sql_reset_main = """
                    UPDATE tally_data 
                    SET match_status = 'unmatched', 
                        matched_with = NULL,
                        match_score = NULL,
                        reconciliation_date = NULL
                    WHERE uid = :uid
                    """
                    conn.execute(text(sql_reset_main), {'uid': uid})
                
            else:
                # For confirmed status, first get the matched_with value
                sql_get_matched = """
                SELECT matched_with FROM tally_data WHERE uid = :uid
                """
                result = conn.execute(text(sql_get_matched), {'uid': uid})
                matched_record = result.fetchone()
                
                if matched_record and matched_record[0]:
                    matched_with_uid = matched_record[0]
                    
                    # Update the main record
                    sql_update_main = """
                    UPDATE tally_data 
                    SET match_status = :status, 
                        reconciliation_date = NOW(),
                        confirmed_by = :confirmed_by
                    WHERE uid = :uid
                    """
                    conn.execute(text(sql_update_main), {
                        'status': status,
                        'confirmed_by': confirmed_by,
                        'uid': uid
                    })
                    
                    # Update the matched record
                    sql_update_matched = """
                    UPDATE tally_data 
                    SET match_status = :status, 
                        reconciliation_date = NOW(),
                        confirmed_by = :confirmed_by
                    WHERE uid = :matched_with_uid
                    """
                    conn.execute(text(sql_update_matched), {
                        'status': status,
                        'confirmed_by': confirmed_by,
                        'matched_with_uid': matched_with_uid
                    })
                else:
                    # Just update the main record if no match found
                    sql_update_main = """
                    UPDATE tally_data 
                    SET match_status = :status, 
                        reconciliation_date = NOW(),
                        confirmed_by = :confirmed_by
                    WHERE uid = :uid
                    """
                    conn.execute(text(sql_update_main), {
                        'status': status,
                        'confirmed_by': confirmed_by,
                        'uid': uid
                    })
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"Error updating match status: {e}")
        return False

def get_pending_matches():
    """Get matches that need user confirmation"""
    try:
        ensure_table_exists('tally_data')
        
        sql = """
        SELECT t1.*, t2.owner as matched_owner, t2.counterparty as matched_counterparty,
               t2.Particulars as matched_particulars, t2.Date as matched_date,
               t2.Debit as matched_Debit, t2.Credit as matched_Credit
        FROM tally_data t1
        LEFT JOIN tally_data t2 ON t1.matched_with = t2.uid
        WHERE t1.match_status = 'matched' AND t1.confirmed_by IS NULL
        ORDER BY t1.reconciliation_date DESC
        """
        
        df = pd.read_sql(sql, engine)
        
        # Convert to records and handle NaN values
        records = df.to_dict('records')
        
        # Replace NaN values with None for JSON serialization
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        return records
    except Exception as e:
        print(f"Error getting pending matches: {e}")
        return []

def get_confirmed_matches():
    """Get confirmed matches"""
    try:
        ensure_table_exists('tally_data')
        
        sql = """
        SELECT t1.*, t2.owner as matched_owner, t2.counterparty as matched_counterparty,
               t2.Particulars as matched_particulars, t2.Date as matched_date,
               t2.Debit as matched_Debit, t2.Credit as matched_Credit
        FROM tally_data t1
        LEFT JOIN tally_data t2 ON t1.matched_with = t2.uid
        WHERE t1.match_status = 'confirmed' AND t1.confirmed_by IS NOT NULL
        ORDER BY t1.reconciliation_date DESC
        """
        
        df = pd.read_sql(sql, engine)
        
        # Convert to records and handle NaN values
        records = df.to_dict('records')
        
        # Replace NaN values with None for JSON serialization
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        return records
    except Exception as e:
        print(f"Error getting confirmed matches: {e}")
        return [] 

def reset_match_status():
    """Reset all match status columns to clear previous matches"""
    try:
        with engine.connect() as conn:
            # Reset all match-related columns
            reset_query = text("""
                UPDATE tally_data 
                SET match_status = NULL, 
                    matched_with = NULL, 
                    match_score = NULL, 
                    keywords = NULL,
                    confirmed_by = NULL
            """)
            conn.execute(reset_query)
            conn.commit()
            return True
    except Exception as e:
        print(f"Error resetting match status: {e}")
        return False 

def get_column_order():
    """Get the exact column order from the database"""
    try:
        ensure_table_exists('tally_data')
        with engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM tally_data"))
            columns = [row[0] for row in result]
        return columns
    except Exception as e:
        print(f"Error getting column order: {e}")
        return [] 