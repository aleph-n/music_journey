import os
import pandas as pd
from sqlalchemy import create_engine, text
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timezone

# --- Configuration ---
OUTPUT_DIR = 'output'
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

def spotify_playlists(journey_name=None):
    """
    Connects to the DWH, retrieves journey steps, and creates/updates a Spotify playlist.
    If journey_name is None, it processes all journeys.
    """
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}. Please run build_dwh.py first.")
        return
    engine = create_engine(f'sqlite:///{DB_PATH}')

    try:
        scope = "playlist-modify-public playlist-modify-private"
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        user_id = sp.current_user()['id']
        print(f"Successfully authenticated with Spotify for user {user_id}.")
    except Exception as e:
        print(f"ERROR: Could not authenticate with Spotify. Details: {e}")
        return

    journey_query = "SELECT JourneyID, JourneyName, JourneyDescription FROM DimJourney"
    if journey_name:
        journey_query += f" WHERE JourneyName = '{journey_name}'"
    
    journeys = pd.read_sql(journey_query, engine)
    print(f"Found {len(journeys)} journey(s) to process.")

    for _, journey in journeys.iterrows():
        j_id, j_name, j_desc = journey['JourneyID'], journey['JourneyName'], journey['JourneyDescription']
        print(f"\n--- Processing Journey: {j_name} ---")

        tracks_query = f"""
        SELECT mw.Title, mw.PrimaryArtist, mw.WorkType
        FROM FactJourneyStep fs
        JOIN DimRecording dr ON fs.RecordingID = dr.RecordingID
        JOIN DimMusicalWork mw ON dr.WorkID = mw.WorkID
        WHERE fs.JourneyID = '{j_id}' ORDER BY fs.StepOrder;
        """
        playlist_df = pd.read_sql(tracks_query, engine)
        
        track_uris = []
        print("Searching for tracks on Spotify...")
        for _, track in playlist_df.iterrows():
            query_type = 'track'
            query = f"track:{track['Title']} artist:{track['PrimaryArtist']}"
            if track['WorkType'] == 'Album':
                query_type = 'album'
                query = f"album:{track['Title']} artist:{track['PrimaryArtist']}"
            
            results = sp.search(q=query, type=query_type, limit=1)
            items = results[f'{query_type}s']['items']
            if items:
                uri = items[0]['uri']
                if query_type == 'album':
                    album_tracks = sp.album_tracks(uri)
                    track_uris.extend([t['uri'] for t in album_tracks['items']])
                else:
                    track_uris.append(uri)
                print(f"  Found: {track['Title']} by {track['PrimaryArtist']}")
            else:
                print(f"  Could not find: {track['Title']} by {track['PrimaryArtist']}")

        if not track_uris:
            print("No tracks were found on Spotify. Skipping playlist creation.")
            continue

        playlist_id = get_existing_playlist_id(engine, j_id, 'Spotify')

        if playlist_id:
            print(f"Updating existing playlist (ID: {playlist_id})...")
            sp.playlist_replace_items(playlist_id, track_uris)
        else:
            print("Creating new playlist...")
            playlist = sp.user_playlist_create(user=user_id, name=j_name, public=False, description=j_desc)
            playlist_id = playlist['id']
            sp.playlist_add_items(playlist_id, track_uris)
        
        save_playlist_id(engine, j_id, 'Spotify', playlist_id)

def get_existing_playlist_id(engine, journey_id, service_id):
    """Checks the DimPlaylist table for an existing playlist ID."""
    query = text("SELECT ServicePlaylistID FROM DimPlaylist WHERE JourneyID = :jid AND ServiceID = :sid")
    with engine.connect() as connection:
        result = connection.execute(query, {"jid": journey_id, "sid": service_id}).scalar_one_or_none()
    return result

def save_playlist_id(engine, journey_id, service_id, playlist_id):
    """Saves or updates the playlist ID in the DimPlaylist table using an UPSERT."""
    now_utc = datetime.now(timezone.utc).isoformat()
    query = text("""
    INSERT INTO DimPlaylist (JourneyID, ServiceID, ServicePlaylistID, LastUpdatedUTC)
    VALUES (:jid, :sid, :pid, :ts)
    ON CONFLICT(JourneyID, ServiceID) DO UPDATE SET
        ServicePlaylistID = excluded.ServicePlaylistID,
        LastUpdatedUTC = excluded.LastUpdatedUTC;
    """)
    with engine.connect() as connection:
        connection.execute(query, {"jid": journey_id, "sid": service_id, "pid": playlist_id, "ts": now_utc})
        connection.commit()
    print(f"Saved playlist ID {playlist_id} to the database.")
