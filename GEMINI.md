# MASI Fundamental Value Estimation

This project provides a quantitative framework for estimating the fundamental value of the Moroccan All Shares Index (MASI) using the Hodrick-Prescott (HP) filter and Agent-Based Modeling (ABM) principles.

## 🏗 Project Architecture

The project is structured for modularity and scalability:

- **`main.py`**: The primary entry point. Coordinates fetching data from the database and applying signal processing.
- **`src/`**: Core package containing project logic.
  - `db_client.py`: Manages PostgreSQL connections and data I/O using SQLAlchemy.
  - `scraper.py`: Utility to fetch historical MASI data (`MASI.CS`) from Yahoo Finance.
  - `signal_processing.py`: Implementation of the HP-filter and trend extraction.
- **`biblio/`**: Research papers and documentation.
- **`docker-compose.yml`**: Defines the local PostgreSQL database service.

## 🚀 Getting Started

### 1. Environment Setup
Install the required dependencies:
```bash
pip install sqlalchemy psycopg2-binary statsmodels yfinance pandas python-dotenv
```

### 2. Launch Database (Docker)
Ensure Docker is installed and running, then start the database:
```bash
docker-compose up -d
```
This will start a PostgreSQL instance on `localhost:5432`.

### 3. Initialize Tables
Create the required database schema:
```bash
python src/setup_tables.py
```

### 4. Data Acquisition
Populate your database with historical MASI prices:
```bash
python src/scraper.py
```


### 5. Running the Analysis
Estimate the fundamental value from your stored data:
```bash
python main.py
```

## 📊 Methodology

### Fundamental Value Proxy
The project uses the **Hodrick-Prescott (HP) filter** to decompose the observed MASI price into a trend component ($p_t^f$, interpreted as the fundamental value).

### Theoretical Context
Supports the **Chen et al. (2-type)** agent-based framework (Fundamentalists vs. Chartists).

---
*Note: Credentials can be configured in the `.env` file.*
