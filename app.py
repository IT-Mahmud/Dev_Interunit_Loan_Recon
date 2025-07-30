from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import pandas as pd
from werkzeug.utils import secure_filename
from parser.tally_parser_interunit_loan_recon import parse_tally_file
import database
import threading
from openpyxl.styles import Alignment

app = Flask(__name__)

# Create upload folder
os.makedirs('uploads', exist_ok=True)

RECENT_UPLOADS_FILE = 'recent_uploads.txt'
RECENT_UPLOADS_LIMIT = 10
recent_uploads_lock = threading.Lock()

def record_recent_upload(filename):
    with recent_uploads_lock:
        try:
            if os.path.exists(RECENT_UPLOADS_FILE):
                with open(RECENT_UPLOADS_FILE, 'r', encoding='utf-8') as f:
                    uploads = [line.strip() for line in f if line.strip()]
            else:
                uploads = []
            # Remove if already present
            uploads = [f for f in uploads if f != filename]
            uploads.insert(0, filename)
            uploads = uploads[:RECENT_UPLOADS_LIMIT]
            with open(RECENT_UPLOADS_FILE, 'w', encoding='utf-8') as f:
                for f_name in uploads:
                    f.write(f_name + '\n')
        except Exception as e:
            print(f"Error recording recent upload: {e}")

@app.route('/api/recent-uploads', methods=['GET'])
def get_recent_uploads():
    try:
        if os.path.exists(RECENT_UPLOADS_FILE):
            with open(RECENT_UPLOADS_FILE, 'r', encoding='utf-8') as f:
                uploads = [line.strip() for line in f if line.strip()]
        else:
            uploads = []
        return jsonify({'recent_uploads': uploads})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-recent-uploads', methods=['POST'])
