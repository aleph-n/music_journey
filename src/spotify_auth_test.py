import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


def test_spotify_auth():
    """
    Authenticates with the Spotify API and prints the current user's information.
    """
    # Load environment variables from a .env file
    load_dotenv()

    try:
        # Define the necessary scopes for playlist modification
        scope = "playlist-modify-public playlist-modify-private"

        # Initialize the Spotify client with OAuth 2.0
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

        # Fetch the current user's information to confirm authentication
        user = sp.current_user()

        # Print a success message
        print(
            f"Successfully authenticated with Spotify as: {user['display_name']} ({user['id']})"
        )

    except Exception as e:
        # Print a helpful error message if authentication fails
        print(f"ERROR: Could not authenticate with Spotify. Details: {e}")


# This block allows the script to be run directly from the command line
# for quick testing, in addition to being imported as a module.
if __name__ == "__main__":
    test_spotify_auth()
