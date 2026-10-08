# Code for ETL operations on Bank-GDP data

# Importing the required libraries
import sqlite3
from datetime import datetime
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Known values
url = "https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks"
exchange_rate_csv_path = "./exchange_rate.csv"
output_csv_path = "./Largest_banks_data.csv"
database_name = "Banks.db"
table_name = "Largest_banks"
log_file = "code_log.txt"
table_attribs = ["Name", "MC_USD_Billion"]


def log_progress(message):
    """This function logs the mentioned message of a given stage of the
    code execution to a log file. Function returns nothing"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as file:
        file.write(f"{timestamp} : {message}\n")


def extract(url, table_attribs):
    """This function aims to extract the required
    information from the website and save it to a data frame. The
    function returns the data frame for further processing."""
    
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Use BeautifulSoup to parse HTML
    soup = BeautifulSoup(response.content, 'lxml')
    
    # Find all tables on the page
    tables = soup.find_all('table')
    
    for table in tables:
        rows = table.find_all('tr')
        
        # Check if this is the right table by looking for headers
        if len(rows) > 0:
            headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
            
            # Look for the table with "Name" and "Market cap" columns
            if any('Market cap' in str(h) for h in headers):
                data = []
                
                for row in rows[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        # Extract bank name (usually 2nd column after rank)
                        name = cols[1].get_text(strip=True)
                        # Extract market cap value (usually 3rd column)
                        mc_text = cols[2].get_text(strip=True)
                        
                        # Clean market cap: remove newlines and convert to float
                        mc_value = mc_text.replace('\n', '').strip()
                        try:
                            mc_float = float(mc_value)
                            data.append({"Name": name, "MC_USD_Billion": mc_float})
                        except ValueError:
                            continue
                
                if data:
                    df = pd.DataFrame(data)
                    return df[table_attribs].reset_index(drop=True)
    
    # Fallback: use pd.read_html
    tables = pd.read_html(response.text)
    for table in tables:
        columns = [str(col).strip() for col in table.columns]
        
        if any('Market cap' in str(col) for col in columns):
            df = table.copy()
            
            # Find and rename columns
            for col in df.columns:
                col_str = str(col).strip()
                if 'Bank' in col_str and 'name' in col_str.lower():
                    df = df.rename(columns={col: "Name"})
                elif 'Market cap' in col_str:
                    df = df.rename(columns={col: "MC_USD_Billion"})
            
            # Clean the market cap column
            if "MC_USD_Billion" in df.columns:
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
    """This function accesses the CSV file for exchange rate
    information, and adds three columns to the data frame, each
    containing the transformed version of Market Cap column to
    respective currencies"""
    
    # Read the exchange rate CSV
    exchange_rate_df = pd.read_csv(csv_path)
    exchange_rate_df.columns = [str(col).strip() for col in exchange_rate_df.columns]
    
    # Convert to dictionary with currency as key and rate as value
    rate_dict = exchange_rate_df.set_index(exchange_rate_df.columns[0])[exchange_rate_df.columns[1]].to_dict()
    rate_dict = {str(k).strip().upper(): float(v) for k, v in rate_dict.items()}
    
    transformed_df = df.copy()
    
    # Add GBP column
    gbp_rate = float(rate_dict.get('GBP', 0.76))
    transformed_df['MC_GBP_Billion'] = [np.round(x * gbp_rate, 2) for x in transformed_df['MC_USD_Billion']]
    
    # Add EUR column
    eur_rate = float(rate_dict.get('EUR', 0.90))
    transformed_df['MC_EUR_Billion'] = [np.round(x * eur_rate, 2) for x in transformed_df['MC_USD_Billion']]
    
    # Add INR column
    inr_rate = float(rate_dict.get('INR', 82.76))
    transformed_df['MC_INR_Billion'] = [np.round(x * inr_rate, 2) for x in transformed_df['MC_USD_Billion']]
    
    return transformed_df


def load_to_csv(df, output_path):
    """This function saves the final data frame as a CSV file in
    the provided path. Function returns nothing."""
    df.to_csv(output_path, index=False)


def load_to_db(df, sql_connection, table_name):
    """This function saves the final data frame to a database
    table with the provided name. Function returns nothing."""
    df.to_sql(table_name, sql_connection, if_exists="replace", index=False)


def run_query(query_statement, sql_connection):
    """This function runs the query on the database table and
    prints the output on the terminal. Function returns nothing."""
    print(query_statement)
    query_output = pd.read_sql_query(query_statement, sql_connection)
    print(query_output)


# Main ETL Process
log_progress("Preliminaries complete. Initiating ETL process")

# Extract
df = extract(url, table_attribs)
print(df)
log_progress("Data extraction complete. Initiating Transformation process")

# Transform
df = transform(df, exchange_rate_csv_path)
print(df)
log_progress("Data transformation complete. Initiating Loading process")

# Load to CSV
load_to_csv(df, output_csv_path)
log_progress("Data saved to CSV file")

# Load to Database
sql_connection = sqlite3.connect(database_name)
log_progress("SQL Connection initiated")

load_to_db(df, sql_connection, table_name)
log_progress("Data loaded to Database as a table, Executing queries")

# Run Queries
run_query("SELECT * FROM Largest_banks", sql_connection)
run_query("SELECT AVG(MC_GBP_Billion) FROM Largest_banks", sql_connection)
run_query("SELECT Name FROM Largest_banks LIMIT 5", sql_connection)

log_progress("Process Complete")

sql_connection.close()
log_progress("Server Connection closed")
