# banks-etl-project

This repository contains an ETL project that extracts the top banks by market capitalization from Wikipedia, transforms the values into GBP, EUR, and INR, saves the result to CSV, and loads it into a SQLite database.

## Files
- `banks_project.py` – ETL script
- `exchange_rate.csv` – exchange rates used for currency conversion
- `Largest_banks_data.csv` – generated output CSV
- `Banks.db` – generated SQLite database
- `code_log.txt` – execution log

## Run
```bash
python3.11 -m pip install requests pandas numpy lxml beautifulsoup4
python3.11 banks_project.py
```
