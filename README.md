
# **The Natural Language Music Journey Engine**

## Gemini AI Integration & Automated Journey Generation

This project now integrates Gemini AI to automatically generate rich, narrative-driven music journey markdown files from either natural language prompts or imported Spotify playlists. The generated markdown is parsed and upserted into the local data warehouse, ensuring all journey metadata and steps are always in sync.

### Key Features Added
- **Gemini AI Markdown Generation:** Use Gemini to create immersive journey essays and playlist metadata from prompts or playlist imports.
- **Automated Database Upserts:** After markdown generation, journey metadata and steps are parsed and upserted into the SQLite data warehouse.
- **Validation & Sync:** The system verifies that the markdown and database are consistent after each import or generation.
- **Flexible CLI & Makefile:** Easily run imports, generate journeys, and sync data using simple commands.

### How It Works
1. **Import a Spotify Playlist:**
  - Use `make import-spotify-playlist PLAYLIST_URL=<url> JOURNEY_ID=<id> GRANULARITY=<Track|Album>`
  - The playlist is imported, and a journey markdown file is generated using Gemini AI.
2. **Generate Journey from Prompt:**
  - Use `make generate-gemini-journey` with your desired variables and prompt template.
  - Gemini creates a markdown journey, which is then parsed and upserted into the database.
3. **Database Sync:**
  - All journey steps and metadata are automatically upserted into the database, ensuring no duplicates and full consistency.
4. **Validation:**
  - After each operation, the system checks that the markdown and database match.

### Example Workflow
```sh
make import-spotify-playlist PLAYLIST_URL=https://open.spotify.com/playlist/4D7yVkvNm1UwbpFbLfDw5k JOURNEY_ID=la_extraterrestre_01 GRANULARITY=Album
```
This will:
- Import the playlist
- Generate a Gemini-powered journey markdown file
- Upsert all journey data into the database
- Validate the sync between markdown and database

### Requirements
- Python 3.9+
- Docker
- Gemini API key (add to `.env`)
- Spotify API credentials (add to `.env`)

### Main CLI Commands
- `make build` — Build the data warehouse from CSVs
- `make import-spotify-playlist` — Import a playlist and generate a journey
- `make generate-gemini-journey` — Generate a journey from a prompt
- `make playlist` — Sync journeys to Spotify
- `make backup` / `make restore` — Backup/restore the database

### Advanced
- Markdown templates for Gemini prompts are in `journeys/`
- All code for Gemini integration is in `src/generate_dwh_journey.py`, `src/generate_user_journey.py`, and `src/sync_journey_md_to_db.py`

---

This project is a sophisticated ETL pipeline and automation tool designed to create deeply personal, emotionally resonant music playlists. It uses a local data warehouse to store curated musical "journeys" and leverages the Spotify API to generate and manage these playlists programmatically.

The long-term vision is to evolve this tool into a personalized wellness and discovery engine that can generate new journeys from natural language prompts using AI.

## **Features**

* **Curated Data Warehouse:** Builds a local SQLite database from simple CSV files, structuring music with deep, subjective emotional tags.  
* **Stateful Spotify Playlist Management:** Intelligently creates and updates Spotify playlists. It remembers the playlists it creates and will update them with new changes rather than creating duplicates.  
* **Portable & Reproducible:** The entire environment is containerized with Docker, ensuring the project runs identically on any machine.  
* **Command-Line Interface:** A simple, powerful CLI (via main.py and a Makefile) provides easy access to all core functions like building the database and creating playlists.  
* **Secure Credential Management:** Uses a .env file to keep API keys and other secrets safe and out of the codebase.

## **Setup**

1. **Install Docker:** Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running on your system.  
2. **Clone the Repository:**  
   git clone \[https://github.com/YOUR\_USERNAME/YOUR\_REPOSITORY\_NAME.git\](https://github.com/YOUR\_USERNAME/YOUR\_REPOSITORY\_NAME.git)  
   cd YOUR\_REPOSITORY\_NAME

3. **Configure Environment Variables:**  
   * Copy the template file: cp env-template .env  
   * Edit the .env file and add your Spotify API credentials. You can get these from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).  
4. **Add Your Data:** Place your curated CSV files inside the data/ directory.

## **Usage**

This project uses a Makefile to provide simple, memorable commands for all common operations.

* **Build the Data Warehouse:**  
  * This command reads your CSVs and builds the music\_journeys.db file in the output/ directory.  
  *   make build

* **Create or Update Spotify Playlists:**  
  * This command queries your DWH and syncs all defined journeys with your Spotify account.  
  *   make playlist

