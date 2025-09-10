import csv
from difflib import get_close_matches
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
if 'SpotifyURI' in df_album.columns:
    df_album.rename(columns={'SpotifyURI': 'SpotifyURL'}, inplace=True)
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
    # Try full query first
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
        results = sp.search(q=query, type='track', limit=5)
        items = results['tracks']['items']
        # Fuzzy match movement title if multiple results
        if items and movement_title:
            titles = [t['name'] for t in items]
            match = get_close_matches(movement_title, titles, n=1, cutoff=0.7)
            if match:
                for t in items:
                    if t['name'] == match[0]:
                        return t['uri']
            # If no close match, return first
            return items[0]['uri']
        elif items:
            return items[0]['uri']
    except Exception as e:
        logger.error(f"Spotify search error for query '{query}': {e}")
    # Fallback: try without movement
    if album_title and performer_name:
        fallback_query = f'album:"{album_title}" artist:"{performer_name}"'
        try:
            results = sp.search(q=fallback_query, type='track', limit=5)
            items = results['tracks']['items']
            if items:
                logger.warning(f"Ambiguous match for fallback query '{fallback_query}': {[t['name'] for t in items]}")
                return items[0]['uri']
        except Exception as e:
            logger.error(f"Spotify search error for fallback query '{fallback_query}': {e}")
    # Fallback: try only album
    if album_title:
        fallback_query = f'album:"{album_title}"'
        try:
            results = sp.search(q=fallback_query, type='track', limit=5)
            items = results['tracks']['items']
            if items:
                logger.warning(f"Ambiguous match for album-only query '{fallback_query}': {[t['name'] for t in items]}")
                return items[0]['uri']
        except Exception as e:
            logger.error(f"Spotify search error for album-only query '{fallback_query}': {e}")
    return None

def main():
    updated = 0
    unresolved = []
    for idx, row in df_recording.iterrows():
        movement_title, album_title, performer_name = get_metadata(row)
        album_url = None
        if not pd.isna(row['AlbumID']):
            a = df_album[df_album['AlbumID'] == row['AlbumID']]
            if not a.empty and 'SpotifyURL' in a.columns:
                album_url = a.iloc[0]['SpotifyURL']
        if album_url and isinstance(album_url, str) and album_url.startswith('https://open.spotify.com/album/'):
            # Use Spotify API to get album tracks
            album_id = album_url.split('/')[-1]
            try:
                album_tracks = sp.album_tracks(album_id)['items']
                # Try to match by movement title
                match = None
                if movement_title:
                    titles = [t['name'] for t in album_tracks]
                    close = get_close_matches(movement_title, titles, n=1, cutoff=0.7)
                    if close:
                        for t in album_tracks:
                            if t['name'] == close[0]:
                                match = t
                                break
                # If no close match, use track number if available
                if not match and 'track_number' in row and not pd.isna(row['track_number']):
                    for t in album_tracks:
                        if t['track_number'] == int(row['track_number']):
                            match = t
                            break
                # If still no match, use first track
                if not match and album_tracks:
                    match = album_tracks[0]
                if match:
                    df_recording.at[idx, 'SpotifyURL'] = match['uri']
                    logger.info(f"Overwrote URL for RecordingID {row['RecordingID']} from album: {match['uri']}")
                    updated += 1
                    continue
            except Exception as e:
                logger.error(f"Spotify album lookup error for {album_uri}: {e}")
        # Fallback to search only if no album URI or no match
        if pd.isna(row['SpotifyURL']) or not row['SpotifyURL']:
            uri = search_spotify_track(movement_title, album_title, performer_name)
            if uri:
                df_recording.at[idx, 'SpotifyURL'] = uri
                logger.info(f"Found URL for RecordingID {row['RecordingID']}: {uri}")
                updated += 1
            else:
                # Get descriptive fields for easier review
                movement_desc = None
                album_desc = None
                performer_desc = None
                if not pd.isna(row['MovementID']):
                    m = df_movement[df_movement['MovementID'] == row['MovementID']]
                    if not m.empty:
                        movement_desc = m.iloc[0]['MovementDescription']
                if not pd.isna(row['AlbumID']):
                    a = df_album[df_album['AlbumID'] == row['AlbumID']]
                    if not a.empty:
                        album_desc = a.iloc[0]['RecordingLabel']
                if not pd.isna(row['PerformerID']):
                    p = df_performer[df_performer['PerformerID'] == row['PerformerID']]
                    if not p.empty:
                        performer_desc = p.iloc[0]['InstrumentOrRole']
                unresolved.append({
                    'RecordingID': row['RecordingID'],
                    'MovementTitle': movement_title,
                    'MovementDescription': movement_desc,
                    'AlbumTitle': album_title,
                    'RecordingLabel': album_desc,
                    'PerformerName': performer_name,
                    'InstrumentOrRole': performer_desc
                })
    # Write unresolved cases to CSV
    if unresolved:
        with open(os.path.join(DATA_DIR, 'missing_spotify_uris.csv'), 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'RecordingID','MovementTitle','MovementDescription','AlbumTitle','RecordingLabel','PerformerName','InstrumentOrRole'])
            writer.writeheader()
            writer.writerows(unresolved)
        logger.info(f"Wrote {len(unresolved)} unresolved cases to missing_spotify_uris.csv")
    df_recording.to_csv(RECORDING_PATH, index=False)
    logger.info(f"Updated {updated} SpotifyURLs in {RECORDING_PATH}")

if __name__ == "__main__":
    main()
