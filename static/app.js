// Interunit Loan Reconciliation - JavaScript

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    if (document.getElementById('recent-uploads-list')) {
        loadRecentUploads();
    }
});

// Tab switching function
function showTab(tabName) {
    // Hide all tab panes
    const tabPanes = document.querySelectorAll('.tab-pane');
    tabPanes.forEach(pane => {
        pane.style.display = 'none';
    });
    
    // Show selected tab pane
    const selectedPane = document.getElementById('pane-' + tabName);
    if (selectedPane) {
        selectedPane.style.display = 'block';
        
        // If switching to data-table tab, load data
        if (tabName === 'data-table') {
            loadData();
        }
        
        // If switching to reconciliation tab, load company pairs
        if (tabName === 'reconciliation') {
            loadCompanyPairs();
        }
    }
}

// Handle file selection with SheetJS
function handleFileSelect(input, fileNumber) {
    const file = input.files[0];
    const fileChosenSpan = document.getElementById(`file-chosen-${fileNumber}`);
    const sheetRow = document.getElementById(`sheet-row-${fileNumber}`);
    const sheetSelect = sheetRow.querySelector('.sheet-select');
    const parseBtn = document.getElementById('parse-btn');
    
    if (file) {
        // Update file name display
        fileChosenSpan.textContent = file.name;
        
        // Read Excel file with SheetJS
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = new Uint8Array(e.target.result);
                const workbook = XLSX.read(data, { type: 'array' });
                
                // Clear existing options
                sheetSelect.innerHTML = '';
                
                // Add sheet names to dropdown
                workbook.SheetNames.forEach(sheetName => {
                    const option = document.createElement('option');
                    option.value = sheetName;
                    option.textContent = sheetName;
                    sheetSelect.appendChild(option);
                });
                
                // Show sheet selection row
                sheetRow.style.display = 'flex';
                
                // Enable parse button if both files are selected
                checkBothFilesSelected();
                
            } catch (error) {
                console.error('Error reading Excel file:', error);
                fileChosenSpan.textContent = 'Error reading file';
                parseBtn.disabled = true;
            }
        };
        reader.readAsArrayBuffer(file);
    } else {
        fileChosenSpan.textContent = 'No file chosen';
        sheetRow.style.display = 'none';
        parseBtn.disabled = true;
    }
}

function checkBothFilesSelected() {
    const file1 = document.querySelector('input[name="file1"]').files[0];
    const file2 = document.querySelector('input[name="file2"]').files[0];
    const sheet1 = document.getElementById('sheet-select-1').value;
    const sheet2 = document.getElementById('sheet-select-2').value;
    
    const parseBtn = document.getElementById('parse-btn');
    const uploadMsg = document.getElementById('upload-msg');
    
    // Check if both files are selected
    if (file1 && file2) {
        // Check if same file is selected
        if (file1.name === file2.name) {
            uploadMsg.textContent = 'Warning: Same file selected for both companies. Please select different files.';
            uploadMsg.style.color = 'orange';
            parseBtn.disabled = true;
            return;
        } else {
            uploadMsg.textContent = '';
            uploadMsg.style.color = 'red';
        }
    }
    
    parseBtn.disabled = !(file1 && file2 && sheet1 && sheet2);
}

// Handle form submission
document.getElementById('tally-upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    uploadFile();
});

