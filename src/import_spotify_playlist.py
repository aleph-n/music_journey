import os
from dotenv import load_dotenv
load_dotenv()
from src.logger import setup_logger
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sqlalchemy import create_engine, text
from datetime import datetime, timezone

# --- Configuration ---
OUTPUT_DIR = 'output'
DB_NAME = 'music_journeys.db'
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# --- Main Import Function ---

def import_spotify_playlist(playlist_url, journey_id=None, granularity="Track"):

    logger = setup_logger()
    logger.info(f"Starting import for playlist: {playlist_url}")

    # Authenticate with Spotify
    try:
        scope = "playlist-modify-public playlist-modify-private"
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        user_id = sp.current_user()['id']
        logger.info(f"Authenticated with Spotify for user {sp.current_user()['display_name']}.")
    except Exception as e:
        logger.error(f"Could not authenticate with Spotify. Details: {e}")
        return

    # Connect to database
    engine = create_engine(f'sqlite:///{DB_PATH}')
    with engine.connect() as connection:
        # Fetch playlist details
        try:
            playlist = sp.playlist(playlist_url.split('/')[-1].split('?')[0])
            playlist_name = playlist['name']
            playlist_desc = playlist.get('description', '')
            tracks = playlist['tracks']['items']
            logger.info(f"Fetched playlist '{playlist_name}' with {len(tracks)} tracks.")
        except Exception as e:
            logger.error(f"Failed to fetch playlist details: {e}")
            return

        # Insert or update journey
        if not journey_id:
            journey_id = playlist_url.split('/')[-1].split('?')[0]
        journey_query = text("""
            INSERT INTO DimJourney (JourneyID, JourneyName, JourneyDescription, Granularity)
            VALUES (:jid, :jname, :jdesc, :gran)
            ON CONFLICT(JourneyID) DO UPDATE SET JourneyName=excluded.JourneyName, JourneyDescription=excluded.JourneyDescription, Granularity=excluded.Granularity;
        """)
        connection.execute(journey_query, {"jid": journey_id, "jname": playlist_name, "jdesc": playlist_desc, "gran": granularity})
        connection.commit()
        logger.info(f"Journey '{playlist_name}' ({journey_id}) imported with granularity '{granularity}'.")

        # Remove existing steps for this journey
        del_steps_query = text("DELETE FROM FactJourneyStep WHERE JourneyID = :jid")
        connection.execute(del_steps_query, {"jid": journey_id})
        connection.commit()
        logger.info(f"Removed existing steps for journey {journey_id}.")


        # Helper: get next integer ID for a table
        def get_next_id(table, id_col):
            result = connection.execute(text(f"SELECT MAX({id_col}) FROM {table}"))
            max_id = result.scalar()
            return (max_id or 0) + 1

        # Helper: get or insert performer
        def get_or_create_performer(artist):
            name = artist['name']
            sel = text("SELECT PerformerID FROM DimPerformer WHERE PerformerName = :name")
            res = connection.execute(sel, {"name": name}).fetchone()
            if res:
                return res[0]
            new_id = get_next_id('DimPerformer', 'PerformerID')
            ins = text("INSERT INTO DimPerformer (PerformerID, PerformerName) VALUES (:id, :name)")
            connection.execute(ins, {"id": new_id, "name": name})
            logger.info(f"Inserted new performer: {name} (ID: {new_id})")
            return new_id

        # Helper: get or insert album
        def get_or_create_album(album, performer_id):
            title = album['name']
            sel = text("SELECT AlbumID FROM DimAlbum WHERE AlbumTitle = :title AND PerformerID = :pid")
            res = connection.execute(sel, {"title": title, "pid": performer_id}).fetchone()
            if res:
                return res[0]
            new_id = get_next_id('DimAlbum', 'AlbumID')
            release_date = album.get('release_date', None)
            release_precision = album.get('release_date_precision', None)
            label = album.get('label', None)
            spotify_genre = ','.join(album.get('genres', [])) if album.get('genres') else None
            ins = text("""
                INSERT INTO DimAlbum (AlbumID, AlbumTitle, PerformerID, SpotifyReleaseDate, RecordingLabel, SpotifyGenre)
                VALUES (:id, :title, :pid, :reldate, :label, :spotify_genre)
            """)
            connection.execute(ins, {
                "id": new_id,
                "title": title,
                "pid": performer_id,
                "reldate": release_date,
                "label": label,
                "spotify_genre": spotify_genre
            })
            logger.info(f"Inserted new album: {title} (ID: {new_id})")
            return new_id

        # Track unique albums for album-level journeys
        album_keys = set()
        step_order = 1
        for item in tracks:
            track = item['track']
            # Get performer
            main_artist = track['artists'][0] if track['artists'] else {"name": "Unknown"}
            performer_id = get_or_create_performer(main_artist)

            # Get album
            album_id_spotify = track['album']['id']
            album_api = sp.album(album_id_spotify)
            album_id = get_or_create_album(album_api, performer_id)

            if granularity == "Album":
                album_key = (album_id, performer_id)
                if album_key in album_keys:
                    continue  # Avoid duplicate album steps
                album_keys.add(album_key)
                step_query = text("""
                    INSERT INTO FactJourneyStep (JourneyID, StepOrder, AlbumID)
                    VALUES (:jid, :order, :aid)
                """)
                connection.execute(step_query, {"jid": journey_id, "order": step_order, "aid": album_id})
                logger.info(f"Added album step: {album_api['name']} (ID: {album_id})")
            else:
                # Track-level step
                step_query = text("""
                    INSERT INTO FactJourneyStep (JourneyID, StepOrder, RecordingID)
                    VALUES (:jid, :order, :rid)
                """)
                connection.execute(step_query, {"jid": journey_id, "order": step_order, "rid": track['id']})
                logger.info(f"Added track step: {track['name']} ({track['id']})")
            step_order += 1
        connection.commit()
        logger.info(f"Imported {step_order-1} steps for journey {journey_id}.")

