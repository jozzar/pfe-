"""Scraper for MASI historical prices using yfinance.

This script fetches historical data for the MASI index and uploads it to PostgreSQL.
"""

import yfinance as yf
import pandas as pd
import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_client import upload_masi_prices, clean_price_frame, DataIngestionError

MASI_TICKER = "MASI.CS"

def scrape_masi_data(period: str = "max") -> pd.DataFrame:
    """Fetch historical MASI data from Yahoo Finance."""
    print(f"Fetching historical data for {MASI_TICKER}...")
    ticker = yf.Ticker(MASI_TICKER)
    df = ticker.history(period=period)
    
    if df.empty:
        raise DataIngestionError(f"No data found for {MASI_TICKER}. You might be rate-limited by Yahoo Finance. Try again later.")
    
    df = df[["Close"]].copy()
    df.index.name = "date"
    df.rename(columns={"Close": "close"}, inplace=True)
    
    print(f"Successfully fetched {len(df)} records.")
    return df

def main():
    try:
        # 1. Scrape data
        raw_data = scrape_masi_data()
        
        # 2. Clean data
        clean_df = clean_price_frame(raw_data.reset_index())
        
        # 3. Upload to Database
        print("\nUploading data to PostgreSQL...")
        upload_masi_prices(clean_df)
        print("Upload complete! Database is now initialized.")
        
    except Exception as e:
        print(f"\nError during scraping/uploading: {e}")
        print("\nNote: Ensure your Docker container is running: docker-compose up -d")

if __name__ == "__main__":
    main()
