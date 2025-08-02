from sqlalchemy import create_engine, inspect, text
import pandas as pd
from core.config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB
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
    """Get available filters for the data"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    filters = {}
    
    # Get lenders
    df = pd.read_sql("SELECT DISTINCT lender FROM tally_data WHERE lender IS NOT NULL", engine)
    filters['lenders'] = df['lender'].tolist()
    
    # Get borrowers
    df = pd.read_sql("SELECT DISTINCT borrower FROM tally_data WHERE borrower IS NOT NULL", engine)
    filters['borrowers'] = df['borrower'].tolist()
    
    # Get statement months
    df = pd.read_sql("SELECT DISTINCT statement_month FROM tally_data WHERE statement_month IS NOT NULL", engine)
    filters['statement_months'] = df['statement_month'].tolist()
    
    # Get statement years
    df = pd.read_sql("SELECT DISTINCT statement_year FROM tally_data WHERE statement_year IS NOT NULL", engine)
    filters['statement_years'] = df['statement_year'].tolist()
    
    return filters

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




def find_matches(data):
    """Match only if Lender Debit == Borrower Credit AND PO or LC reference matches in Particulars."""
    if not data:
        print("No data to match")
        return []
    
    lenders = [r for r in data if r.get('Debit') and r['Debit'] > 0]
    borrowers = [r for r in data if r.get('Credit') and r['Credit'] > 0]
    
    matches = []
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
                t2.lender as matched_lender, 
                t2.borrower as matched_borrower,
                t2.Particulars as matched_particulars, 
                t2.Date as matched_date,
                t2.Debit as matched_Debit, 
                t2.Credit as matched_Credit,
                t2.keywords as matched_keywords,
                t2.uid as matched_uid,
                t2.Vch_Type as matched_Vch_Type,
                t2.role as matched_role
            FROM tally_data t1
            LEFT JOIN tally_data t2 ON t1.matched_with = t2.uid
            WHERE t1.match_status = 'matched'
            ORDER BY t1.date_matched DESC
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
                        keywords = NULL
                    WHERE uid = :uid
                    """
                    conn.execute(text(sql_reset_main), {'uid': uid})
                    
                    # Reset the matched record
                    sql_reset_matched = """
                    UPDATE tally_data 
                    SET match_status = 'unmatched', 
                        matched_with = NULL,
                        keywords = NULL
                    WHERE uid = :matched_with_uid
                    """
                    conn.execute(text(sql_reset_matched), {'matched_with_uid': matched_with_uid})
                    
                else:
                    # Just reset the main record if no match found
                    sql_reset_main = """
                    UPDATE tally_data 
                    SET match_status = 'unmatched', 
                        matched_with = NULL,
                        keywords = NULL
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
                        date_matched = NOW(),
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
                        date_matched = NOW(),
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
                        date_matched = NOW(),
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
    """Get pending matches"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                t1.*, t2.lender as matched_lender, t2.borrower as matched_borrower,
               t2.Particulars as matched_particulars, t2.Date as matched_date,
                t2.Debit as matched_Debit, t2.Credit as matched_Credit,
                t2.keywords as matched_keywords, t2.uid as matched_uid,
                t2.Vch_Type as matched_Vch_Type, t2.role as matched_role
        FROM tally_data t1
            LEFT JOIN tally_data t2 ON t1.matched_with = t2.uid
            WHERE t1.match_status = 'matched'
            ORDER BY t1.date_matched DESC
        """))
        
        records = []
        for row in result:
            record = dict(row._mapping)
            records.append(record)
        
        return records

def get_confirmed_matches():
    """Get confirmed matches"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                t1.*, t2.lender as matched_lender, t2.borrower as matched_borrower,
               t2.Particulars as matched_particulars, t2.Date as matched_date,
                t2.Debit as matched_Debit, t2.Credit as matched_Credit,
                t2.keywords as matched_keywords, t2.uid as matched_uid,
                t2.Vch_Type as matched_Vch_Type, t2.role as matched_role
        FROM tally_data t1
            LEFT JOIN tally_data t2 ON t1.matched_with = t2.uid
            WHERE t1.match_status = 'confirmed'
            ORDER BY t1.date_matched DESC
        """))
        
        records = []
        for row in result:
            record = dict(row._mapping)
            records.append(record)
        
        return records

def reset_match_status():
    """Reset all match status columns to clear previous matches"""
    try:
        with engine.connect() as conn:
            # Reset all match-related columns
            reset_query = text("""
                UPDATE tally_data 
                SET match_status = NULL, 
                    matched_with = NULL, 
                    keywords = NULL
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

