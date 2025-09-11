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
                playlist_info = sp.playlist(existing_playlist_id)
                current_playlist_name = playlist_info['name']
                # Always update playlist name and description to match journey
                sp.playlist_change_details(existing_playlist_id, name=j_name, description=j_desc)
                logger.info(f"   - Updated playlist name and description to match journey: '{j_name}'")
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

    try:
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        # Fetch actual playlist title from Spotify API
        playlist_info = sp.playlist(playlist_id)
        playlist_title = playlist_info.get('name', None)
    except UnboundLocalError as e:
        logger.error(f"playlist_id is not set: {e}")
        playlist_url = None
        playlist_title = None
    except Exception as e:
        logger.error(f"Failed to fetch playlist info for title: {e}")
        playlist_title = None
    try:
        logger.info(f" -> Successfully synced playlist. Spotify ID: {playlist_id} | {playlist_url}")
        save_playlist_id(engine, j_id, 'Spotify', playlist_id, playlist_title)
    except UnboundLocalError as e:
        logger.error(f"playlist_id is not set for logger/save: {e}")

def get_track_uris(engine, journey_id, logger):
    """Fetches pre-curated track URIs for a track-level journey directly from the DWH."""
    # --- THIS QUERY IS NOW CORRECTED AND ROBUST ---
    query = text("""
        SELECT
            dr.SpotifyURL,
            dm.MovementTitle AS TrackTitle
        FROM FactJourneyStep fs
        JOIN DimRecording dr ON fs.RecordingID = dr.RecordingID
        JOIN BridgeAlbumMovement bam ON dr.RecordingID = bam.recording_id
        JOIN DimMovement dm ON bam.movement_id = dm.MovementID
        WHERE fs.JourneyID = :jid ORDER BY fs.StepOrder;
    """)
    with engine.connect() as connection:
        results = connection.execute(query, {"jid": journey_id}).fetchall()
    
    logger.info(f" -> Found {len(results)} steps in DWH.")
    from spotipy.exceptions import SpotifyException
    import spotipy
    # Get a Spotipy client (reuse from main function if possible)
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public playlist-modify-private"))
    except Exception as e:
        logger.error(f"Could not authenticate with Spotify for URI validation: {e}")
        return []

    valid_uris = []
    invalid_uris = []
    for row in results:
        url = row[0]
        valid = False
        if url and isinstance(url, str) and url.startswith('https://open.spotify.com/track/'):
            track_id = url.split('/')[-1]
            if len(track_id) == 22 and track_id.isalnum():
                # Check existence on Spotify
                try:
                    sp.track(track_id)
                    valid = True
                except SpotifyException:
                    valid = False
                except Exception:
                    valid = False
        if valid:
            valid_uris.append(url)
        else:
            invalid_uris.append(url)
    if invalid_uris:
        logger.error(f"   - Found {len(invalid_uris)} invalid, missing, or not found URLs. Listing them:")
        for idx, url in enumerate(invalid_uris, 1):
            logger.error(f"     {idx}: '{url}' (invalid format or not found on Spotify)")
    return valid_uris

def get_album_uris(engine, journey_id, sp, logger):
    """
    For album-level journeys, fetch all tracks for each album in FactJourneyStep using AlbumID.
    """
    query = text("""
        SELECT fs.AlbumID, da.SpotifyURL, da.AlbumTitle
        FROM FactJourneyStep fs
        JOIN DimAlbum da ON fs.AlbumID = da.AlbumID
        WHERE fs.JourneyID = :jid AND fs.AlbumID IS NOT NULL AND fs.AlbumID != '' AND da.SpotifyURL IS NOT NULL AND da.SpotifyURL != ''
        ORDER BY fs.StepOrder;
    """)
    with engine.connect() as connection:
        albums = connection.execute(query, {"jid": journey_id}).fetchall()
    logger.info(f" -> Found {len(albums)} album steps. Retrieving album tracks...")
    all_uris = []
    for album_id, url, title in albums:
        try:
            if url.startswith('https://open.spotify.com/album/'):
                spotify_album_id = url.split('/')[-1]
                tracks = sp.album_tracks(spotify_album_id, market="US")
                all_uris.extend([track['uri'] for track in tracks['items']])
                logger.info(f"   - Found {len(tracks['items'])} tracks for album: '{title}' (AlbumID: {album_id})")
            else:
                logger.error(f"   - Invalid Spotify album URL: {url}")
        except Exception as e:
            logger.error(f"   - Could not fetch tracks for album '{title}'. URL: {url}. Error: {e}")
    return all_uris

def get_existing_playlist_id(engine, journey_id, service_id):
    query = text("SELECT SpotifyPlaylistURL FROM DimPlaylist WHERE JourneyID = :jid AND ServiceID = :sid")
    with engine.connect() as connection:
        return connection.execute(query, {"jid": journey_id, "sid": service_id}).scalar_one_or_none()

def save_playlist_id(engine, journey_id, service_id, playlist_id, playlist_title):
    now_utc = datetime.now(timezone.utc).isoformat()
    query = text("""INSERT INTO DimPlaylist (JourneyID, ServiceID, SpotifyPlaylistURL, SpotifyPlaylistTitle, LastUpdatedUTC) VALUES (:jid, :sid, :pid, :ptitle, :ts) ON CONFLICT(JourneyID, ServiceID) DO UPDATE SET SpotifyPlaylistURL = excluded.SpotifyPlaylistURL, SpotifyPlaylistTitle = excluded.SpotifyPlaylistTitle, LastUpdatedUTC = excluded.LastUpdatedUTC;""")
    with engine.connect() as connection:
        connection.execute(query, {"jid": journey_id, "sid": service_id, "pid": playlist_id, "ptitle": playlist_title, "ts": now_utc})
        connection.commit()

def clear_playlist_id(engine, journey_id, service_id):
    query = text("DELETE FROM DimPlaylist WHERE JourneyID = :jid AND ServiceID = :sid")
    with engine.connect() as connection:
        connection.execute(query, {"jid": journey_id, "sid": service_id})
        connection.commit()