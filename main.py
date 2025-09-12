import argparse
from src.build_dwh import build_data_warehouse
from src.spotify_playlists import spotify_playlists
from src.spotify_auth_test import test_spotify_auth
from src.backup_dwh import backup_database_to_csv

def main():
    """Main entrypoint for the project CLI."""
    parser = argparse.ArgumentParser(description="Music Journey Data Warehouse and Playlist Manager.")
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # Command: build
    parser_build = subparsers.add_parser('build', help='Builds or rebuilds the SQLite data warehouse from CSVs.')
    parser_build.set_defaults(func=build_data_warehouse)

    # Command: playlist
    parser_playlist = subparsers.add_parser('playlist', help='Creates or updates Spotify playlists from the DWH.')
    parser_playlist.add_argument(
        '--name', 
        type=str,
        default=None,
        help='(Optional) The name of a single journey to process.'
    )
    # --- ADD THIS ARGUMENT ---
    parser_playlist.add_argument(
        '--recreate',
        action='store_true', # This makes it a flag, e.g., --recreate
        help='(Optional) Deletes existing playlists and creates them from scratch.'
    )
    # --- END OF ADDITION ---
    parser_playlist.set_defaults(func=spotify_playlists)
    
    # Command: test-auth
    parser_auth = subparsers.add_parser('test-auth', help='Tests Spotify authentication.')
    parser_auth.set_defaults(func=test_spotify_auth)

    # Command: backup
    parser_backup = subparsers.add_parser('backup', help='Exports the SQLite database back to CSV files.')
    parser_backup.set_defaults(func=backup_database_to_csv)

    # Command: import-spotify-playlist
    parser_import = subparsers.add_parser('import-spotify-playlist', help='Imports a Spotify playlist and creates a journey.')
    parser_import.add_argument(
        'SpotifyPlaylistURL',
        type=str,
        help='The Spotify playlist URL to import.'
    )
    parser_import.add_argument(
        '--journey-id',
        type=str,
        default=None,
        help='(Optional) The JourneyID to use for the new journey.'
    )
    parser_import.add_argument(
        '--granularity',
        type=str,
        choices=['Album', 'Track'],
        default='Track',
        help='(Optional) Granularity for journey steps: Album or Track.'
    )
    def import_spotify_playlist_cli(SpotifyPlaylistURL, journey_id=None, granularity="Track"):
        from src.import_spotify_playlist import import_spotify_playlist
        import_spotify_playlist(SpotifyPlaylistURL, journey_id=journey_id, granularity=granularity)
    parser_import.set_defaults(func=import_spotify_playlist_cli)

    args = parser.parse_args()
    
    # Call the function associated with the chosen command
    if args.command == 'playlist':
        args.func(journey_name_filter=args.name, recreate=args.recreate)
    elif args.command == 'import-spotify-playlist':
        args.func(
            args.SpotifyPlaylistURL,
            journey_id=args.journey_id,
            granularity=args.granularity
        )
    else:
        args.func()

if __name__ == "__main__":
    main()