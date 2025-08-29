rebuild-dwh:
	mkdir -p data
	docker-compose up --build

backup-data:
	mkdir -p backup
	tar -czf backup/data_backup_$$(date +%Y%m%d_%H%M%S).tar.gz data/*
restore-data:
	latest_backup=$$(ls -t backup/data_backup_*.tar.gz | head -n1); \
	if [ -z "$$latest_backup" ]; then \
		echo "No backup file found in backup/."; exit 1; \
	fi; \
	tar -xzf $$latest_backup -C data --strip-components=1
