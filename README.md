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

The data warehouse is built on a star schema, which separates the descriptive data (Dimensions) from the journey steps (Facts).

* **Dimensions:** DimMusicalWork, DimPerformer, DimRecording, DimJourney, DimPlaylist  
* **Fact Table:** FactJourneyStep