def clear_recent_uploads():
    try:
        if os.path.exists(RECENT_UPLOADS_FILE):
            with open(RECENT_UPLOADS_FILE, 'w', encoding='utf-8') as f:
                f.write('')
        return jsonify({'message': 'Recent uploads cleared.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    """Check if file is Excel"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and process file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        sheet_name = request.form.get('sheet_name', 'Sheet1')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Please upload Excel files only'}), 400
        
        # Save file temporarily
        original_filename = file.filename
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # Record recent upload (store original filename)
        record_recent_upload(original_filename)
        
        # Parse file
        df = parse_tally_file(filepath, sheet_name)
        
        # Save to database
        success, error_msg = database.save_data(df)
        if success:
            os.remove(filepath)
            return jsonify({
                'message': 'File processed successfully',
                'rows_processed': len(df)
            })
        else:
            os.remove(filepath)
            return jsonify({'error': error_msg or 'Failed to save data'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all data"""
    try:
        data = database.get_data()
        # Get column order from database
        column_order = database.get_column_order()
        return jsonify({
            'data': data,
            'column_order': column_order
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/filters', methods=['GET'])
def get_filters():
    """Get filter options"""
    try:
        filters = database.get_filters()
        return jsonify(filters)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export filtered data to Excel"""
    try:
        filters = {}
        if request.args.get('lender'):
            filters['lender'] = request.args.get('lender')
        if request.args.get('borrower'):
            filters['borrower'] = request.args.get('borrower')
        if request.args.get('statement_month'):
            filters['statement_month'] = request.args.get('statement_month')
        if request.args.get('statement_year'):
            filters['statement_year'] = request.args.get('statement_year')
        
        data = database.get_data(filters)
        if not data:
            return jsonify({'error': 'No data found'}), 404
        
        df = pd.DataFrame(data)
        export_filename = f"tally_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_path = os.path.join('uploads', export_filename)
        
        df.to_excel(export_path, index=False)
        
        return send_from_directory('uploads', export_filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reconcile', methods=['POST'])
def reconcile_transactions():
    """Reconcile interunit transactions using new matching logic"""
    try:
        # Get all unmatched transactions
        data = database.get_unmatched_data()
        # Perform matching logic
        matches = database.find_matches(data)
        # Update database with matches
        database.update_matches(matches)
        return jsonify({
            'message': 'Reconciliation complete.',
            'matches_found': len(matches)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches', methods=['GET'])
def get_matches():
    """Get matched transactions"""
    try:
        matches = database.get_matched_data()
        return jsonify({'matches': matches})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pending-matches', methods=['GET'])
def get_pending_matches():
    """Get matches that need user confirmation"""
    try:
        matches = database.get_pending_matches()
        return jsonify({'matches': matches})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/confirmed-matches', methods=['GET'])
def get_confirmed_matches():
    """Get confirmed matches"""
    try:
        matches = database.get_confirmed_matches()
        return jsonify({'matches': matches})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accept-match', methods=['POST'])
def accept_match():
    """Accept a match"""
    try:
        data = request.get_json()
        uid = data.get('uid')
        confirmed_by = data.get('confirmed_by', 'User')
        
        if not uid:
            return jsonify({'error': 'uid is required'}), 400
        
        success = database.update_match_status(uid, 'confirmed', confirmed_by)
        
        if success:
            return jsonify({'message': 'Match accepted successfully'})
        else:
            return jsonify({'error': 'Failed to accept match'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reject-match', methods=['POST'])
def reject_match():
    """Reject a match"""
    try:
        data = request.get_json()
        uid = data.get('uid')
        confirmed_by = data.get('confirmed_by', 'User')
        
        if not uid:
            return jsonify({'error': 'uid is required'}), 400
        
        success = database.update_match_status(uid, 'rejected', confirmed_by)
        
        if success:
            return jsonify({'message': 'Match rejected successfully'})
        else:
            return jsonify({'error': 'Failed to reject match'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-matches', methods=['GET'])
def download_matches():
    """Download matched transactions as Excel (matching table structure)"""
    try:
        matches = database.get_matched_data()
        if not matches:
            return jsonify({'error': 'No matched data found'}), 404
        df = pd.DataFrame(matches)
        # Get dynamic lender/borrower names from the first match
        lender_name = 'Lender'
        borrower_name = 'Borrower'
        if len(df) > 0:
            first_row = df.iloc[0]
            # Determine which is lender (Debit side) vs borrower (Credit side)
            if first_row.get('Debit') and first_row.get('Debit') > 0:
                # Main record is lender (Debit side)
                lender_name = first_row.get('lender', 'Lender')
                borrower_name = first_row.get('matched_lender', 'Borrower')
            elif first_row.get('matched_Debit') and first_row.get('matched_Debit') > 0:
                # Matched record is lender (Debit side)
                lender_name = first_row.get('matched_lender', 'Lender')
                borrower_name = first_row.get('lender', 'Borrower')
            else:
                # Fallback to original logic
                if first_row.get('lender'):
                    lender_name = first_row['lender']
                if first_row.get('matched_lender') and first_row['matched_lender'] != first_row.get('lender'):
                    borrower_name = first_row['matched_lender']
                elif first_row.get('borrower'):
                    borrower_name = first_row['borrower']
            
            # Build rows matching the table structure exactly
            export_rows = []
            for _, row in df.iterrows():
                # Determine which record is lender and which is borrower based on Debit/Credit values
                main_record_debit = float(row.get('Debit', 0) or 0)
                main_record_credit = float(row.get('Credit', 0) or 0)
                matched_record_debit = float(row.get('matched_Debit', 0) or 0)
                matched_record_credit = float(row.get('matched_Credit', 0) or 0)
                
                if main_record_debit > 0:
                    # Main record is Lender (Debit > 0)
                    lender_uid = row.get('uid')
                    lender_date = row.get('Date')
                    lender_particulars = row.get('Particulars')
                    lender_credit = row.get('Credit')
                    lender_debit = row.get('Debit')
                    lender_vch_type = row.get('Vch_Type')
                    
                    borrower_uid = row.get('matched_uid')
                    borrower_date = row.get('matched_date')
                    borrower_particulars = row.get('matched_particulars')
                    borrower_credit = row.get('matched_Credit')
                    borrower_debit = row.get('matched_Debit')
                    borrower_vch_type = row.get('matched_Vch_Type')
                elif matched_record_debit > 0:
                    # Matched record is Lender (Debit > 0)
                    lender_uid = row.get('matched_uid')
                    lender_date = row.get('matched_date')
                    lender_particulars = row.get('matched_particulars')
                    lender_credit = row.get('matched_Credit')
                    lender_debit = row.get('matched_Debit')
                    lender_vch_type = row.get('matched_Vch_Type')
                    
                    borrower_uid = row.get('uid')
                    borrower_date = row.get('Date')
                    borrower_particulars = row.get('Particulars')
                    borrower_credit = row.get('Credit')
                    borrower_debit = row.get('Debit')
                    borrower_vch_type = row.get('Vch_Type')
                else:
                    # Fallback: use the original logic based on lender_name
                    if row.get('lender') == lender_name:
                        lender_uid = row.get('uid')
                        lender_date = row.get('Date')
                        lender_particulars = row.get('Particulars')
                        lender_credit = row.get('Credit')
                        lender_debit = row.get('Debit')
                        lender_vch_type = row.get('Vch_Type')
                        
                        borrower_uid = row.get('matched_uid')
                        borrower_date = row.get('matched_date')
                        borrower_particulars = row.get('matched_particulars')
                        borrower_credit = row.get('matched_Credit')
                        borrower_debit = row.get('matched_Debit')
                        borrower_vch_type = row.get('matched_Vch_Type')
                    else:
                        borrower_uid = row.get('uid')
                        borrower_date = row.get('Date')
                        borrower_particulars = row.get('Particulars')
                        borrower_credit = row.get('Credit')
                        borrower_debit = row.get('Debit')
                        borrower_vch_type = row.get('Vch_Type')
                        
                        lender_uid = row.get('matched_uid')
                        lender_date = row.get('matched_date')
                        lender_particulars = row.get('matched_particulars')
                        lender_credit = row.get('matched_Credit')
                        lender_debit = row.get('matched_Debit')
                        lender_vch_type = row.get('matched_Vch_Type')
                
                # Determine roles based on Debit/Credit values
                if main_record_debit > 0:
                    lender_role = 'Lender'  # Main record has Debit > 0
                    borrower_role = 'Borrower'  # Matched record has Credit > 0
                elif matched_record_debit > 0:
                    lender_role = 'Lender'  # Matched record has Debit > 0
                    borrower_role = 'Borrower'  # Main record has Credit > 0
                else:
                    # Fallback: determine based on actual values
                    lender_role = 'Lender' if lender_debit and float(lender_debit) > 0 else 'Borrower'
                    borrower_role = 'Borrower' if borrower_credit and float(borrower_credit) > 0 else 'Lender'

                # Add Lender Role and Borrower Role columns
                export_rows.append({
                    # Lender section
                    f'{lender_name} UID': lender_uid,
                    f'{lender_name} Date': lender_date,
                    f'{lender_name} Particulars': lender_particulars,
                    f'{lender_name} Credit': lender_credit,
                    f'{lender_name} Debit': lender_debit,
                    f'{lender_name} Vch_Type': lender_vch_type,
                    f'{lender_name} Role': lender_role,
                    # Borrower section
                    f'{borrower_name} UID': borrower_uid,
                    f'{borrower_name} Date': borrower_date,
                    f'{borrower_name} Particulars': borrower_particulars,
                    f'{borrower_name} Credit': borrower_credit,
                    f'{borrower_name} Debit': borrower_debit,
                    f'{borrower_name} Vch_Type': borrower_vch_type,
                    f'{borrower_name} Role': borrower_role,
                    # Match info
                    'Match Score': row.get('match_score'),
                    'Keywords': row.get('keywords')
                })
            
            export_df = pd.DataFrame(export_rows)
            export_filename = f"matched_transactions_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            export_path = os.path.join('uploads', export_filename)
            
            # Export with openpyxl for formatting
            with pd.ExcelWriter(export_path, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Matched Transactions')
                
                # Get the worksheet for formatting
                worksheet = writer.sheets['Matched Transactions']
                
                # Find columns with 'Particulars' in the header
                particulars_cols = [i+1 for i, col in enumerate(export_df.columns) if 'Particulars' in col]

                for col_idx in range(1, len(export_df.columns)+1):
                    col_letter = worksheet.cell(row=1, column=col_idx).column_letter
                    if col_idx in particulars_cols:
                        worksheet.column_dimensions[col_letter].width = 100
                        for cell in worksheet[col_letter]:
                            cell.alignment = Alignment(wrap_text=True)
                    else:
                        max_length = 0
                        for cell in worksheet[col_letter]:
                            try:
                                if cell.value and len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
            
            return send_from_directory('uploads', export_filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 