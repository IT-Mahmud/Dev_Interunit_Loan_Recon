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
function handleFileSelect(input) {
    const file = input.files[0];
    const fileChosenSpan = input.nextElementSibling;
    const sheetRow = document.getElementById('sheet-row');
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
                
                // Enable parse button
                parseBtn.disabled = false;
                
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

// Handle form submission
document.getElementById('tally-upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    uploadFile();
});

// Upload file function
async function uploadFile() {
    const formData = new FormData();
    const fileInput = document.querySelector('input[type="file"]');
    const sheetSelect = document.querySelector('.sheet-select');
    const parseBtn = document.getElementById('parse-btn');
    const uploadMsg = document.getElementById('upload-msg');
    const uploadResult = document.getElementById('upload-result');
    
    if (!fileInput.files[0]) {
        uploadMsg.textContent = 'Please select a file to upload.';
        return;
    }
    
    if (!sheetSelect.value) {
        uploadMsg.textContent = 'Please select a sheet.';
        return;
    }
    
    formData.append('file', fileInput.files[0]);
    formData.append('sheet_name', sheetSelect.value);
    
    // Show loading
    parseBtn.disabled = true;
    parseBtn.textContent = 'Processing...';
    uploadMsg.textContent = '';
    uploadResult.innerHTML = '<div style="color: blue;">Uploading file...</div>';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            uploadResult.innerHTML = `<div style="color: green;">File uploaded successfully! ${result.rows_processed} rows processed.</div>`;
            
            // Reset form
            fileInput.value = '';
            document.querySelector('.file-chosen').textContent = 'No file chosen';
            document.getElementById('sheet-row').style.display = 'none';
            parseBtn.disabled = true;
            
            // Reload data
            loadData();
            loadRecentUploads();
            
            // Clear success message after 5 seconds
            setTimeout(() => {
                uploadResult.innerHTML = '';
            }, 5000);
            
        } else {
            uploadResult.innerHTML = `<div style="color: red;">Upload failed: ${result.error}</div>`;
        }
        
    } catch (error) {
        uploadResult.innerHTML = `<div style="color: red;">Upload failed: ${error.message}</div>`;
    } finally {
        parseBtn.disabled = false;
        parseBtn.textContent = 'Parse';
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

// Company pair selection functions
async function loadCompanyPairs() {
    try {
        const response = await fetch('/api/company-pairs');
        const result = await response.json();
        
        if (response.ok) {
            displayCompanyPairs(result.pairs);
        } else {
            console.error('Failed to load company pairs:', result.error);
        }
    } catch (error) {
        console.error('Error loading company pairs:', error);
    }
}

function displayCompanyPairs(pairs) {
    const companyPairSelect = document.getElementById('company-pair-select');
    const periodSelect = document.getElementById('period-select');
    
    // Clear existing options
    companyPairSelect.innerHTML = '<option value="">-- Select Company Pair --</option>';
    periodSelect.innerHTML = '<option value="">-- All Periods --</option>';
    
    if (pairs.length === 0) {
        // Add option for all data
        companyPairSelect.innerHTML += '<option value="">-- All Data (No specific pair) --</option>';
        return;
    }
    
    // Add company pairs
    pairs.forEach(pair => {
        const option = document.createElement('option');
        option.value = `${pair.lender_company}|${pair.borrower_company}`;
        option.textContent = pair.description;
        option.dataset.pair = JSON.stringify(pair);
        companyPairSelect.appendChild(option);
    });
    
    // Remove existing event listener to prevent duplicates
    const newCompanyPairSelect = companyPairSelect.cloneNode(true);
    companyPairSelect.parentNode.replaceChild(newCompanyPairSelect, companyPairSelect);
    
    // Add event listener to populate periods
    newCompanyPairSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        if (selectedOption.dataset.pair) {
            const pair = JSON.parse(selectedOption.dataset.pair);
            // For now, just show the specific period
            periodSelect.innerHTML = `<option value="${pair.month}|${pair.year}">${pair.month} ${pair.year}</option>`;
        } else {
            periodSelect.innerHTML = '<option value="">-- All Periods --</option>';
        }
    });
}

function clearCompanySelection() {
    document.getElementById('company-pair-select').value = '';
    document.getElementById('period-select').value = '';
}

// Update reconciliation function to use company pairs
async function runReconciliation() {
    const resultDiv = document.getElementById('reconciliation-result');
    resultDiv.innerHTML = '<div style="color: blue;">Running reconciliation...</div>';
    
    const companyPairValue = document.getElementById('company-pair-select').value;
    const periodValue = document.getElementById('period-select').value;
    
    let lenderCompany = null;
    let borrowerCompany = null;
    let month = null;
    let year = null;
    
    if (companyPairValue) {
        [lenderCompany, borrowerCompany] = companyPairValue.split('|');
    }
    
    if (periodValue) {
        [month, year] = periodValue.split('|');
    }
    
    let message = 'Running reconciliation';
    if (lenderCompany && borrowerCompany) {
        message += ` for ${lenderCompany} ↔ ${borrowerCompany}`;
        if (month && year) {
            message += ` (${month} ${year})`;
        }
    } else {
        message += ' on all data';
    }
    resultDiv.innerHTML = `<div style="color: blue;">${message}...</div>`;
    
    try {
        const response = await fetch('/api/reconcile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lender_company: lenderCompany,
                borrower_company: borrowerCompany,
                month: month,
                year: year
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            let successMessage = `${result.message} ${result.matches_found} matches found.`;
            if (result.lender_company && result.borrower_company) {
                successMessage += ` (${result.lender_company} ↔ ${result.borrower_company})`;
                if (result.month && result.year) {
                    successMessage += ` (${result.month} ${result.year})`;
                }
            }
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