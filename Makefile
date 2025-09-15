.PHONY: build playlist playlist-recreate test-auth backup restore import-spotify-playlist lint format

build:
	@echo "--- Building Data Warehouse ---"
	@docker-compose run --rm dwh-manager python main.py build

playlist:
	@echo "--- Creating/Updating Spotify Playlists ---"
	@docker-compose run --rm dwh-manager python main.py playlist

playlist-recreate:
	@echo "--- FORCE RECREATING all Spotify Playlists ---"
	@docker-compose run --rm d-manager python main.py playlist --recreate

test-auth:
	@echo "--- Testing Spotify Authentication ---"
	@docker-compose run --rm dwh-manager python main.py test-auth

backup:
	@echo "--- Backing up Data Warehouse ---"
	@echo "Step 1: Exporting database to CSV files..."
	@docker-compose run --rm dwh-manager python main.py backup
	@echo "\nStep 2: Creating tar.gz archive..."
	@mkdir -p backup
	@tar -czf backup/data_backup_$$(date +%Y%m%d_%H%M%S).tar.gz data/*
	@echo "Backup complete: backup/data_backup_$$(date +%Y%m%d_%H%M%S).tar.gz"

restore:
	@echo "--- Restoring Data from Backup ---"
	@latest_backup=$$(ls -t backup/data_backup_*.tar.gz 2>/dev/null | head -n1); \
	if [ -z "$$latest_backup" ]; then \
		echo "No backup file found in backup/."; exit 1; \
	fi; \
	echo "Restoring from: $$latest_backup"; \
	tar -xzf $$latest_backup -C ./
	@echo "Restore complete. Run 'make build' to rebuild the DWH from the restored CSVs."

import-spotify-playlist:
	@echo "--- Importing Spotify Playlist: $(SpotifyPlaylistURL) ---"
	@docker-compose run --rm dwh-manager python /app/src/import_spotify_playlist.py $(PLAYLIST_URL) --journey-id $(JOURNEY_ID) --granularity $(GRANULARITY)

lint:
	ruff check --fix src/ main.py

format:
	black src/ main.py