def get_company_pairs():
    """Get available company pairs for reconciliation based on company names and statement periods"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        # Get all unique company combinations with their statement periods
        # Use LEAST and GREATEST to ensure consistent ordering and avoid duplicates
        result = conn.execute(text("""
            SELECT DISTINCT 
                LEAST(lender, borrower) as company1,
                GREATEST(lender, borrower) as company2,
                statement_month,
                statement_year,
                COUNT(*) as transaction_count
            FROM tally_data 
            WHERE lender IS NOT NULL AND borrower IS NOT NULL
            AND lender != borrower
            GROUP BY LEAST(lender, borrower), GREATEST(lender, borrower), statement_month, statement_year
            HAVING transaction_count >= 2
            ORDER BY statement_year DESC, statement_month DESC, company1, company2
        """))
        
        pairs = []
        for row in result:
            pairs.append({
                'lender_company': row.company1,
                'borrower_company': row.company2,
                'month': row.statement_month,
                'year': row.statement_year,
                'transaction_count': row.transaction_count,
                'description': f"{row.company1} ↔ {row.company2} ({row.statement_month} {row.statement_year})"
            })
        
        return pairs

def detect_company_pairs():
    """Smart scan to detect company pairs based on the pattern in the data"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        # Get all unique combinations of current company and counterparty
        result = conn.execute(text("""
            SELECT DISTINCT 
                lender as current_company,
                borrower as counterparty,
                statement_month,
                statement_year,
                COUNT(*) as transaction_count
            FROM tally_data 
            WHERE lender IS NOT NULL AND borrower IS NOT NULL
            AND lender != borrower
            GROUP BY lender, borrower, statement_month, statement_year
            HAVING transaction_count >= 1
            ORDER BY statement_year DESC, statement_month DESC, lender, borrower
        """))
        
        # Create a mapping of detected pairs
        detected_pairs = {}
        
        for row in result:
            current_company = row.current_company
            counterparty = row.counterparty
            month = row.statement_month
            year = row.statement_year
            
            # Create a unique key for this combination
            pair_key = f"{current_company}_{counterparty}_{month}_{year}"
            opposite_key = f"{counterparty}_{current_company}_{month}_{year}"
            
            # If we haven't seen this pair or its opposite, add it
            if pair_key not in detected_pairs and opposite_key not in detected_pairs:
                detected_pairs[pair_key] = {
                    'current_company': current_company,
                    'counterparty': counterparty,
                    'month': month,
                    'year': year,
                    'transaction_count': row.transaction_count,
                    'description': f"{current_company} ↔ {counterparty} ({month} {year})",
                    'opposite_pair': {
                        'current_company': counterparty,
                        'counterparty': current_company,
                        'month': month,
                        'year': year,
                        'description': f"{counterparty} ↔ {current_company} ({month} {year})"
                    }
                }
        
        return list(detected_pairs.values())

