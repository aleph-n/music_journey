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
                SpotifyURL TEXT,
                SpotifyTitle TEXT,
                SpotifyTitleMatch BOOLEAN,
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
                SpotifyURL TEXT,
                SpotifyTitle TEXT,
                SpotifyTitleMatch BOOLEAN
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

            # Add SpotifyTitle and SpotifyTitleMatch columns for albums and recordings
            if table_name == 'DimAlbum' and 'SpotifyURL' in df.columns:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
                sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
                df['SpotifyTitle'] = ''
                df['SpotifyTitleMatch'] = False
                for idx, row in df.iterrows():
                    url = row['SpotifyURL']
                    if isinstance(url, str) and url.startswith('https://open.spotify.com/album/'):
                        album_id = url.split('/')[-1]
                        try:
                            album = sp.album(album_id)
                            spotify_title = album['name']
                            df.at[idx, 'SpotifyTitle'] = spotify_title
                            df.at[idx, 'SpotifyTitleMatch'] = (spotify_title.strip().lower() == str(row['AlbumTitle']).strip().lower())
                        except Exception:
                            df.at[idx, 'SpotifyTitle'] = ''
                            df.at[idx, 'SpotifyTitleMatch'] = False
            if table_name == 'DimRecording' and 'SpotifyURL' in df.columns:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
                sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
                df['SpotifyTitle'] = ''
                df['SpotifyTitleMatch'] = False
                # Load DimMovement for MovementTitle lookup
                movement_path = os.path.join(DATA_DIR, 'DimMovement.csv')
                df_movement = pd.read_csv(movement_path)
                movement_title_map = dict(zip(df_movement['MovementID'], df_movement['MovementTitle']))
                for idx, row in df.iterrows():
                    url = row['SpotifyURL']
                    if isinstance(url, str) and url.startswith('https://open.spotify.com/track/'):
                        track_id = url.split('/')[-1]
                        try:
                            track = sp.track(track_id)
                            spotify_title = track['name']
                            df.at[idx, 'SpotifyTitle'] = spotify_title
                            movement_title = movement_title_map.get(row['MovementID'], '')
                            df.at[idx, 'SpotifyTitleMatch'] = (spotify_title.strip().lower() == str(movement_title).strip().lower())
                        except Exception:
                            df.at[idx, 'SpotifyTitle'] = ''
                            df.at[idx, 'SpotifyTitleMatch'] = False

            # --- START DATA CLEANING FIX ---
            if table_name == 'DimRecording' and 'SpotifyURL' in df.columns:
                print(f"   -> Cleaning SpotifyURL column in {csv_file}...")
                if df['SpotifyURL'].dtype == object:
                    df['SpotifyURL'] = df['SpotifyURL'].str.replace(r'[^a-zA-Z0-9:/._-]', '', regex=True)
                    print(f"   -> Cleaning complete.")
                else:
                    print(f"   -> Skipping cleaning: SpotifyURL column is not string type.")
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

