# MASI Fundamental Value Estimation

This project provides a quantitative framework for estimating the fundamental value of the Moroccan All Shares Index (MASI) using the Hodrick-Prescott (HP) filter and Agent-Based Modeling (ABM) principles.

## 🏗 Project Architecture

The project is structured for modularity and scalability:

- **`main.py`**: The primary entry point. Coordinates fetching data from Supabase and applying signal processing.
- **`src/`**: Core package containing project logic.
  - `db_client.py`: Manages Supabase authentication and data I/O (fetching and uploading).
  - `scraper.py`: Utility to fetch historical MASI data (`MASI.CS`) from Yahoo Finance.
  - `signal_processing.py`: Implementation of the HP-filter and trend extraction.
- **`biblio/`**: Research papers and documentation.
  - `explanation/`: Contains `explanation.tex` and `explanation.pdf` for a deep dive into the methodology.

## 🚀 Getting Started

### 1. Environment Setup
Install the required dependencies:
```bash
pip install supabase statsmodels yfinance pandas python-dotenv
```

Create a `.env` file in the root directory with your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 2. Database Initialization
Run the following SQL in your Supabase Editor to create the necessary table:
```sql
CREATE TABLE masi_prices (
    date DATE PRIMARY KEY,
    close FLOAT8 NOT NULL
);
```

### 3. Data Acquisition
Populate your database with historical MASI data:
```bash
python src/scraper.py
```

### 4. Running the Analysis
Estimate the fundamental value from your stored data:
```bash
python main.py
```

## 📈 Methodology

### Fundamental Value Proxy
The project uses the **Hodrick-Prescott (HP) filter** to decompose the observed MASI price ($p_t$) into a trend component ($p_t^f$, interpreted as the fundamental value) and a cyclical component. The default smoothing parameter is $\lambda = 129,600$ for daily data.

### Theoretical Context
This implementation supports the **Chen et al. (2-type)** agent-based framework, which analyzes market dynamics through the interaction of Fundamentalists and Chartists.

---
*Note: Ensure you have a stable internet connection for Supabase and yfinance operations.*
