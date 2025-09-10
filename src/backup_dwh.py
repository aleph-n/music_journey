import os
import pandas as pd
from sqlalchemy import create_engine, inspect

# --- Configuration ---
DATA_DIR = 'data'
OUTPUT_DIR = 'output'
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# Mapping from table names to CSV filenames
TABLE_TO_CSV_MAP = {
    'DimMusicalWork': 'DimMusicalWork.csv',
    'DimPerformer': 'DimPerformer.csv',
    'DimRecording': 'DimRecording.csv',
    'DimJourney': 'DimJourney.csv',
    'FactJourneyStep': 'FactJourneyStep.csv',
    'DimPlaylist': 'DimPlaylist.csv',
    'DimAlbum': 'DimAlbum.csv',
    'DimMovement': 'DimMovement.csv',
    'BridgeAlbumMovement': 'BridgeAlbumMovement.csv'
}

def backup_database_to_csv():
    """
    Exports all tables from the SQLite database back to their source CSV files.
    """
    print("Starting database to CSV backup process...")

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}. Cannot perform backup.")
        return

    engine = create_engine(f'sqlite:///{DB_PATH}')
    
    try:
        # The inspector is used to get schema information, like table names
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        print(f"Found tables: {table_names}")

        for table_name in table_names:
            if table_name in TABLE_TO_CSV_MAP:
                csv_file = TABLE_TO_CSV_MAP[table_name]
                csv_path = os.path.join(DATA_DIR, csv_file)
                
                print(f"Exporting table '{table_name}' to '{csv_path}'...")
                
                # Read the entire table into a pandas DataFrame
                df = pd.read_sql_table(table_name, engine)
                
                # Save the DataFrame to a CSV file, overwriting the existing one
                df.to_csv(csv_path, index=False)
                
                print(f"Successfully exported {len(df)} rows to '{csv_file}'.")
            else:
                print(f"WARNING: Table '{table_name}' found in DB but has no mapping to a CSV file. Skipping.")

        print("\nDatabase backup to CSVs completed successfully.")

    except Exception as e:
        print(f"An error occurred during the backup process: {e}")

if __name__ == '__main__':
    backup_database_to_csv()
