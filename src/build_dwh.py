import pandas as pd
from sqlalchemy import create_engine
import os

# --- Configuration ---
# Define the directory where the source CSV files are located.
DATA_DIR = 'data'
# Define the directory where the final database will be saved.
OUTPUT_DIR = 'output'
# Define the name of the SQLite database file.
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# Define the tables to be created in the data warehouse.
# The key is the table name, and the value is the corresponding CSV file name.
TABLES = {
    'DimMusicalWork': 'DimMusicalWork.csv',
    'DimPerformer': 'DimPerformer.csv',
    'DimRecording': 'DimRecording.csv',
    'DimJourney': 'DimJourney.csv',
    'FactJourneyStep': 'FactJourneyStep.csv'
}

def build_data_warehouse():
    """
    Extracts data from CSV files, transforms it, and loads it into a SQLite database.
    """
    print("Starting the Data Warehouse build process...")

    # --- Create Output Directory ---
    # Ensure the output directory exists. If not, create it.
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating output directory at: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    # --- Create Database Engine ---
    # Using SQLAlchemy, create an engine to connect to the SQLite database.
    # The database will be created at the specified path if it doesn't exist.
    engine = create_engine(f'sqlite:///{DB_PATH}')
    print(f"Database engine created. DWH will be built at: {DB_PATH}")

    # --- Loop Through Tables and Load Data ---
    for table_name, csv_file in TABLES.items():
        try:
            # Construct the full path to the source CSV file.
            csv_path = os.path.join(DATA_DIR, csv_file)
            print(f"Processing {csv_file} -> loading into table '{table_name}'...")

            # Read the CSV file into a pandas DataFrame.
            df = pd.read_csv(csv_path)

            # Use pandas' to_sql() function to write the DataFrame to the SQLite database.
            # - `name`: The name of the SQL table.
            # - `con`: The database connection engine.
            # - `if_exists='replace'`: If the table already exists, it will be dropped and recreated.
            # - `index=False`: Do not write the DataFrame's index as a column in the table.
            df.to_sql(table_name, con=engine, if_exists='replace', index=False)
            
            print(f"Successfully loaded {len(df)} rows into '{table_name}'.")

        except FileNotFoundError:
            print(f"ERROR: CSV file not found at {csv_path}. Skipping table '{table_name}'.")
        except Exception as e:
            print(f"An error occurred while processing {csv_file}: {e}")

    print("\nData Warehouse build process completed successfully!")

if __name__ == "__main__":
    build_data_warehouse()
