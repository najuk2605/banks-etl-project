import sqlite3
from datetime import datetime
import numpy as np
import pandas as pd
import requests

# Known values
url = "https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks"
exchange_rate_csv_path = "./exchange_rate.csv"
output_csv_path = "./Largest_banks_data.csv"
database_name = "Banks.db"
table_name = "Largest_banks"
log_file = "code_log.txt"
table_attribs = ["Name", "MC_USD_Billion"]


def log_progress(message):
    """Logs a progress message with timestamp to code_log.txt."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as file:
        file.write(f"{timestamp} : {message}\n")


def extract(url, table_attribs):
    """Extracts the table under 'By market capitalization' from the provided URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    for table in tables:
        columns = [str(col).strip() for col in table.columns]

        if ("Bank name" in columns and "Market cap (US$ billion)" in columns) or \
           ("Name" in columns and "MC_USD_Billion" in columns):
            df = table.copy()

            df.columns = [str(col).strip() for col in df.columns]
            if "Bank name" in df.columns:
                df = df.rename(columns={"Bank name": "Name"})
            if "Market cap (US$ billion)" in df.columns:
                df = df.rename(columns={"Market cap (US$ billion)": "MC_USD_Billion"})

            df = df[["Name", "MC_USD_Billion"]].copy()
            df["MC_USD_Billion"] = (
                df["MC_USD_Billion"]
                .astype(str)
                .str.replace(r"[^\d.]", "", regex=True)
                .replace("", np.nan)
                .astype(float)
            )

            return df[table_attribs].reset_index(drop=True)

    raise ValueError("The required table was not found on the webpage.")


def transform(df, csv_path):
    """Reads exchange rate CSV and adds GBP, EUR, and INR columns."""
    exchange_rate_df = pd.read_csv(csv_path)
    exchange_rate_df.columns = [str(col).strip() for col in exchange_rate_df.columns]

    rate_dict = exchange_rate_df.set_index(exchange_rate_df.columns[0])[exchange_rate_df.columns[1]].to_dict()
    rate_dict = {str(k).strip().upper(): float(v) for k, v in rate_dict.items()}

    transformed_df = df.copy()
    transformed_df["MC_GBP_Billion"] = np.round(transformed_df["MC_USD_Billion"] * float(rate_dict["GBP"]), 2)
    transformed_df["MC_EUR_Billion"] = np.round(transformed_df["MC_USD_Billion"] * float(rate_dict["EUR"]), 2)
    transformed_df["MC_INR_Billion"] = np.round(transformed_df["MC_USD_Billion"] * float(rate_dict["INR"]), 2)

    return transformed_df


def load_to_csv(df, output_path):
    """Saves the final data frame to a CSV file."""
    df.to_csv(output_path, index=False)


def load_to_db(df, sql_connection, table_name):
    """Loads the final dataframe into a SQLite database table."""
    df.to_sql(table_name, sql_connection, if_exists="replace", index=False)


def run_query(query_statement, sql_connection):
    """Runs a SQL query and prints the result."""
    print(f"\nQuery: {query_statement}")
    result = pd.read_sql_query(query_statement, sql_connection)
    print(result)


# Main script
log_progress("Preliminaries complete. Initiating ETL process")

df = extract(url, table_attribs)
print("Extracted data:")
print(df.head())
log_progress("Data extraction complete. Initiating Transformation process")

df = transform(df, exchange_rate_csv_path)
print("\nTransformed data:")
print(df.head())
log_progress("Data transformation complete. Initiating Loading process")

load_to_csv(df, output_csv_path)
log_progress("Data saved to CSV file")

sql_connection = sqlite3.connect(database_name)
log_progress("SQL Connection initiated")

load_to_db(df, sql_connection, table_name)
log_progress("Data loaded to Database as a table, Executing queries")

run_query("SELECT * FROM Largest_banks", sql_connection)
run_query("SELECT AVG(MC_GBP_Billion) FROM Largest_banks", sql_connection)
run_query("SELECT Name FROM Largest_banks LIMIT 5", sql_connection)

log_progress("Process Complete")
sql_connection.close()
log_progress("Server Connection closed")
