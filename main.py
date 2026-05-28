"""Main entry point for the MASI Fundamental Value project.

This script coordinates the data ingestion and processing workflow.
"""

from src.db_client import fetch_masi_prices
from src.signal_processing import add_hp_fundamental_value

def main():
    print("--- MASI Fundamental Value Estimation ---")
    try:
        # 1. Fetch data from Database
        print("Fetching prices from PostgreSQL...")
        prices = fetch_masi_prices()
        
        # 2. Process data
        print("Calculating fundamental value (HP-filter)...")
        results = add_hp_fundamental_value(prices)
        
        # 3. Display summary
        print("\nProcess Complete!")
        print(f"Total observations: {len(results)}")
        print("\nLatest Estimates:")
        print(results.tail())
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nSuggestions:")
        print("- Ensure your Docker container is running: docker-compose up -d")
        print("- Ensure your .env file has valid credentials.")
        print("- Ensure the 'masi_daily' table exists and contains data.")
        print("- Run 'python src/scraper.py' if the table is empty.")

if __name__ == "__main__":
    main()
