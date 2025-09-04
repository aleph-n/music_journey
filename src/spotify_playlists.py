import os
from sqlalchemy import create_engine, text
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timezone
from src.logger import setup_logger

# --- Configuration ---
OUTPUT_DIR = 'output'
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# --- Main Playlist Creation Function ---
def spotify_playlists(journey_name_filter=None, recreate=False):
    logger = setup_logger()
    engine = create_engine(f'sqlite:///{DB_PATH}')
    
    try:
        scope = "playlist-modify-public playlist-modify-private"
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        user_id = sp.current_user()['id']
        logger.info(f"Successfully authenticated with Spotify for user {sp.current_user()['display_name']}.")
    except Exception as e:
        logger.error(f"Could not authenticate with Spotify. Details: {e}")
        return

    journey_query_str = "SELECT JourneyID, JourneyName, JourneyDescription, Granularity FROM DimJourney"
    if journey_name_filter:
        journey_query_str += " WHERE JourneyName = :jname"
    journey_query = text(journey_query_str)
    
    with engine.connect() as connection:
        journeys = connection.execute(journey_query, {"jname": journey_name_filter} if journey_name_filter else {}).fetchall()
    
    if not journeys:
        logger.warning(f"No journeys found.")
        return

    for journey in journeys:
        j_id, j_name, j_desc, granularity = journey
        logger.info(f"Processing journey: '{j_name}' (Granularity: {granularity})")
        existing_playlist_id = get_existing_playlist_id(engine, j_id, 'Spotify')

        if recreate and existing_playlist_id:
            logger.warning(f" -> --recreate flag is set. Deleting playlist '{j_name}'.")
            try:
                sp.current_user_unfollow_playlist(existing_playlist_id)
                clear_playlist_id(engine, j_id, 'Spotify')
                logger.info(f" -> Deleted playlist and cleared local state.")
                existing_playlist_id = None
            except Exception as e:
                logger.error(f" -> Failed to delete playlist: {e}")
        
        item_uris = get_album_uris(engine, j_id, sp, logger) if granularity == 'Album' else get_track_uris(engine, j_id, logger)
        valid_item_uris = [uri for uri in item_uris if uri]

        if not valid_item_uris:
            logger.warning(f" -> No valid URIs found for '{j_name}'. Skipping.")
            continue
        
        if existing_playlist_id:
            logger.info(f" -> Updating existing playlist: '{j_name}'")
            try:
                sp.playlist_replace_items(existing_playlist_id, valid_item_uris[:100])
                for i in range(100, len(valid_item_uris), 100):
                    sp.playlist_add_items(existing_playlist_id, valid_item_uris[i:i+100])
                playlist_id = existing_playlist_id
            except Exception as e:
                logger.error(f"   - Failed to update playlist: {e}")
                continue
        else:
            logger.info(f" -> Creating new playlist: '{j_name}'")
            try:
                playlist = sp.user_playlist_create(user=user_id, name=j_name, public=False, description=j_desc)
                playlist_id = playlist['id']
                for i in range(0, len(valid_item_uris), 100):
                    sp.playlist_add_items(playlist_id, valid_item_uris[i:i+100])
            except Exception as e:
                logger.error(f"   - Failed to create playlist: {e}")
                continue

        logger.info(f" -> Successfully synced playlist. Spotify ID: {playlist_id}")
        save_playlist_id(engine, j_id, 'Spotify', playlist_id)

def get_track_uris(engine, journey_id, logger):
    """Fetches pre-curated track URIs for a track-level journey directly from the DWH."""
    # --- THIS QUERY IS NOW CORRECTED AND ROBUST ---
    query = text("""
        SELECT
            dr.SpotifyURI,
            COALESCE(dm.MovementTitle, dmw.Title) AS TrackTitle
        FROM FactJourneyStep fs
        JOIN DimRecording dr ON fs.RecordingID = dr.RecordingID
        LEFT JOIN DimMovement dm ON dr.MovementID = dm.MovementID
        LEFT JOIN DimMusicalWork dmw ON dm.WorkID = dmw.WorkID OR dr.WorkID = dmw.WorkID
        WHERE fs.JourneyID = :jid ORDER BY fs.StepOrder;
    """)
    with engine.connect() as connection:
        results = connection.execute(query, {"jid": journey_id}).fetchall()
    
    logger.info(f" -> Found {len(results)} steps in DWH.")
    track_uris = [row[0] for row in results if row[0] and isinstance(row[0], str) and row[0].startswith('spotify:track:')]
    if len(track_uris) != len(results):
        logger.warning(f"   - Found {len(results) - len(track_uris)} invalid or missing URIs.")
    return track_uris

def get_album_uris(engine, journey_id, sp, logger):
    query = text("""
        SELECT DISTINCT da.SpotifyURI, da.AlbumTitle
        FROM FactJourneyStep fs JOIN DimRecording dr ON fs.RecordingID = dr.RecordingID JOIN DimAlbum da ON dr.AlbumID = da.AlbumID
        WHERE fs.JourneyID = :jid AND da.SpotifyURI IS NOT NULL AND da.SpotifyURI != '' ORDER BY fs.StepOrder;
    """)
    with engine.connect() as connection:
        albums = connection.execute(query, {"jid": journey_id}).fetchall()
    logger.info(f" -> Found {len(albums)} album steps. Retrieving album tracks...")
    all_uris = []
    for uri, title in albums:
        try:
            tracks = sp.album_tracks(uri.split(':')[-1], market="US")
            all_uris.extend([track['uri'] for track in tracks['items']])
            logger.info(f"   - Found {len(tracks['items'])} tracks for album: '{title}'")
        except Exception as e:
            logger.error(f"   - Could not fetch tracks for album '{title}'. URI: {uri}. Error: {e}")
    return all_uris

def get_existing_playlist_id(engine, journey_id, service_id):
    query = text("SELECT ServicePlaylistID FROM DimPlaylist WHERE JourneyID = :jid AND ServiceID = :sid")
    with engine.connect() as connection:
        return connection.execute(query, {"jid": journey_id, "sid": service_id}).scalar_one_or_none()

def save_playlist_id(engine, journey_id, service_id, playlist_id):
    now_utc = datetime.now(timezone.utc).isoformat()
    query = text("""INSERT INTO DimPlaylist (JourneyID, ServiceID, ServicePlaylistID, LastUpdatedUTC) VALUES (:jid, :sid, :pid, :ts) ON CONFLICT(JourneyID, ServiceID) DO UPDATE SET ServicePlaylistID = excluded.ServicePlaylistID, LastUpdatedUTC = excluded.LastUpdatedUTC;""")
    with engine.connect() as connection:
        connection.execute(query, {"jid": journey_id, "sid": service_id, "pid": playlist_id, "ts": now_utc})
        connection.commit()

def clear_playlist_id(engine, journey_id, service_id):
    query = text("DELETE FROM DimPlaylist WHERE JourneyID = :jid AND ServiceID = :sid")
    with engine.connect() as connection:
        connection.execute(query, {"jid": journey_id, "sid": service_id})
        connection.commit()