import sqlite3
import os
import requests
from jinja2 import Template

def extract_journey_steps(journey_id, granularity="Album"):
    db_path = os.path.join("output", "music_journeys.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if granularity == "Album":
        query = """
        SELECT
            fs.StepOrder,
            da.AlbumTitle,
            dp.PerformerName,
            da.RecordingLabel,
            da.SpotifyReleaseDate,
            da.SpotifyURL
        FROM FactJourneyStep fs
        JOIN DimAlbum da ON fs.AlbumID = da.AlbumID
        JOIN DimPerformer dp ON da.PerformerID = dp.PerformerID
        WHERE fs.JourneyID = ?
        ORDER BY fs.StepOrder
        """
    else:
        query = """
        SELECT
            fs.StepOrder,
            dr.SpotifyTitle,
            dp.PerformerName,
            da.RecordingLabel,
            da.SpotifyReleaseDate,
            dr.SpotifyURL
        FROM FactJourneyStep fs
        JOIN DimRecording dr ON fs.RecordingID = dr.RecordingID
        JOIN DimAlbum da ON dr.AlbumID = da.AlbumID
        JOIN DimPerformer dp ON dr.PerformerID = dp.PerformerID
        WHERE fs.JourneyID = ?
        ORDER BY fs.StepOrder
        """
    cursor.execute(query, (journey_id,))
    steps = []
    for row in cursor.fetchall():
        steps.append({
            "step_order": row[0],
            "album": row[1],
            "performer": row[2],
            "label": row[3],
            "release_date": row[4],
            "spotify_url": row[5],
            "apple_music_url": "",
        })
    conn.close()
    return steps

def prepare_gemini_prompt(template_path, journey_steps):
    with open(template_path, 'r', encoding='utf-8') as f:
        template_str = f.read()
    template = Template(template_str)
    playlist_md = ""
    for step in journey_steps:
        playlist_md += (
            f"* **Concerto:** {step['album']}\n"
            f"* **Performer:** {step['performer']}\n"
            f"* **Album:** {step['album']}\n"
            f"* **Label:** {step['label']}\n"
            f"* **Release Date:** {step['release_date']}\n"
            f"* **Spotify:** {step['spotify_url']}\n"
            f"* **Apple Music:** {step['apple_music_url']}\n"
        )
    prompt = template.render(playlist=playlist_md)
    return prompt

def send_to_gemini(prompt_text):
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    markdown = result["candidates"][0]["content"]["parts"][0]["text"]
    return markdown

def save_markdown(journey_id, markdown):
    output_path = f"journeys/{journey_id}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"Journey markdown saved to {output_path}")

def generate_dwh_journey(journey_id, granularity="Album", template_path="journeys/joruney_import_prompt.md"):
    steps = extract_journey_steps(journey_id, granularity)
    # Fetch JourneyName from DimJourney
    db_path = os.path.join("output", "music_journeys.db")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT JourneyName FROM DimJourney WHERE JourneyID = ?", (journey_id,))
        result = cursor.fetchone()
        journey_name = result[0] if result else journey_id
    prompt = prepare_gemini_prompt(template_path, steps)
    markdown = send_to_gemini(prompt)
    # Prepend markdown with title
    markdown = f"# {journey_name}\n\n" + markdown
    save_markdown(journey_id, markdown)
    # Sync markdown to DB and verify
    from src.sync_journey_md_to_db import upsert_journey_to_db, verify_md_db_match, parse_journey_md
    md_path = f"journeys/{journey_id}.md"
    journey_title, steps = parse_journey_md(md_path)
    upsert_journey_to_db(journey_id, journey_title, steps)
    match = verify_md_db_match(journey_id, md_path)
    if match:
        print(f"Journey markdown and database are in sync for {journey_id}.")
    else:
        print(f"WARNING: Journey markdown and database do not match for {journey_id}.")