* **Import a Specific Spotify Playlist:**  
  * This command imports an existing Spotify playlist into the system, creating a new journey from it.  
  *   make import-spotify-playlist PLAYLIST\_URL=<url> JOURNEY\_ID=<id> GRANULARITY=<Track|Album>
  *   Example: make import-spotify-playlist PLAYLIST\_URL=https://open.spotify.com/playlist/4D7yVkvNm1UwbpFbLfDw5k JOURNEY\_ID=la\_extraterrestre\_01 GRANULARITY=Album

* **Test Spotify Authentication:**  
  * Use this command to quickly check if your API credentials are working.  
  *   make test-auth

* **Backup/Restore:**
  - `make backup`
  - `make restore`

* **Lint & Format:**
  - `make lint` (auto-fixes with ruff)
  - `make format` (auto-formats with black)

### CLI Entrypoint

You can also run the import directly:

```sh
python src/import_spotify_playlist.py <playlist_url> --journey-id <id> --granularity <Track|Album>
```

### Linting & Formatting

- All Python code is checked and auto-fixed with `ruff` and formatted with `black`.
- Run `make lint` and `make format` to ensure code quality before committing.

### Playlist Import Validation

- To validate a playlist import, use the Makefile rule with the correct parameters.
- Example:
  - Playlist: "La extraterrestre"
  - JourneyID: `la_extraterrestre_01`
  - Granularity: `Album`
  - Spotify URL: `https://open.spotify.com/playlist/4D7yVkvNm1UwbpFbLfDw5k?si=2426e57ae5324ecb`
- After import, verify the database contents using SQLite queries:

```sh
sqlite3 output/music_journeys.db 'SELECT JourneyID, StepOrder, AlbumID FROM FactJourneyStep WHERE JourneyID="la_extraterrestre_01" ORDER BY StepOrder;'
```

This will show the imported steps and confirm the workflow is working as intended.

## **Project Roadmap**

This project is planned in three major phases:

1. **Phase 1: Foundation & Curation (Current):** Perfecting the local workflow for curating and managing the musical journey data.  
2. **Phase 2: Intelligence & Automation:** Integrating the Gemini API to enable the creation of journeys from natural language prompts.  
3. **Phase 3: Cloud Deployment & User Application:** Moving the system to a scalable cloud platform (GCP) and building a simple web interface for user interaction.

## **Data Schema**

The data warehouse uses a star schema to support both classical and non-classical music journeys. This model is designed for flexibility, clarity, and scalability, allowing you to curate playlists that span genres and formats.

### **Why This Data Model?**
Music journeys can be highly diverse: classical journeys often involve works, movements, and recordings, while non-classical journeys may focus on albums and tracks. Our schema supports both by:
- Separating descriptive data (dimensions) from journey steps (facts)
- Allowing tracks, movements, or entire albums to be sequenced in any journey
- Supporting many-to-many relationships via bridge tables

### **Table Roles and Importance**

**DimMusicalWork**: Describes classical works (e.g., symphonies, concertos). Essential for journeys that reference classical compositions and their structure.

**DimMovement**: Details individual movements within classical works. Used for fine-grained classical journeys, but not needed for pop/rock/album-based journeys.

**DimPerformer**: Stores performer metadata. Important for classical recordings and useful for any genre where performer context matters.

**DimAlbum**: Represents albums for all genres. Central for non-classical journeys and also links classical recordings to their album releases.

**DimRecording**: Generalizes the concept of a track or recording. For classical, it links to movements and works; for non-classical, it simply represents a track on an album. This flexibility allows the same table to serve both genres.

**BridgeAlbumMovement**: Connects albums, movements, and recordings. Critical for classical journeys to map recordings to specific movements. For non-classical, this table is optional or unused.

**DimJourney**: Defines each curated journey (playlist), regardless of genre. Contains metadata and descriptive context.

**FactJourneyStep**: Sequences the steps in a journey. Each step can reference a recording (track), movement, or album, allowing for flexible playlist construction. This is the heart of the journey logic.

**DimPlaylist**: Tracks the state of generated playlists on external services (e.g., Spotify). Ensures updates and avoids duplication.

### **Classical vs. Non-Classical Workflows**
- **Classical:** Use DimMusicalWork, DimMovement, DimRecording, BridgeAlbumMovement, and FactJourneyStep to build journeys from works and movements.
- **Non-Classical:** Use DimAlbum, DimRecording, and FactJourneyStep to build journeys from albums and tracks. Movements and bridge tables are not required.

This model ensures you can curate any type of musical journey, from a symphony’s movements to a band’s discography, with clear relationships and extensibility.