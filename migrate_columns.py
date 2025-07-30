import pandas as pd
from sqlalchemy import create_engine, text
from config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB

def migrate_columns():
    """Migrate owner and counterparty columns to lender and borrower"""
    engine = create_engine(f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}')
    
    with engine.connect() as conn:
        try:
            # Check if the role column exists
            result = conn.execute(text("SHOW COLUMNS FROM tally_data LIKE 'role'"))
            role_exists = result.fetchone() is not None
            
            # Rename columns
            print("Renaming owner to lender...")
            conn.execute(text("ALTER TABLE tally_data CHANGE COLUMN owner lender VARCHAR(32)"))
            
            print("Renaming counterparty to borrower...")
            conn.execute(text("ALTER TABLE tally_data CHANGE COLUMN counterparty borrower VARCHAR(32)"))
            
            # Add role column if it doesn't exist
            if not role_exists:
                print("Adding role column...")
                conn.execute(text("ALTER TABLE tally_data ADD COLUMN role VARCHAR(16)"))
                
                # Populate role column based on Debit/Credit
                print("Populating role column...")
                conn.execute(text("""
                    UPDATE tally_data 
                    SET role = CASE 
                        WHEN Debit > 0 THEN 'Lender'
                        WHEN Credit > 0 THEN 'Borrower'
                        ELSE NULL
                    END
                    WHERE role IS NULL
                """))
            
            conn.commit()
            print("Migration completed successfully!")
            
            # Verify the changes
            result = conn.execute(text("DESCRIBE tally_data"))
            columns = [row[0] for row in result]
            print(f"Current columns: {columns}")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate_columns() 