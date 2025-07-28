CREATE DATABASE IF NOT EXISTS interunit_loan_recon_db;
USE interunit_loan_recon_db;

CREATE TABLE IF NOT EXISTS tally_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uid VARCHAR(50) UNIQUE,
    
    Date DATE,
    dr_cr VARCHAR(255),
    Particulars TEXT,
    Vch_Type VARCHAR(255),
    Vch_No VARCHAR(255),
    Debit DECIMAL(15,2),
	Credit DECIMAL(15,2),
	keywords TEXT,
    entered_by VARCHAR(100),

    lender VARCHAR(50),
    borrower VARCHAR(50),
    
    statement_month VARCHAR(10),
    statement_year VARCHAR(10),
    
    matched_with VARCHAR(50),
    match_status ENUM('unmatched', 'matched', 'confirmed') DEFAULT 'unmatched',
    match_score DECIMAL(5,2),
    reconciliation_date DATETIME,
    confirmed_by VARCHAR(100),
    input_date DATETIME
	);