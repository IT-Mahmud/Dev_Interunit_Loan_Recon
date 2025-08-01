# Database settings
MYSQL_USER = 'interunit_loan_recon_user'
MYSQL_PASSWORD = 'abc123'
MYSQL_HOST = 'localhost'
MYSQL_DB = 'interunit_loan_recon_db'

# Manual company pairs configuration
# Format: 'Company Name': 'Counterparty Name'
MANUAL_COMPANY_PAIRS = {
    'GeoTex': 'Steel',
    'Steel': 'GeoTex',
    'Pole': 'Steel',
    'Steel': 'Pole',
    'Geo Textile': 'Steel',
    'Steel': 'Geo Textile',
    # Add more pairs as needed
    # The system will automatically create opposite pairs
} 