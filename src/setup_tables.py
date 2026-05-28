"""Setup script to create database tables for the MASI Fundamental Value project.
"""

import sys
import os
from sqlalchemy import text

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_client import get_db_engine, DataIngestionError

TABLES_SQL = """
CREATE TABLE IF NOT EXISTS masi_daily (
    id SERIAL PRIMARY KEY,
    trade_date DATE UNIQUE NOT NULL,
    closing_price NUMERIC(10, 2) NOT NULL,
    trading_volume BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bam_policy (
    id SERIAL PRIMARY KEY,
    announcement_date DATE UNIQUE NOT NULL,
    taux_directeur NUMERIC(5, 4) NOT NULL, 
    basis_point_change INTEGER NOT NULL, 
    event_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_fractions (
    id SERIAL PRIMARY KEY,
    trade_date DATE UNIQUE NOT NULL REFERENCES masi_daily(trade_date),
    fundamental_price NUMERIC(10, 2) NOT NULL, 
    fundamentalist_fraction NUMERIC(5, 4) NOT NULL, 
    chartist_fraction NUMERIC(5, 4) NOT NULL, 
    lambda_estimate NUMERIC(8, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

def setup_database():
    """Execute the SQL to create tables."""
    print("Connecting to database...")
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            print("Creating tables...")
            # We split by semicolon to execute individually if needed, 
            # but SQLAlchemy's text() can handle multiple statements in some drivers.
            # To be safe and explicit with 'IF NOT EXISTS', we use the provided SQL.
            conn.execute(text(TABLES_SQL))
            conn.commit()
            print("Tables created successfully!")
    except Exception as e:
        print(f"Error setting up database: {e}")
        print("\nEnsure your PostgreSQL container is running (docker-compose up -d).")
        sys.exit(1)

if __name__ == "__main__":
    setup_database()
