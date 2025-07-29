// Interunit Loan Reconciliation - JavaScript

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadData();
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

// Reconciliation functions
async function runReconciliation() {
    const resultDiv = document.getElementById('reconciliation-result');
    resultDiv.innerHTML = '<div style="color: blue;">Running reconciliation...</div>';
    
    try {
        const response = await fetch('/api/reconcile', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            resultDiv.innerHTML = `<div style="color: green;">${result.message}. ${result.matches_found} matches found.</div>`;
            
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
    
    let tableHTML = `
        <div class="report-table-wrapper">
            <h4>Matched Transactions (${matches.length} pairs)</h4>
            <table class="report-table">
                <thead>
                    <tr>
                        <th colspan="5" style="text-align: center; background-color: #e3f2fd;">Steel (Lender)</th>
                        <th colspan="5" style="text-align: center; background-color: #f3e5f5;">GeoTex (Borrower)</th>
                        <th>Match Score</th>
                        <th>Keywords</th>
                        <th>Actions</th>
                    </tr>
                    <tr>
                        <th>UID</th>
                        <th>Date</th>
                        <th>Particulars</th>
                        <th>Credit</th>
                        <th>Debit</th>
                        <th>UID</th>
                        <th>Date</th>
                        <th>Particulars</th>
                        <th>Credit</th>
                        <th>Debit</th>
                        <th>Similarity</th>
                        <th>Matching keywords</th>
                        <th>Accept/Reject</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    matches.forEach(match => {
        // Determine which record is Steel and which is GeoTex based on lender field
        let steelRecord, geotexRecord;
        let steelUid, geotexUid;
        
        if (match.lender === 'Steel') {
            // This record is Steel, get GeoTex from matched data
            steelRecord = {
                Date: match.Date,
                Particulars: match.Particulars,
                Credit: match.Credit,
                Debit: match.Debit
            };
            steelUid = match.uid;
            geotexRecord = {
                Date: match.matched_date,
                Particulars: match.matched_particulars,
                Credit: match.matched_Credit,
                Debit: match.matched_Debit
            };
            geotexUid = match.matched_uid;
        } else if (match.matched_lender === 'Steel') {
            // This record is GeoTex, get Steel from matched data
            geotexRecord = {
                Date: match.Date,
                Particulars: match.Particulars,
                Credit: match.Credit,
                Debit: match.Debit
            };
            geotexUid = match.uid;
            steelRecord = {
                Date: match.matched_date,
                Particulars: match.matched_particulars,
                Credit: match.matched_Credit,
                Debit: match.matched_Debit
            };
            steelUid = match.matched_uid;
        } else {
            // Fallback: assume current record is Steel if we can't determine
            steelRecord = {
                Date: match.Date,
                Particulars: match.Particulars,
                Credit: match.Credit,
                Debit: match.Debit
            };
            steelUid = match.uid;
            geotexRecord = {
                Date: match.matched_date,
                Particulars: match.matched_particulars,
                Credit: match.matched_Credit,
                Debit: match.matched_Debit
            };
            geotexUid = match.matched_uid;
        }
        
        tableHTML += `
            <tr>
                <td style="font-size: 11px; color: #666;">${steelUid || ''}</td>
                <td>${formatDate(steelRecord.Date)}</td>
                <td>${steelRecord.Particulars || ''}</td>
                <td style="text-align: right; color: green;">${formatAmount(steelRecord.Credit || 0)}</td>
                <td style="text-align: right; color: red;">${formatAmount(steelRecord.Debit || 0)}</td>
                <td style="font-size: 11px; color: #666;">${geotexUid || ''}</td>
                <td>${formatDate(geotexRecord.Date)}</td>
                <td>${geotexRecord.Particulars || ''}</td>
                <td style="text-align: right; color: green;">${formatAmount(geotexRecord.Credit || 0)}</td>
                <td style="text-align: right; color: red;">${formatAmount(geotexRecord.Debit || 0)}</td>
                <td style="text-align: center;">
                    <span class="badge ${match.match_score > 0.7 ? 'bg-success' : match.match_score > 0.5 ? 'bg-warning' : 'bg-danger'}">
                        ${(match.match_score * 100).toFixed(0)}%
                    </span>
                </td>
                <td style="font-size: 10px; max-width: 150px; word-wrap: break-word;">
                    ${match.keywords || match.matched_keywords || ''}
                </td>
                <td style="text-align: center;">
                    <button class="btn btn-success btn-sm me-1" onclick="acceptMatch('${match.uid}')" title="Accept Match">
                        <i class="bi bi-check-lg"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="rejectMatch('${match.uid}')" title="Reject Match">
                        <i class="bi bi-x-lg"></i>
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