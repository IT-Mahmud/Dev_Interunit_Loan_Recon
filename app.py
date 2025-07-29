from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import pandas as pd
from werkzeug.utils import secure_filename
from parser.tally_parser_interunit_loan_recon import parse_tally_file
import database
import threading

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
    """Export data to Excel"""
    try:
        filters = {}
        if request.args.get('owner'):
            filters['owner'] = request.args.get('owner')
        if request.args.get('counterparty'):
            filters['counterparty'] = request.args.get('counterparty')
        if request.args.get('statement_month'):
            filters['statement_month'] = request.args.get('statement_month')
        if request.args.get('statement_year'):
            filters['statement_year'] = request.args.get('statement_year')
        
        data = database.get_data(filters)
        
        if not data:
            return jsonify({'error': 'No data found'}), 404
        
        # Convert to DataFrame and export
        df = pd.DataFrame(data)
        export_filename = f"export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
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
            # Determine which is lender (Credit side) vs borrower (Debit side)
            if first_row.get('Credit') and first_row.get('Credit') > 0:
                # Main record is lender (Credit side)
                lender_name = first_row.get('owner', 'Lender')
                borrower_name = first_row.get('matched_owner', 'Borrower')
            elif first_row.get('matched_Credit') and first_row.get('matched_Credit') > 0:
                # Matched record is lender (Credit side)
                lender_name = first_row.get('matched_owner', 'Lender')
                borrower_name = first_row.get('owner', 'Borrower')
            else:
                # Fallback to original logic
                if first_row.get('owner'):
                    lender_name = first_row['owner']
                if first_row.get('matched_owner') and first_row['matched_owner'] != first_row.get('owner'):
                    borrower_name = first_row['matched_owner']
                elif first_row.get('counterparty'):
                    borrower_name = first_row['counterparty']
            
            # Build rows matching the table structure exactly
            export_rows = []
            for _, row in df.iterrows():
                # Determine which record is lender and which is borrower (same logic as frontend)
                if row.get('owner') == lender_name:
                    # This record is lender, get borrower from matched data
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
                elif row.get('matched_owner') == lender_name:
                    # This record is borrower, get lender from matched data
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
                else:
                    # Fallback: assume current record is lender
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
                
                export_rows.append({
                    # Lender section
                    f'{lender_name} UID': lender_uid,
                    f'{lender_name} Date': lender_date,
                    f'{lender_name} Particulars': lender_particulars,
                    f'{lender_name} Credit': lender_credit,
                    f'{lender_name} Debit': lender_debit,
                    f'{lender_name} Vch_Type': lender_vch_type,
                    # Borrower section
                    f'{borrower_name} UID': borrower_uid,
                    f'{borrower_name} Date': borrower_date,
                    f'{borrower_name} Particulars': borrower_particulars,
                    f'{borrower_name} Credit': borrower_credit,
                    f'{borrower_name} Debit': borrower_debit,
                    f'{borrower_name} Vch_Type': borrower_vch_type,
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
                
                # Format Particulars columns (columns C and H - 3rd and 8th columns)
                from openpyxl.styles import Alignment
                
                # Steel Particulars column (C)
                worksheet.column_dimensions['C'].width = 100
                for cell in worksheet['C']:
                    cell.alignment = Alignment(wrap_text=True)
                
                # GeoTex Particulars column (H)
                worksheet.column_dimensions['H'].width = 100
                for cell in worksheet['H']:
                    cell.alignment = Alignment(wrap_text=True)
                
                # Autofit all other columns
                for column in worksheet.columns:
                    column_letter = column[0].column_letter
                    if column_letter not in ['C', 'H']:  # Skip Particulars columns
                        max_length = 0
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)  # Add padding, max 50
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return send_from_directory('uploads', export_filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 