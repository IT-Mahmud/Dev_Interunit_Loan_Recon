CREATE DATABASE IF NOT EXISTS interunit_loan_recon_db;
USE interunit_loan_recon_db;

CREATE TABLE IF NOT EXISTS tally_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uid VARCHAR(50) NOT NULL UNIQUE,
    pair_id VARCHAR(64),
    lender VARCHAR(32),
    borrower VARCHAR(32),
    statement_month VARCHAR(16),
    statement_year VARCHAR(8),
    Date DATE,
    dr_cr VARCHAR(4),
    Particulars TEXT,
    Vch_Type VARCHAR(32),
    Vch_No VARCHAR(32),
    Debit DECIMAL(18,2),
    Credit DECIMAL(18,2),
    entered_by VARCHAR(64),
    input_date DATETIME,
    match_status VARCHAR(16),
    matched_with VARCHAR(64),
    match_score FLOAT,
    date_matched DATETIME,
    keywords TEXT,
    role VARCHAR(16),
    original_filename VARCHAR(255)
);