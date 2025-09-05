import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import os
from dotenv import load_dotenv
load_dotenv()

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spotify_uri_lookup")

# --- Spotify API credentials ---
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

DATA_DIR = "data"
RECORDING_PATH = os.path.join(DATA_DIR, "DimRecording.csv")
MOVEMENT_PATH = os.path.join(DATA_DIR, "DimMovement.csv")
ALBUM_PATH = os.path.join(DATA_DIR, "DimAlbum.csv")
PERFORMER_PATH = os.path.join(DATA_DIR, "DimPerformer.csv")

# Load CSVs
df_recording = pd.read_csv(RECORDING_PATH)
df_movement = pd.read_csv(MOVEMENT_PATH)
df_album = pd.read_csv(ALBUM_PATH)
df_performer = pd.read_csv(PERFORMER_PATH)

def get_metadata(row):
    movement_title = None
    album_title = None
    performer_name = None
    # Get movement title
    if not pd.isna(row['MovementID']):
        m = df_movement[df_movement['MovementID'] == row['MovementID']]
        if not m.empty:
            movement_title = m.iloc[0]['MovementTitle']
    # Get album title
    if not pd.isna(row['AlbumID']):
        a = df_album[df_album['AlbumID'] == row['AlbumID']]
        if not a.empty:
            album_title = a.iloc[0]['AlbumTitle']
    # Get performer name
    if not pd.isna(row['PerformerID']):
        p = df_performer[df_performer['PerformerID'] == row['PerformerID']]
        if not p.empty:
            performer_name = p.iloc[0]['PerformerName']
    return movement_title, album_title, performer_name

def search_spotify_track(movement_title, album_title, performer_name):
    query_parts = []
    if movement_title:
        query_parts.append(f'track:"{movement_title}"')
    if album_title:
        query_parts.append(f'album:"{album_title}"')
    if performer_name:
        query_parts.append(f'artist:"{performer_name}"')
    query = " ".join(query_parts)
    if not query:
        return None
    try:
        results = sp.search(q=query, type='track', limit=1)
        items = results['tracks']['items']
        if items:
            return items[0]['uri']
    except Exception as e:
        logger.error(f"Spotify search error for query '{query}': {e}")
    return None

def main():
    updated = 0
    for idx, row in df_recording.iterrows():
        if pd.isna(row['SpotifyURI']) or not row['SpotifyURI']:
            movement_title, album_title, performer_name = get_metadata(row)
            uri = search_spotify_track(movement_title, album_title, performer_name)
            if uri:
                df_recording.at[idx, 'SpotifyURI'] = uri
                logger.info(f"Found URI for RecordingID {row['RecordingID']}: {uri}")
                updated += 1
            else:
                logger.warning(f"No URI found for RecordingID {row['RecordingID']} (movement: {movement_title}, album: {album_title}, performer: {performer_name})")
    df_recording.to_csv(RECORDING_PATH, index=False)
    logger.info(f"Updated {updated} SpotifyURIs in {RECORDING_PATH}")

if __name__ == "__main__":
    main()
