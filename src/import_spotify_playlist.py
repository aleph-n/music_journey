import os
from dotenv import load_dotenv
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
from src.generate_dwh_journey import generate_dwh_journey

load_dotenv()

# --- Configuration ---
OUTPUT_DIR = "output"
DB_NAME = "music_journeys.db"
DB_PATH = os.path.join(OUTPUT_DIR, DB_NAME)

# --- Main Import Function ---


def import_spotify_playlist(playlist_url, journey_id=None, granularity="Track"):

    logger = logging.getLogger("import_spotify_playlist")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    # File handler
    fh = logging.FileHandler("output/import_spotify_playlist.log", mode="a")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    # Avoid duplicate handlers
    if not logger.hasHandlers():
        logger.addHandler(ch)
        logger.addHandler(fh)
    else:
        logger.handlers.clear()
        logger.addHandler(ch)
        logger.addHandler(fh)
    logger.info(f"Starting import for playlist: {playlist_url}")
    logger.info(f"Using database file: {os.path.abspath(DB_PATH)}")

    # Authenticate with Spotify
    try:
        scope = "playlist-modify-public playlist-modify-private"
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        user = sp.current_user()
        user_id = user["id"]
        creator_name = user.get("display_name", user_id)
        logger.info(f"Authenticated with Spotify for user {creator_name}.")
    except Exception as e:
        logger.error(f"Could not authenticate with Spotify. Details: {e}")
        return

    # Connect to database
    engine = create_engine(f"sqlite:///{DB_PATH}")
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            # Fetch playlist details
            try:
                playlist = sp.playlist(playlist_url.split("/")[-1].split("?")[0])
                playlist_name = playlist["name"]
                playlist_desc = playlist.get("description", "")
                playlist_url_actual = playlist["external_urls"]["spotify"]
                tracks = playlist["tracks"]["items"]
                logger.info(
                    f"Fetched playlist '{playlist_name}' with {len(tracks)} tracks."
                )
            except Exception as e:
                logger.error(f"Failed to fetch playlist details: {e}")
                trans.rollback()
                return

            # Insert or update journey
            if not journey_id:
                journey_id = playlist_url.split("/")[-1].split("?")[0]
            journey_query = text(
                """
                INSERT INTO DimJourney (JourneyID, JourneyName, JourneyDescription, CreatorName, Granularity)
                VALUES (:jid, :jname, :jdesc, :creator, :gran)
                ON CONFLICT(JourneyID) DO UPDATE SET JourneyName=excluded.JourneyName, JourneyDescription=excluded.JourneyDescription, CreatorName=excluded.CreatorName, Granularity=excluded.Granularity;
            """
            )
            connection.execute(
                journey_query,
                {
                    "jid": journey_id,
                    "jname": playlist_name,
                    "jdesc": playlist_desc,
                    "creator": creator_name,
                    "gran": granularity,
                },
            )
            logger.info(
                f"Journey '{playlist_name}' ({journey_id}) imported with granularity '{granularity}' and creator '{creator_name}'."
            )

            # Insert or update DimPlaylist
            playlist_query = text(
                """
                INSERT INTO DimPlaylist (JourneyID, ServiceID, SpotifyPlaylistURL, SpotifyPlaylistTitle, LastUpdatedUTC)
                VALUES (:jid, 'Spotify', :url, :title, :updated)
                ON CONFLICT(JourneyID, ServiceID) DO UPDATE SET SpotifyPlaylistURL=excluded.SpotifyPlaylistURL, SpotifyPlaylistTitle=excluded.SpotifyPlaylistTitle, LastUpdatedUTC=excluded.LastUpdatedUTC;
            """
            )
            connection.execute(
                playlist_query,
                {
                    "jid": journey_id,
                    "url": playlist_url_actual,
                    "title": playlist_name,
                    "updated": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.info(f"DimPlaylist updated for journey {journey_id}.")
            # Remove existing steps for this journey
            del_steps_query = text("DELETE FROM FactJourneyStep WHERE JourneyID = :jid")
            connection.execute(del_steps_query, {"jid": journey_id})
            logger.info(f"Removed existing steps for journey {journey_id}.")

            # Helper: get next integer ID for a table
            def get_next_id(table, id_col):
                result = connection.execute(text(f"SELECT MAX({id_col}) FROM {table}"))
                max_id = result.scalar()
                return (max_id or 0) + 1

            # Helper: get or insert performer
            def get_or_create_performer(artist):
                name = artist["name"]
                role = artist.get("type", None)
                if role:
                    if role.lower() == "artist":
                        role_val = "Artist"
                    elif role.lower() == "band":
                        role_val = "Band"
                    else:
                        role_val = role.capitalize()
                else:
                    role_val = None
                upsert = text(
                    """
                    INSERT INTO DimPerformer (PerformerName, InstrumentOrRole)
                    VALUES (:name, :role)
                    ON CONFLICT(PerformerName) DO UPDATE SET InstrumentOrRole=excluded.InstrumentOrRole
                """
                )
                connection.execute(upsert, {"name": name, "role": role_val})
                logger.info(f"Upserted performer: {name} with role {role_val}")
                sel = text(
                    "SELECT PerformerID FROM DimPerformer WHERE PerformerName = :name"
                )
                res = connection.execute(sel, {"name": name}).fetchone()
                logger.info(
                    f"Upserted performer: {name} (ID: {res[0]}) with role {role_val}"
                )
                return res[0]

            # Helper: get or insert album
            def get_or_create_album(album, performer_id):
                title = album["name"]
                spotify_url = (
                    album["external_urls"]["spotify"]
                    if "external_urls" in album and "spotify" in album["external_urls"]
                    else None
                )
                spotify_title = album.get("name", None)
                release_date = album.get("release_date", None)
                release_year = None
                if release_date:
                    # release_date can be 'YYYY', 'YYYY-MM', or 'YYYY-MM-DD'
                    try:
                        release_year = int(release_date[:4])
                    except (ValueError, TypeError):
                        release_year = None
                label = album.get("label", None)
                spotify_genre = (
                    ",".join(album.get("genres", [])) if album.get("genres") else None
                )
                upsert = text(
                    """
                    INSERT INTO DimAlbum (AlbumTitle, PerformerID, SpotifyReleaseDate, RecordingLabel, SpotifyGenre, SpotifyURL, SpotifyTitle)
                    VALUES (:title, :pid, :reldate, :label, :spotify_genre, :spotify_url, :spotify_title)
                    ON CONFLICT(AlbumTitle, PerformerID) DO UPDATE SET
                        SpotifyReleaseDate=excluded.SpotifyReleaseDate,
                        RecordingLabel=excluded.RecordingLabel,
                        SpotifyGenre=excluded.SpotifyGenre,
                        SpotifyURL=excluded.SpotifyURL,
                        SpotifyTitle=excluded.SpotifyTitle
                    """
                )
                album_params = {
                    "title": title,
                    "pid": performer_id,
                    "reldate": release_year,
                    "label": label,
                    "spotify_genre": spotify_genre,
                    "spotify_url": spotify_url,
                    "spotify_title": spotify_title,
                }
                connection.execute(upsert, album_params)
                logger.info(f"Upserted album: {title} performer {performer_id}")
                sel = text(
                    "SELECT AlbumID FROM DimAlbum WHERE AlbumTitle = :title AND PerformerID = :pid"
                )
                res = connection.execute(
                    sel, {"title": title, "pid": performer_id}
                ).fetchone()
                logger.info(
                    f"Upserted album: {title} (ID: {res[0]}) performer {performer_id}"
                )
                return res[0]

            # Track unique albums for album-level journeys
            album_keys = set()
            step_order = 1
            # Removed unused max_id assignment
            for item in tracks:
                track = item["track"]
                logger.info(
                    f"Processing track: {track.get('name', 'Unknown')} | Artists: {[a['name'] for a in track.get('artists', [])]}"
                )
                main_artist = (
                    track["artists"][0] if track["artists"] else {"name": "Unknown"}
                )
                logger.info(f"Main artist: {main_artist['name']}")
                performer_id = get_or_create_performer(main_artist)
                logger.info(f"Performer ID: {performer_id}")
                album_id_spotify = track["album"]["id"]
                album_api = sp.album(album_id_spotify)
                logger.info(
                    f"Album API: {album_api.get('name', 'Unknown')} | Spotify ID: {album_id_spotify}"
                )
                album_id = get_or_create_album(album_api, performer_id)
                logger.info(f"Album ID: {album_id}")
                if granularity == "Album":
                    album_key = (album_id, performer_id)
                    if album_key in album_keys:
                        logger.info(
                            f"Skipping duplicate album step: {album_api['name']} (ID: {album_id}) performer {performer_id}"
                        )
                        continue
                    album_keys.add(album_key)
                    step_params = {
                        "jid": journey_id,
                        "order": step_order,
                        "aid": album_id,
                    }
                    logger.info(f"Attempting to upsert album step: {step_params}")
                    step_query = text(
                        """
                        INSERT INTO FactJourneyStep (JourneyID, StepOrder, AlbumID)
                        VALUES (:jid, :order, :aid)
                        ON CONFLICT(JourneyID, StepOrder) DO UPDATE SET AlbumID=-999
                    """
                    )
                    try:
                        result = connection.execute(step_query, step_params)
                        if getattr(result, "rowcount", None) == 0:
                            logger.info(
                                f"CONFLICT: Dummy record inserted for params={step_params}"
                            )
                        else:
                            logger.info(
                                f"Upserted album step: params={step_params}, rowcount={getattr(result, 'rowcount', 'N/A')}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to upsert album step: params={step_params}, error={e}"
                        )
                else:
                    step_params = {
                        "jid": journey_id,
                        "order": step_order,
                        "rid": track["id"],
                    }
                    logger.info(f"Attempting to upsert track step: {step_params}")
                    step_query = text(
                        """
                        INSERT INTO FactJourneyStep (JourneyID, StepOrder, RecordingID)
                        VALUES (:jid, :order, :rid)
                        ON CONFLICT(JourneyID, StepOrder) DO UPDATE SET RecordingID=excluded.RecordingID
                    """
                    )
                    try:
                        result = connection.execute(step_query, step_params)
                        logger.info(
                            f"Upserted track step: params={step_params}, rowcount={getattr(result, 'rowcount', 'N/A')}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to upsert track step: params={step_params}, error={e}"
                        )
                step_order += 1
            logger.info(f"Imported {step_order-1} steps for journey {journey_id}.")
            # --- Import Verification Step ---
            logger.info("Starting import verification...")
            # Fetch journey steps from DB
            if granularity == "Album":
                db_steps = connection.execute(
                    text(
                        "SELECT StepOrder, AlbumID FROM FactJourneyStep WHERE JourneyID = :jid ORDER BY StepOrder"
                    ),
                    {"jid": journey_id},
                ).fetchall()
                # Build expected steps from playlist
                expected_steps = []
                album_keys = set()
                order = 1
                for item in tracks:
                    track = item["track"]
                    main_artist = (
                        track["artists"][0] if track["artists"] else {"name": "Unknown"}
                    )
                    performer_id = get_or_create_performer(main_artist)
                    album_id_spotify = track["album"]["id"]
                    album_api = sp.album(album_id_spotify)
                    album_id = get_or_create_album(album_api, performer_id)
                    album_key = (album_id, performer_id)
                    if album_key in album_keys:
                        continue
                    album_keys.add(album_key)
                    expected_steps.append((order, album_id))
                    order += 1
                # Compare
                match_count = len(db_steps) == len(expected_steps)
                match_order = all(
                    db == exp for db, exp in zip(db_steps, expected_steps)
                )
                logger.info(
                    f"Verification: DB steps={len(db_steps)}, Playlist albums={len(expected_steps)}"
                )
                if match_count and match_order:
                    logger.info(
                        "Import verification PASSED: Album steps match playlist order and count."
                    )
                else:
                    logger.warning(
                        "Import verification FAILED: Album steps do not match playlist."
                    )
                    # Log mismatches
                    for i, (db, exp) in enumerate(zip(db_steps, expected_steps)):
                        if db != exp:
                            logger.warning(f"Step {i+1}: DB={db}, Playlist={exp}")
            else:
                db_steps = connection.execute(
                    text(
                        "SELECT StepOrder, RecordingID FROM FactJourneyStep WHERE JourneyID = :jid ORDER BY StepOrder"
                    ),
                    {"jid": journey_id},
                ).fetchall()
                expected_steps = []
                order = 1
                for item in tracks:
                    track = item["track"]
                    expected_steps.append((order, track["id"]))
                    order += 1
                match_count = len(db_steps) == len(expected_steps)
                match_order = all(
                    db == exp for db, exp in zip(db_steps, expected_steps)
                )
                logger.info(
                    f"Verification: DB steps={len(db_steps)}, Playlist tracks={len(expected_steps)}"
                )
                if match_count and match_order:
                    logger.info(
                        "Import verification PASSED: Track steps match playlist order and count."
                    )
                else:
                    logger.warning(
                        "Import verification FAILED: Track steps do not match."
                    )
                    for i, (db, exp) in enumerate(zip(db_steps, expected_steps)):
                        if db != exp:
                            logger.warning(f"Step {i+1}: DB={db}, Playlist={exp}")
            # Call Gemini essay generation
            try:
                generate_dwh_journey(journey_id, granularity)
                logger.info(f"Generated Gemini journey essay for {journey_id}.")
            except Exception as e:
                logger.error(f"Failed to generate Gemini journey essay: {e}")
            trans.commit()
            logger.info("All upserts committed successfully.")
        except Exception as e:
            trans.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")


# --- CLI Entrypoint ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import a Spotify playlist into the music journey database."
    )
    parser.add_argument("playlist_url", help="Spotify playlist URL")
    parser.add_argument(
        "--journey-id", help="Journey ID to use (default: derived from playlist)"
    )
    parser.add_argument(
        "--granularity",
        choices=["Track", "Album"],
        default="Track",
        help="Step granularity: Track or Album (default: Track)",
    )
    args = parser.parse_args()
    import_spotify_playlist(
        args.playlist_url, journey_id=args.journey_id, granularity=args.granularity
    )
