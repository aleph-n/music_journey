import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Configuration ---
DATA_DIR = 'data'
OUTPUT_DIR = 'output'
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# Define the tables to be created in the data warehouse.
# The key is the table name, and the value is the corresponding CSV file name.
TABLES = {
    'DimMusicalWork': 'DimMusicalWork.csv',
    'DimPerformer': 'DimPerformer.csv',
    'DimRecording': 'DimRecording.csv',
    'DimJourney': 'DimJourney.csv',
    'FactJourneyStep': 'FactJourneyStep.csv',
    'DimPlaylist': 'DimPlaylist.csv'  # <-- ADDED
}

def build_data_warehouse():
    """
    Extracts data from CSV files and loads it into a SQLite database.
    Also creates the DimPlaylist table if it doesn't exist.
    """
    print("Starting the Data Warehouse build process...")

    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating output directory at: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    engine = create_engine(f'sqlite:///{DB_PATH}')
    print(f"Database engine created. DWH will be built at: {DB_PATH}")

    # --- Load Data from CSVs ---
    for table_name, csv_file in TABLES.items():
        try:
            csv_path = os.path.join(DATA_DIR, csv_file)
            print(f"Processing {csv_file} -> loading into table '{table_name}'...")
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, con=engine, if_exists='replace', index=False)
            print(f"Successfully loaded {len(df)} rows into '{table_name}'.")
        except FileNotFoundError:
            print(f"ERROR: CSV file not found at {csv_path}. Skipping table '{table_name}'.")
        except Exception as e:
            print(f"An error occurred while processing {csv_file}: {e}")

    # --- Ensure DimPlaylist table has the correct schema for UPSERT ---
    # The ON CONFLICT clause requires a unique constraint.
    with engine.connect() as connection:
        # Check if the table was created from an empty CSV
        count_query = text(f"SELECT COUNT(*) FROM DimPlaylist")
        if connection.execute(count_query).scalar() == 0:
             # Drop and recreate with the constraint if it's empty
            print("Ensuring DimPlaylist has the correct primary key for updates...")
            connection.execute(text("DROP TABLE IF EXISTS DimPlaylist;"))
            connection.execute(text("""
                CREATE TABLE DimPlaylist (
                    JourneyID TEXT NOT NULL,
                    ServiceID TEXT NOT NULL,
                    ServicePlaylistID TEXT,
                    LastUpdatedUTC TEXT,
                    PRIMARY KEY (JourneyID, ServiceID)
                );
            """))
            connection.commit()

    print("\nData Warehouse build process finished successfully.")

if __name__ == '__main__':
    build_data_warehouse()