// Upload file function
async function uploadFile() {
    const formData = new FormData();
    const fileInput1 = document.querySelector('input[name="file1"]');
    const fileInput2 = document.querySelector('input[name="file2"]');
    const sheetSelect1 = document.getElementById('sheet-select-1');
    const sheetSelect2 = document.getElementById('sheet-select-2');
    const parseBtn = document.getElementById('parse-btn');
    const uploadMsg = document.getElementById('upload-msg');
    const uploadResult = document.getElementById('upload-result');
    
    if (!fileInput1.files[0] || !fileInput2.files[0]) {
        uploadMsg.textContent = 'Please select both files to upload.';
        return;
    }
    
    if (!sheetSelect1.value || !sheetSelect2.value) {
        uploadMsg.textContent = 'Please select sheets for both files.';
        return;
    }
    
    formData.append('file1', fileInput1.files[0]);
    formData.append('file2', fileInput2.files[0]);
    formData.append('sheet_name1', sheetSelect1.value);
    formData.append('sheet_name2', sheetSelect2.value);
    
    // Show loading
    parseBtn.disabled = true;
    parseBtn.textContent = 'Processing...';
    uploadMsg.textContent = '';
    uploadResult.innerHTML = '<div style="color: blue;">Uploading file pair...</div>';
    
    try {
        const response = await fetch('/api/upload-pair', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            uploadResult.innerHTML = `<div style="color: green;">File pair uploaded successfully! ${result.rows_processed} rows processed. Pair ID: <code>${result.pair_id}</code></div>`;
            
            // Reset form
            fileInput1.value = '';
            fileInput2.value = '';
            document.getElementById('file-chosen-1').textContent = 'No file chosen';
            document.getElementById('file-chosen-2').textContent = 'No file chosen';
            document.getElementById('sheet-row-1').style.display = 'none';
            document.getElementById('sheet-row-2').style.display = 'none';
            parseBtn.disabled = true;
            
            // Reload data
            loadData();
            loadRecentUploads();
            
            // Clear success message after 8 seconds (longer to show pair ID)
            setTimeout(() => {
                uploadResult.innerHTML = '';
            }, 8000);
            
        } else {
            uploadResult.innerHTML = `<div style="color: red;">Upload failed: ${result.error}</div>`;
        }
        
    } catch (error) {
        uploadResult.innerHTML = `<div style="color: red;">Upload failed: ${error.message}</div>`;
    } finally {
        parseBtn.disabled = false;
        parseBtn.textContent = 'Upload Pair';
    }
}

