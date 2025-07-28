from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import pandas as pd
from werkzeug.utils import secure_filename
from parser.tally_parser_interunit_loan_recon import parse_tally_file
import database

app = Flask(__name__)

# Create upload folder
os.makedirs('uploads', exist_ok=True)

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
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # Parse file
        df = parse_tally_file(filepath, sheet_name)
        
        # Save to database
        if database.save_data(df):
            os.remove(filepath)
            return jsonify({
                'message': 'File processed successfully',
                'rows_processed': len(df)
            })
        else:
            return jsonify({'error': 'Failed to save data'}), 500
            
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
    """Reconcile interunit transactions"""
    try:
        # Get all unmatched transactions
        data = database.get_unmatched_data()
        
        # Perform matching logic
        matches = database.find_matches(data)
        
        # Update database with matches
        database.update_matches(matches)
        
        return jsonify({
            'message': 'Reconciliation completed',
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
        # Build rows matching the table structure exactly
        export_rows = []
        for _, row in df.iterrows():
            # Determine which record is Steel and which is GeoTex (same logic as frontend)
            if row.get('lender') == 'Steel':
                # This record is Steel, get GeoTex from matched data
                steel_uid = row.get('uid')
                steel_date = row.get('Date')
                steel_particulars = row.get('Particulars')
                steel_credit = row.get('Credit')
                steel_debit = row.get('Debit')
                
                geotex_uid = row.get('matched_uid')
                geotex_date = row.get('matched_date')
                geotex_particulars = row.get('matched_particulars')
                geotex_credit = row.get('matched_Credit')
                geotex_debit = row.get('matched_Debit')
            elif row.get('matched_lender') == 'Steel':
                # This record is GeoTex, get Steel from matched data
                geotex_uid = row.get('uid')
                geotex_date = row.get('Date')
                geotex_particulars = row.get('Particulars')
                geotex_credit = row.get('Credit')
                geotex_debit = row.get('Debit')
                
                steel_uid = row.get('matched_uid')
                steel_date = row.get('matched_date')
                steel_particulars = row.get('matched_particulars')
                steel_credit = row.get('matched_Credit')
                steel_debit = row.get('matched_Debit')
            else:
                # Fallback: assume current record is Steel
                steel_uid = row.get('uid')
                steel_date = row.get('Date')
                steel_particulars = row.get('Particulars')
                steel_credit = row.get('Credit')
                steel_debit = row.get('Debit')
                
                geotex_uid = row.get('matched_uid')
                geotex_date = row.get('matched_date')
                geotex_particulars = row.get('matched_particulars')
                geotex_credit = row.get('matched_Credit')
                geotex_debit = row.get('matched_Debit')
            
            export_rows.append({
                # Steel (Lender) section
                'Steel UID': steel_uid,
                'Steel Date': steel_date,
                'Steel Particulars': steel_particulars,
                'Steel Credit': steel_credit,
                'Steel Debit': steel_debit,
                # GeoTex (Borrower) section
                'GeoTex UID': geotex_uid,
                'GeoTex Date': geotex_date,
                'GeoTex Particulars': geotex_particulars,
                'GeoTex Credit': geotex_credit,
                'GeoTex Debit': geotex_debit,
                # Match info
                'Match Score': row.get('match_score'),
                'Keywords': row.get('keywords')
            })
        
        export_df = pd.DataFrame(export_rows)
        export_filename = f"matched_transactions_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_path = os.path.join('uploads', export_filename)
        export_df.to_excel(export_path, index=False)
        return send_from_directory('uploads', export_filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 