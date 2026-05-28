"""Scraper for MASI historical prices using yfinance.

This script fetches historical data for the MASI index and uploads it to Supabase.
"""

import yfinance as yf
import pandas as pd
from db_client import upload_masi_prices, clean_price_frame, DataIngestionError

MASI_TICKER = "MASI.CS"  # Common ticker for MASI index on Yahoo Finance

def scrape_masi_data(period: str = "max") -> pd.DataFrame:
    """Fetch historical MASI data from Yahoo Finance."""
    print(f"Fetching historical data for {MASI_TICKER}...")
    ticker = yf.Ticker(MASI_TICKER)
    df = ticker.history(period=period)
    
    if df.empty:
        raise DataIngestionError(f"No data found for {MASI_TICKER}. Check the ticker or network connection.")
    
    # yfinance returns a DataFrame with 'Close' column and a DatetimeIndex
    df = df[["Close"]].copy()
    df.index.name = "date"
    df.rename(columns={"Close": "close"}, inplace=True)
    
    print(f"Successfully fetched {len(df)} records.")
    print("\nData Preview (First 5 records):")
    print(df.head())
    return df

def main():
    try:
        # 1. Scrape data
        raw_data = scrape_masi_data()
        
        # 2. Clean data using existing logic
        clean_df = clean_price_frame(raw_data.reset_index())
        
        # 3. Upload to Supabase
        print("\nUploading data to Supabase...")
        upload_masi_prices(clean_df)
        print("Upload complete!")
        
    except Exception as e:
        print(f"\nError during scraping/uploading: {e}")
        print("\nNote: If you haven't created the 'masi_prices' table in Supabase yet,")
        print("please run the SQL command provided in GEMINI.md first.")

if __name__ == "__main__":
    main()
