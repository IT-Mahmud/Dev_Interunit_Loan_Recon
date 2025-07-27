CREATE DATABASE IF NOT EXISTS interunit_loan_recon_db;
USE interunit_loan_recon_db;

CREATE TABLE IF NOT EXISTS tally_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tally_uid VARCHAR(50) UNIQUE,
    Date DATE,
    Voucher_Type VARCHAR(50),
    Voucher_No VARCHAR(50),
    Ref VARCHAR(50),
    Ref_Type VARCHAR(50),
    Particulars TEXT,
    Credit DECIMAL(15,2),
    Debit DECIMAL(15,2),
    Balance DECIMAL(15,2),
    Unit VARCHAR(50),
    lender VARCHAR(50),
    borrower VARCHAR(50),
    statement_month VARCHAR(10),
    statement_year VARCHAR(10),
    dr_cr VARCHAR(255),
    Vch_Type VARCHAR(255),
    Vch_No VARCHAR(255),
    entered_by VARCHAR(100),
    matched_with VARCHAR(50),
    match_status ENUM('unmatched', 'matched', 'confirmed') DEFAULT 'unmatched',
    match_score DECIMAL(5,2),
    reconciliation_date DATETIME,
    confirmed_by VARCHAR(100),
    keywords TEXT
);

