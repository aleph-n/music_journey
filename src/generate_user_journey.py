import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import re
from dotenv import load_dotenv
import logging
import requests
import json
from jinja2 import Template

def update_spotify_urls(markdown, market="MX"):
    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    logging.info(f"Loaded SPOTIFY_CLIENT_ID: {client_id}, SPOTIFY_CLIENT_SECRET: {'set' if client_secret else 'unset'}")
    if not client_id or not client_secret:
        logging.warning("Spotify client credentials not set. Skipping Spotify URL update.")
        return markdown
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    entry_pattern = re.compile(r"\d+\.\s+\*\*Performer:\*\*\s*(.*?)\n\d+\.\s+\*\*Album:\*\*\s*(.*?)\n", re.MULTILINE)
    entries = entry_pattern.findall(markdown)
    for artist, album in entries:
        try:
            results = sp.search(q=f"album:{album} artist:{artist}", type="album", market=market, limit=1)
            items = results.get("albums", {}).get("items", [])
            if items:
                url = items[0]["external_urls"]["spotify"]
                logging.info(f"Regex match: Performer='{artist}', Album='{album}' -> Spotify URL: {url}")
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


def fill_template(template_path, variables):
    with open(template_path, 'r', encoding='utf-8') as f:
        template_str = f.read()
    template = Template(template_str)
    return template.render(**variables)

def prompt_for_variables(template_path, cli_vars=None):
    variables = {} if cli_vars is None else dict(cli_vars)
    return variables

def generate_user_journey(prompt_text, output_path, gemini_api_key):
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent?key=" + gemini_api_key
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    result = response.json()
    markdown = result["candidates"][0]["content"]["parts"][0]["text"]
    markdown = update_spotify_urls(markdown, market="MX")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"Journey markdown saved to {output_path}")
    # Sync markdown to DB and verify
    from sync_journey_md_to_db import upsert_journey_to_db, verify_md_db_match, parse_journey_md
    journey_id = os.path.splitext(os.path.basename(output_path))[0]
    journey_title, steps = parse_journey_md(output_path)
    upsert_journey_to_db(journey_id, journey_title, steps)
    match = verify_md_db_match(journey_id, output_path)
    if match:
        print(f"Journey markdown and database are in sync for {journey_id}.")
    else:
        print(f"WARNING: Journey markdown and database do not match for {journey_id}.")

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
    generate_user_journey(prompt_text, args.output, api_key)
