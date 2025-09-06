import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Configuration ---
DATA_DIR = 'data'
OUTPUT_DIR = 'output'
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# Define all tables and their corresponding CSV files
TABLES = {
    'DimMusicalWork': 'DimMusicalWork.csv',
    'DimPerformer': 'DimPerformer.csv',
    'DimMovement': 'DimMovement.csv',
    'DimAlbum': 'DimAlbum.csv',
    'DimRecording': 'DimRecording.csv',
    'DimJourney': 'DimJourney.csv',
    'FactJourneyStep': 'FactJourneyStep.csv',
    'DimPlaylist': 'DimPlaylist.csv',
    'BridgeAlbumMovement': 'BridgeAlbumMovement.csv'
}

def build_data_warehouse():
    """
    Extracts data from CSV files and loads it into a SQLite database.
    This version explicitly creates the DimPlaylist table with a composite primary key.
    """
    print("Starting the Data Warehouse build process...")

    # --- Create Output Directory ---
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating output directory at: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    # --- Create Database Engine ---
    engine = create_engine(f'sqlite:///{DB_PATH}')
    print(f"Database engine created. DWH will be built at: {DB_PATH}")

    # --- Drop and Recreate All Tables ---
    with engine.connect() as connection:
        for table_name in TABLES.keys():
            print(f"Dropping table if exists: {table_name}")
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        print("Recreating all tables with updated schema...")
        # DimMusicalWork
        connection.execute(text("""
            CREATE TABLE DimMusicalWork (
                WorkID TEXT PRIMARY KEY,
                WorkType TEXT,
                Genre TEXT,
                Title TEXT,
                WorkDescription TEXT
            );
        """))
        # DimPerformer
        connection.execute(text("""
            CREATE TABLE DimPerformer (
                PerformerID TEXT PRIMARY KEY,
                PerformerName TEXT,
                InstrumentOrRole TEXT
            );
        """))
        # DimAlbum
        connection.execute(text("""
            CREATE TABLE DimAlbum (
                AlbumID TEXT PRIMARY KEY,
                AlbumTitle TEXT,
                PerformerID TEXT,
                SpotifyURI TEXT,
                RecordingLabel TEXT
            );
        """))
        # DimMovement
        connection.execute(text("""
            CREATE TABLE DimMovement (
                MovementID TEXT PRIMARY KEY,
                WorkID TEXT,
                MovementNumber TEXT,
                MovementTitle TEXT,
                MovementDescription TEXT
            );
        """))
        # DimRecording
        connection.execute(text("""
            CREATE TABLE DimRecording (
                RecordingID TEXT PRIMARY KEY,
                AlbumID TEXT,
                MovementID TEXT,
                WorkID TEXT,
                PerformerID TEXT,
                SpotifyURI TEXT
            );
        """))
        # DimJourney
        connection.execute(text("""
            CREATE TABLE DimJourney (
                JourneyID TEXT PRIMARY KEY,
                JourneyName TEXT,
                JourneyDescription TEXT,
                CreatorName TEXT,
                Granularity TEXT,
                JourneyTheme TEXT
            );
        """))
        # FactJourneyStep
        connection.execute(text("""
            CREATE TABLE FactJourneyStep (
                JourneyStepID TEXT PRIMARY KEY,
                JourneyID TEXT,
                RecordingID TEXT,
                StepOrder TEXT,
                ActNumber TEXT,
                ActTitle TEXT,
                CurationNotes TEXT,
                WhyThisRecording TEXT
            );
        """))
        # DimPlaylist
        connection.execute(text("""
            CREATE TABLE DimPlaylist (
                JourneyID TEXT,
                ServiceID TEXT,
                ServicePlaylistID TEXT,
                LastUpdatedUTC TEXT,
                PRIMARY KEY (JourneyID, ServiceID)
            );
        """))
        # BridgeAlbumMovement
        connection.execute(text("""
            CREATE TABLE BridgeAlbumMovement (
                album_id TEXT,
                movement_id TEXT,
                track_number TEXT,
                recording_id TEXT,
                PRIMARY KEY (album_id, movement_id, recording_id)
            );
        """))
        connection.commit()
        print("All tables created successfully.")

    # --- Loop Through Tables and Load Data ---
    for table_name, csv_file in TABLES.items():
        try:
            csv_path = os.path.join(DATA_DIR, csv_file)
            print(f"Processing {csv_file} -> loading into table '{table_name}'...")

            df = pd.read_csv(csv_path)

            # --- START DATA CLEANING FIX ---
            if table_name == 'DimRecording' and 'SpotifyURI' in df.columns:
                print(f"   -> Cleaning SpotifyURI column in {csv_file}...")
                if df['SpotifyURI'].dtype == object:
                    df['SpotifyURI'] = df['SpotifyURI'].str.replace(r'[^a-zA-Z0-9:-]', '', regex=True)
                    print(f"   -> Cleaning complete.")
                else:
                    print(f"   -> Skipping cleaning: SpotifyURI column is not string type.")
            # --- END DATA CLEANING FIX ---

            # For DimPlaylist, append since we've already created the table
            if table_name == 'DimPlaylist':
                if not df.empty:
                    df.to_sql(table_name, con=engine, if_exists='append', index=False)
                    print(f"Successfully appended {len(df)} rows into '{table_name}'.")
                else:
                    print(f"'{table_name}' CSV is empty, skipping append.")
            else:
                df.to_sql(table_name, con=engine, if_exists='replace', index=False)
                print(f"Successfully loaded {len(df)} rows into '{table_name}'.")

        except FileNotFoundError:
            print(f"ERROR: CSV file not found at {csv_path}. Skipping table '{table_name}'.")
        except Exception as e:
            print(f"An error occurred while processing {csv_file}: {e}")

    print("\nData Warehouse build process is complete.")
    print(f"Database is located at: {DB_PATH}")

