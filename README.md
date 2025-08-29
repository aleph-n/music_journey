# Music Data Warehouse Project

## Setup
1. Copy `config-template.env` to `config.env` and adjust paths as needed.
2. Install requirements: `pip install -r requirements.txt`
3. Use Docker or run `main.py` directly.

## Makefile Commands
- `make rebuild-dwh` — Rebuild the DWH using Docker Compose
- `make backup-data` — Create a tar.gz backup of the `data/` directory in the backup directory
- `make restore-data` — Restore the latest backup to the `data/` directory

## Configuration
- Edit `config.env` to set the backup directory (default: `backup/`).
- `config.env` is ignored by git; use `config-template.env` for sharing config structure.

## Data
- Place your CSVs in the `data/` directory.
- Backups are stored as tar.gz files in the backup directory.

## Docker
- Build and run with `docker-compose up --build`

---

**Note:** Do not commit sensitive or large data files to the repository. Use the backup and restore commands for data management.
