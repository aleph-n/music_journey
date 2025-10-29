import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
def update_spotify_urls(markdown, market="MX"): 
    import re
    from dotenv import load_dotenv
    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    logging.info(f"Loaded SPOTIFY_CLIENT_ID: {client_id}, SPOTIFY_CLIENT_SECRET: {'set' if client_secret else 'unset'}")
    if not client_id or not client_secret:
        logging.warning("Spotify client credentials not set. Skipping Spotify URL update.")
        return markdown
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    # Find all album/track entries in markdown (numbered, formatted)
    entry_pattern = re.compile(r"\d+\.\s+\*\*Performer:\*\*\s*(.*?)\n\d+\.\s+\*\*Album:\*\*\s*(.*?)\n", re.MULTILINE)
    entries = entry_pattern.findall(markdown)
    for artist, album in entries:
        try:
            results = sp.search(q=f"album:{album} artist:{artist}", type="album", market=market, limit=1)
            items = results.get("albums", {}).get("items", [])
            if items:
                url = items[0]["external_urls"]["spotify"]
                logging.info(f"Regex match: Performer='{artist}', Album='{album}' -> Spotify URL: {url}")
                # Replace all Spotify URL lines for this album/artist
                block_pattern = re.compile(
                    rf"(\d+\.\s+\*\*Performer:\*\*\s*{re.escape(artist)}\n\d+\.\s+\*\*Album:\*\*\s*{re.escape(album)}.*?)(Spotify URL:.*?\n|Spotify URL:.*?$|$)",
                    re.DOTALL)
                def block_replacer(match):
                    block = match.group(1)
                    logging.info(f"Updating block for Performer='{artist}', Album='{album}' with Spotify URL: {url}")
                    return f"{block}Spotify URL: {url}\n"
                markdown = block_pattern.sub(block_replacer, markdown)
        except Exception as e:
            logging.warning(f"Spotify search failed for {artist} - {album}: {e}")
    return markdown
"""
Automate Gemini API interaction to generate a listening journey markdown file.
"""

import os
import requests
import json
from dotenv import load_dotenv
import logging
from jinja2 import Template

def fill_template(template_path, variables):
    with open(template_path, 'r', encoding='utf-8') as f:
        template_str = f.read()
    template = Template(template_str)
    return template.render(**variables)

def prompt_for_variables(template_path, cli_vars=None):
    # With Jinja2, just use CLI variables directly
    variables = {} if cli_vars is None else dict(cli_vars)
    # Optionally, prompt for missing variables if desired
    return variables

def generate_journey_with_gemini(prompt_text, output_path, gemini_api_key):
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent?key=" + gemini_api_key
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    result = response.json()
    markdown = result["candidates"][0]["content"]["parts"][0]["text"]
    # Update Spotify URLs for Mexico market
    markdown = update_spotify_urls(markdown, market="MX")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"Journey markdown saved to {output_path}")

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate listening journey markdown using Gemini API.")
    parser.add_argument("--template", required=True, help="Path to prompt template markdown file")
    parser.add_argument("--output", required=True, help="Path to output markdown file")
    parser.add_argument("--api-key", required=False, help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--artist", required=False, help="Artist, Genre, or Instrument")
    parser.add_argument("--granularity", required=False, help="Album/Track granularity")
    parser.add_argument("--theme", required=False, help="Central theme")
    parser.add_argument("--emotions", required=False, help="Emotions to pursue")
    parser.add_argument("--sound", required=False, help="Desired sound")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key must be provided via --api-key or GEMINI_API_KEY env var.")

    cli_vars = {
        "artist": args.artist,
        "granularity": args.granularity,
        "theme": args.theme,
        "emotions": args.emotions,
        "sound": args.sound,
    }
    logging.info(f"CLI variables: {cli_vars}")
    variables = prompt_for_variables(args.template, cli_vars)
    logging.info(f"Filled variables: {variables}")
    prompt_text = fill_template(args.template, variables)
    logging.info("Final prompt text sent to Gemini:")
    logging.info(prompt_text)
    generate_journey_with_gemini(prompt_text, args.output, api_key)