def get_manual_company_pairs():
    """Get manually defined company pairs from a configuration"""
    from core.config import MANUAL_COMPANY_PAIRS
    
    # Generate opposite pairs automatically
    all_pairs = {}
    for company1, company2 in MANUAL_COMPANY_PAIRS.items():
        if company1 != company2:
            # Add the original pair
            all_pairs[f"{company1}_{company2}"] = (company1, company2)
            # Add the opposite pair
            all_pairs[f"{company2}_{company1}"] = (company2, company1)
    
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        pairs = []
        
        # Get all unique statement periods
        result = conn.execute(text("""
            SELECT DISTINCT statement_month, statement_year
            FROM tally_data 
            WHERE statement_month IS NOT NULL AND statement_year IS NOT NULL
            ORDER BY statement_year DESC, statement_month DESC
        """))
        
        for period_row in result:
            month = period_row.statement_month
            year = period_row.statement_year
            
            # For each manual pair, check if both companies exist in this period
            for pair_key, (company1, company2) in all_pairs.items():
                # Check if both companies have data in this period
                count_result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM tally_data 
                    WHERE (lender = :company1 OR borrower = :company1 OR lender = :company2 OR borrower = :company2)
                    AND statement_month = :month AND statement_year = :year
                """), {
                    'company1': company1,
                    'company2': company2,
                    'month': month,
                    'year': year
                })
                
                count = count_result.fetchone()[0]
                if count > 0:
                    pairs.append({
                        'lender_company': company1,
                        'borrower_company': company2,
                        'month': month,
                        'year': year,
                        'transaction_count': count,
                        'description': f"{company1} ↔ {company2} ({month} {year})",
                        'type': 'manual'
                    })
        
        return pairs

def get_unmatched_data_by_companies(lender_company, borrower_company, month=None, year=None):
    """Get unmatched transactions filtered by company names and optionally by statement period"""
    engine = create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    )
    
    with engine.connect() as conn:
        # Build query based on provided parameters
        # Look for transactions where either company appears as lender or borrower
        query = """
            SELECT * FROM tally_data 
            WHERE (match_status = 'unmatched' OR match_status IS NULL)
            AND (
                (lender = :lender_company AND borrower = :borrower_company)
                OR (lender = :borrower_company AND borrower = :lender_company)
            )
        """
        params = {
            'lender_company': lender_company,
            'borrower_company': borrower_company
        }
        
        if month:
            query += " AND statement_month = :month"
            params['month'] = month
        
        if year:
            query += " AND statement_year = :year"
            params['year'] = year
        
        query += " ORDER BY Date"
        
        result = conn.execute(text(query), params)
        
        records = []
        for row in result:
            record = dict(row._mapping)
            records.append(record)
        
        return records 

def get_data_by_pair_id(pair_id):
    """Get all data for a specific pair ID"""
    try:
        ensure_table_exists('tally_data')
        
        sql = """
        SELECT * FROM tally_data 
        WHERE pair_id = :pair_id
        ORDER BY Date DESC
        """
        
        df = pd.read_sql(sql, engine, params={'pair_id': pair_id})
        
        # Convert to records and handle NaN values
        records = df.to_dict('records')
        
        # Replace any remaining NaN values with None for JSON serialization
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        return records
    except Exception as e:
        print(f"Error getting data by pair_id: {e}")
        return []

def get_all_pair_ids():
    """Get all unique pair IDs"""
    try:
        ensure_table_exists('tally_data')
        
        sql = """
        SELECT DISTINCT pair_id, 
               COUNT(*) as record_count,
               MIN(input_date) as upload_date
        FROM tally_data 
        WHERE pair_id IS NOT NULL
        GROUP BY pair_id
        ORDER BY upload_date DESC
        """
        
        df = pd.read_sql(sql, engine)
        
        pairs = []
        for _, row in df.iterrows():
            pairs.append({
                'pair_id': row['pair_id'],
                'record_count': row['record_count'],
                'upload_date': row['upload_date']
            })
        
        return pairs
    except Exception as e:
        print(f"Error getting pair IDs: {e}")
        return []

def get_unmatched_data_by_pair_id(pair_id):
    """Get unmatched transactions for a specific pair ID"""
    try:
        ensure_table_exists('tally_data')
        
        sql = """
        SELECT * FROM tally_data 
        WHERE pair_id = :pair_id
        AND (match_status = 'unmatched' OR match_status IS NULL)
        ORDER BY Date DESC
        """
        
        df = pd.read_sql(sql, engine, params={'pair_id': pair_id})
        
        # Convert to records and handle NaN values
        records = df.to_dict('records')
        
        # Replace any remaining NaN values with None for JSON serialization
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        return records
    except Exception as e:
        print(f"Error getting unmatched data by pair_id: {e}")
        return [] 