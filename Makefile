# Makefile for Music DWH Project

.PHONY: build playlist test-auth backup restore

# Default target
all: build playlist

# Build the data warehouse
build:
	@echo "--- Building Data Warehouse ---"
	docker-compose run --rm dwh-manager python main.py build

# Create or update Spotify playlists
playlist:
	@echo "--- Creating/Updating Spotify Playlists ---"
	docker-compose run --rm dwh-manager python main.py playlist

# Test Spotify Authentication
test-auth:
	@echo "--- Testing Spotify Authentication ---"
	docker-compose run --rm dwh-manager python main.py test-auth

# Backup data directory
backup:
	@echo "--- Backing up data ---"
	mkdir -p backup
	tar -czf backup/data_backup_$$(date +%Y%m%d_%H%M%S).tar.gz data/*
	@echo "Backup created in backup/ folder."

# Restore latest data backup
restore:
	@echo "--- Restoring latest data backup ---"
	latest_backup=$$(ls -t backup/data_backup_*.tar.gz | head -n1); \
	if [ -z "$$latest_backup" ]; then \
		echo "No backup file found in backup/."; exit 1; \
	fi; \
	tar -xzf $$latest_backup -C .
	@echo "Data restored from $$latest_backup."