// Load data from API
async function loadData() {
    try {
        const response = await fetch('/api/data');
        const result = await response.json();
        
        if (response.ok) {
            displayData(result.data, result.column_order);
        } else {
            console.error('Error loading data:', result.error);
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// Display data in table
function displayData(data, columnOrder) {
    const resultDiv = document.getElementById('data-table-result');
    
    if (!data || data.length === 0) {
        resultDiv.innerHTML = `
            <div style="text-align: center; color: #666; padding: 20px;">
                No data available. Upload a file to get started.
            </div>
        `;
        return;
    }
    
    // Use the column order from backend, fallback to Object.keys if not provided
    const columns = columnOrder || Object.keys(data[0]);
    
    // Debug: Print the column order received by frontend
    console.log("Frontend received columns:", columns);
    
    let tableHTML = `
        <div class="report-table-wrapper" style="max-height: 70vh; overflow-y: auto;">
            <table class="report-table" style="border-collapse: collapse;">
                <thead style="position: sticky; top: 0; background-color: #f8f9fa; z-index: 1;">
                    <tr>
                        ${columns.map(col => `<th style="border: 1px solid #dee2e6; padding: 8px; text-align: left; background-color: #f8f9fa;">${col}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.forEach(row => {
        tableHTML += `
            <tr>
                ${columns.map(col => {
                    let value = row[col];
                    if (value === null || value === undefined) {
                        value = '';
                    } else {
                        // Format date columns to YYYY-MM-DD
                        if (col.toLowerCase().includes('date') || col === 'Date') {
                            value = formatDate(value);
                        }
                    }
                    return `<td style="border: 1px solid #dee2e6; padding: 8px;">${value}</td>`;
                }).join('')}
            </tr>
        `;
    });
    
    tableHTML += `
                </tbody>
            </table>
        </div>
        <div style="margin-top: 10px; color: #666;">
            Total records: ${data.length}
        </div>
    `;
    
    resultDiv.innerHTML = tableHTML;
}

// Helper function to get badge class for match status
function getStatusBadgeClass(status) {
    switch(status) {
        case 'confirmed':
            return 'bg-success';
        case 'matched':
            return 'bg-warning';
        case 'unmatched':
        default:
            return 'bg-secondary';
    }
}

// Update reconciliation function to use company pairs
async function runReconciliation() {
    const resultDiv = document.getElementById('reconciliation-result');
    resultDiv.innerHTML = '<div style="color: blue;">Running reconciliation...</div>';
    
    try {
        const response = await fetch('/api/reconcile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        const result = await response.json();
        
        if (response.ok) {
            let successMessage = `${result.message} ${result.matches_found} matches found.`;
            resultDiv.innerHTML = `<div style="color: green;">${successMessage}</div>`;
            
            // Auto-load matches after reconciliation
            setTimeout(() => {
                loadMatches();
            }, 1000);
            
        } else {
            resultDiv.innerHTML = `<div style="color: red;">Reconciliation failed: ${result.error}</div>`;
        }
        
    } catch (error) {
        resultDiv.innerHTML = `<div style="color: red;">Reconciliation failed: ${error.message}</div>`;
    }
}

async function loadMatches() {
    const resultDiv = document.getElementById('reconciliation-result');
    resultDiv.innerHTML = '<div style="color: blue;">Loading matches...</div>';
    
    try {
        const response = await fetch('/api/matches');
        const result = await response.json();
        
        if (response.ok) {
            displayMatches(result.matches);
        } else {
            resultDiv.innerHTML = `<div style="color: red;">Failed to load matches: ${result.error}</div>`;
        }
        
    } catch (error) {
        resultDiv.innerHTML = `<div style="color: red;">Failed to load matches: ${error.message}</div>`;
    }
}

async function downloadMatches() {
    try {
        const response = await fetch('/api/download-matches');
        
        if (response.ok) {
            // Get the filename from the response headers
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'matched_transactions.xlsx';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            // Create blob and download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } else {
            const result = await response.json();
            alert(`Failed to download: ${result.error}`);
        }
    } catch (error) {
        alert(`Failed to download: ${error.message}`);
    }
}

function displayMatches(matches) {
    const resultDiv = document.getElementById('reconciliation-result');
    
    if (!matches || matches.length === 0) {
        resultDiv.innerHTML = `
            <div style="text-align: center; color: #666; padding: 20px;">
                No matches found. Run reconciliation to find matching transactions.
            </div>
        `;
        return;
    }
    
    // Get dynamic lender/borrower names from the first match (same logic as Excel export)
    let lender_name = 'Lender';
    let borrower_name = 'Borrower';
    if (matches.length > 0) {
        const first_match = matches[0];
        // Determine which is lender (Debit side) vs borrower (Credit side)
        if (first_match.Debit && first_match.Debit > 0) {
            // Main record is lender (Debit side)
            lender_name = first_match.lender || 'Lender';
            borrower_name = first_match.matched_lender || 'Borrower';
        } else if (first_match.matched_Debit && first_match.matched_Debit > 0) {
            // Matched record is lender (Debit side)
            lender_name = first_match.matched_lender || 'Lender';
            borrower_name = first_match.lender || 'Borrower';
        } else {
            // Fallback to original logic
            if (first_match.lender) {
                lender_name = first_match.lender;
            }
            if (first_match.matched_lender && first_match.matched_lender !== first_match.lender) {
                borrower_name = first_match.matched_lender;
            } else if (first_match.borrower) {
                borrower_name = first_match.borrower;
            }
        }
    }
    
    let tableHTML = `
        <div class="matched-transactions-wrapper">
            <div class="matched-header">
                <h4><i class="bi bi-link-45deg"></i> Matched Transactions (${matches.length} pairs)</h4>
            </div>
            <div class="table-responsive">
                <table class="matched-transactions-table">
                <thead>
                    <tr>
                            <!-- Lender Columns -->
                            <th data-column="lender_uid">Lender UID</th>
                            <th data-column="lender_date">Lender Date</th>
                            <th data-column="lender_particulars">Lender Particulars</th>
                            <th data-column="lender_debit">Lender Debit</th>
                            <th data-column="lender_credit">Lender Credit</th>
                            <th data-column="lender_vch_type">Lender Vch Type</th>
                            <th data-column="lender_role">Lender Role</th>
                            <!-- Borrower Columns -->
                            <th data-column="borrower_uid">Borrower UID</th>
                            <th data-column="borrower_date">Borrower Date</th>
                            <th data-column="borrower_particulars">Borrower Particulars</th>
                            <th data-column="borrower_debit">Borrower Debit</th>
                            <th data-column="borrower_credit">Borrower Credit</th>
                            <th data-column="borrower_vch_type">Borrower Vch Type</th>
                            <th data-column="borrower_role">Borrower Role</th>
                            <!-- Match Details Columns -->
                            <th data-column="confidence">Confidence</th>
                            <th data-column="match_type">Match Type</th>
                            <th data-column="amount">Amount</th>
                            <th data-column="actions">Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    matches.forEach(match => {
        // Determine which record is lender and which is borrower based on Debit/Credit values
        let lenderRecord, borrowerRecord, lenderUid, borrowerUid, lenderRole, borrowerRole;
        
        // Check which record has Debit > 0 (Lender) vs Credit > 0 (Borrower)
        const main_record_debit = parseFloat(match.Debit || 0);
        const main_record_credit = parseFloat(match.Credit || 0);
        const matched_record_debit = parseFloat(match.matched_Debit || 0);
        const matched_record_credit = parseFloat(match.matched_Credit || 0);
        
        if (main_record_debit > 0) {
            // Main record is Lender (Debit > 0)
            lenderRecord = {
                Date: match.Date,
                Particulars: match.Particulars,
                Credit: match.Credit,
                Debit: match.Debit,
                Vch_Type: match.Vch_Type
            };
            lenderUid = match.uid;
            lenderRole = 'Lender'; // Correct - Debit > 0 = Lender
            
            borrowerRecord = {
                Date: match.matched_date,
                Particulars: match.matched_particulars,
                Credit: match.matched_Credit,
                Debit: match.matched_Debit,
                Vch_Type: match.matched_Vch_Type
            };
            borrowerUid = match.matched_uid;
            borrowerRole = 'Borrower'; // Correct - Credit > 0 = Borrower
        } else if (matched_record_debit > 0) {
            // Matched record is Lender (Debit > 0)
            lenderRecord = {
                Date: match.matched_date,
                Particulars: match.matched_particulars,
                Credit: match.matched_Credit,
                Debit: match.matched_Debit,
                Vch_Type: match.matched_Vch_Type
            };
            lenderUid = match.matched_uid;
            lenderRole = 'Lender'; // Correct - Debit > 0 = Lender
            
            borrowerRecord = {
                Date: match.Date,
                Particulars: match.Particulars,
                Credit: match.Credit,
                Debit: match.Debit,
                Vch_Type: match.Vch_Type
            };
            borrowerUid = match.uid;
            borrowerRole = 'Borrower'; // Correct - Credit > 0 = Borrower
        } else {
            // Fallback: use the original logic based on lender_name
            if (match.lender === lender_name) {
                lenderRecord = {
                    Date: match.Date,
                    Particulars: match.Particulars,
                    Credit: match.Credit,
                    Debit: match.Debit,
                    Vch_Type: match.Vch_Type
                };
                lenderUid = match.uid;
                // Determine role based on Debit/Credit
                lenderRole = (parseFloat(match.Debit || 0) > 0) ? 'Lender' : 'Borrower';
                
                borrowerRecord = {
                    Date: match.matched_date,
                    Particulars: match.matched_particulars,
                    Credit: match.matched_Credit,
                    Debit: match.matched_Debit,
                    Vch_Type: match.matched_Vch_Type
                };
                borrowerUid = match.matched_uid;
                // Determine role based on Debit/Credit
                borrowerRole = (parseFloat(match.matched_Debit || 0) > 0) ? 'Lender' : 'Borrower';
            } else {
                borrowerRecord = {
                    Date: match.Date,
                    Particulars: match.Particulars,
                    Credit: match.Credit,
                    Debit: match.Debit,
                    Vch_Type: match.Vch_Type
                };
                borrowerUid = match.uid;
                // Determine role based on Debit/Credit
                borrowerRole = (parseFloat(match.Debit || 0) > 0) ? 'Lender' : 'Borrower';
                
                lenderRecord = {
                    Date: match.matched_date,
                    Particulars: match.matched_particulars,
                    Credit: match.matched_Credit,
                    Debit: match.matched_Debit,
                    Vch_Type: match.matched_Vch_Type
                };
                lenderUid = match.matched_uid;
                // Determine role based on Debit/Credit
                lenderRole = (parseFloat(match.matched_Debit || 0) > 0) ? 'Lender' : 'Borrower';
            }
        }
        
        // Calculate the matched amount
        const matchedAmount = Math.max(
            parseFloat(lenderRecord.Debit || 0),
            parseFloat(lenderRecord.Credit || 0),
            parseFloat(borrowerRecord.Debit || 0),
            parseFloat(borrowerRecord.Credit || 0)
        );
        
        tableHTML += `
            <tr class="match-row ${match.match_score > 0.7 ? 'high-confidence' : match.match_score > 0.5 ? 'medium-confidence' : 'low-confidence'}">
                <!-- Lender Columns -->
                <td data-column="lender_uid" class="uid-cell">${lenderUid || ''}</td>
                <td data-column="lender_date">${formatDate(lenderRecord.Date)}</td>
                <td data-column="lender_particulars" class="particulars-cell">${lenderRecord.Particulars || ''}</td>
                <td data-column="lender_debit" class="amount-cell debit-amount">${formatAmount(lenderRecord.Debit || 0)}</td>
                <td data-column="lender_credit" class="amount-cell credit-amount">${formatAmount(lenderRecord.Credit || 0)}</td>
                <td data-column="lender_vch_type">${lenderRecord.Vch_Type || ''}</td>
                <td data-column="lender_role"><span class="role-badge lender-role">${lenderRole}</span></td>
                <!-- Borrower Columns -->
                <td data-column="borrower_uid" class="uid-cell">${borrowerUid || ''}</td>
                <td data-column="borrower_date">${formatDate(borrowerRecord.Date)}</td>
                <td data-column="borrower_particulars" class="particulars-cell">${borrowerRecord.Particulars || ''}</td>
                <td data-column="borrower_debit" class="amount-cell debit-amount">${formatAmount(borrowerRecord.Debit || 0)}</td>
                <td data-column="borrower_credit" class="amount-cell credit-amount">${formatAmount(borrowerRecord.Credit || 0)}</td>
                <td data-column="borrower_vch_type">${borrowerRecord.Vch_Type || ''}</td>
                <td data-column="borrower_role"><span class="role-badge borrower-role">${borrowerRole}</span></td>
                <!-- Match Details Columns -->
                <td data-column="confidence">
                    <div class="confidence-indicator">
                        <span class="confidence-badge ${match.match_score > 0.7 ? 'high' : match.match_score > 0.5 ? 'medium' : 'low'}">
                        ${(match.match_score * 100).toFixed(0)}%
                    </span>
                        <div class="confidence-bar">
                            <div class="confidence-fill ${match.match_score > 0.7 ? 'high' : match.match_score > 0.5 ? 'medium' : 'low'}" style="width: ${match.match_score * 100}%"></div>
                        </div>
                    </div>
                </td>
                <td data-column="match_type">
                    <span class="match-type-badge">${match.keywords || match.matched_keywords || 'Auto'}</span>
                </td>
                <td data-column="amount" class="amount-cell matched-amount">
                    <strong>${formatAmount(matchedAmount)}</strong>
                </td>
                <td data-column="actions">
                    <div class="action-buttons">
                        <button class="btn btn-success btn-sm" onclick="acceptMatch('${match.uid}')" title="Accept Match">
                        <i class="bi bi-check-lg"></i>
                    </button>
                        <button class="btn btn-danger btn-sm" onclick="rejectMatch('${match.uid}')" title="Reject Match">
                        <i class="bi bi-x-lg"></i>
                    </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
                </tbody>
            </table>
            </div>
        </div>
    `;
    
    resultDiv.innerHTML = tableHTML;
}

// Accept/Reject functions
async function acceptMatch(uid) {
    try {
        const response = await fetch('/api/accept-match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                uid: uid,
                confirmed_by: 'User'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Match accepted successfully!');
            loadMatches(); // Refresh the matches display
        } else {
            alert(`Failed to accept match: ${result.error}`);
        }
        
    } catch (error) {
        alert(`Error accepting match: ${error.message}`);
    }
}

async function rejectMatch(uid) {
    if (!confirm('Are you sure you want to reject this match?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/reject-match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                uid: uid,
                confirmed_by: 'User'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Match rejected successfully!');
            loadMatches(); // Refresh the matches display
        } else {
            alert(`Failed to reject match: ${result.error}`);
        }
        
    } catch (error) {
        alert(`Error rejecting match: ${error.message}`);
    }
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    } catch {
        return dateString;
    }
}

function formatAmount(amount) {
    if (!amount || amount === '') return '';
    try {
        return parseFloat(amount).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    } catch {
        return amount;
    }
} 

// Fetch and display recent uploads
async function loadRecentUploads() {
    try {
        const response = await fetch('/api/recent-uploads');
        const result = await response.json();
        const container = document.getElementById('recent-uploads-list');
        if (response.ok && result.recent_uploads && result.recent_uploads.length > 0) {
            let html = '<div class="recent-uploads-heading">Recent uploads</div>';
            html += '<ul class="recent-uploads-ul">';
            result.recent_uploads.forEach(f => {
                html += `<li class="recent-upload-item">${f}</li>`;
            });
            html += '</ul>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '';
        }
    } catch (error) {
        document.getElementById('recent-uploads-list').innerHTML = '';
    }
} 

// Add Clear File List button handler
async function clearRecentUploads() {
    try {
        const response = await fetch('/api/clear-recent-uploads', { method: 'POST' });
        if (response.ok) {
            loadRecentUploads();
        }
    } catch (error) {
        // Ignore
    }
} 

// Load detected company pairs
async function loadDetectedPairs() {
    try {
        const response = await fetch('/api/detected-pairs');
        const result = await response.json();
        
        if (response.ok) {
            displayDetectedPairs(result.pairs, 'Smart Scan');
        } else {
            console.error('Failed to load detected pairs:', result.error);
        }
    } catch (error) {
        console.error('Error loading detected pairs:', error);
    }
}

async function loadManualPairs() {
    try {
        const response = await fetch('/api/manual-pairs');
        const result = await response.json();
        
        if (response.ok) {
            displayDetectedPairs(result.pairs, 'Manual Pairs');
        } else {
            console.error('Failed to load manual pairs:', result.error);
        }
    } catch (error) {
        console.error('Error loading manual pairs:', error);
    }
}

function displayDetectedPairs(pairs, type) {
    const displayDiv = document.getElementById('detected-pairs-display');
    
    if (!pairs || pairs.length === 0) {
        displayDiv.innerHTML = `
            <div style="text-align: center; color: #666; padding: 20px;">
                No ${type.toLowerCase()} pairs found.
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="card">
            <div class="card-header">
                <h6 class="mb-0"><i class="bi bi-diagram-3 me-2"></i>${type} Results (${pairs.length} pairs)</h6>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Company Pair</th>
                                <th>Period</th>
                                <th>Transactions</th>
                                <th>Type</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    pairs.forEach(pair => {
        const description = pair.description || `${pair.lender_company} ↔ ${pair.borrower_company}`;
        const period = `${pair.month} ${pair.year}`;
        const transactionCount = pair.transaction_count || 'N/A';
        const pairType = pair.type || 'detected';
        
        html += `
            <tr>
                <td><strong>${description}</strong></td>
                <td>${period}</td>
                <td><span class="badge bg-info">${transactionCount}</span></td>
                <td><span class="badge bg-secondary">${pairType}</span></td>
            </tr>
        `;
        
        // If this pair has an opposite pair, show it too
        if (pair.opposite_pair) {
            const oppositeDescription = pair.opposite_pair.description;
            html += `
                <tr>
                    <td style="padding-left: 20px;"><em>${oppositeDescription}</em></td>
                    <td>${period}</td>
                    <td><span class="badge bg-info">${transactionCount}</span></td>
                    <td><span class="badge bg-secondary">${pairType}</span></td>
                </tr>
            `;
        }
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    displayDiv.innerHTML = html;
} 

// Load and display pairs
async function loadPairs() {
    try {
        const response = await fetch('/api/pairs');
        const result = await response.json();
        
        if (response.ok) {
            displayPairs(result.pairs);
        } else {
            console.error('Failed to load pairs:', result.error);
        }
    } catch (error) {
        console.error('Error loading pairs:', error);
    }
}

function displayPairs(pairs) {
    const resultDiv = document.getElementById('pairs-table-result');
    
    if (!pairs || pairs.length === 0) {
        resultDiv.innerHTML = `
            <div style="text-align: center; color: #666; padding: 20px;">
                No upload pairs found. Upload some files to get started.
            </div>
        `;
        return;
    }
    
    let tableHTML = `
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Pair ID</th>
                        <th>Upload Date</th>
                        <th>Files</th>
                        <th>Records</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    pairs.forEach(pair => {
        const uploadDate = new Date(pair.upload_date).toLocaleString();
        const files = pair.filenames.join(', ');
        
        tableHTML += `
            <tr>
                <td><code>${pair.pair_id}</code></td>
                <td>${uploadDate}</td>
                <td>${files}</td>
                <td><span class="badge bg-info">${pair.record_count}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewPairData('${pair.pair_id}')">
                        <i class="bi bi-eye"></i> View Data
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="reconcilePair('${pair.pair_id}')">
                        <i class="bi bi-arrow-repeat"></i> Reconcile
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
                </tbody>
            </table>
        </div>
    `;
    
    resultDiv.innerHTML = tableHTML;
}

async function viewPairData(pairId) {
    try {
        const response = await fetch(`/api/pair/${pairId}/data`);
        const result = await response.json();
        
        if (response.ok) {
            // Switch to data table tab and display the pair data
            showTab('data-table');
            displayData(result.data, null);
            
            // Show which pair is being viewed
            const resultDiv = document.getElementById('data-table-result');
            resultDiv.innerHTML = `
                <div class="alert alert-info">
                    <strong>Viewing Pair:</strong> ${pairId}
                </div>
                ${resultDiv.innerHTML}
            `;
        } else {
            alert(`Failed to load pair data: ${result.error}`);
        }
    } catch (error) {
        alert(`Error loading pair data: ${error.message}`);
    }
}

async function reconcilePair(pairId) {
    if (!confirm(`Are you sure you want to reconcile pair ${pairId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/reconcile-pair/${pairId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Reconciliation complete! ${result.matches_found} matches found for pair ${pairId}`);
            // Refresh the pairs list
            loadPairs();
        } else {
            alert(`Reconciliation failed: ${result.error}`);
        }
    } catch (error) {
        alert(`Error reconciling pair: ${error.message}`);
    }
} 