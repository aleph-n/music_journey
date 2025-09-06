# **The Natural Language Music Journey Engine**

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

* **Test Spotify Authentication:**  
  * Use this command to quickly check if your API credentials are working.  
  *   make test-auth

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