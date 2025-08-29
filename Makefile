rebuild-dwh:
	mkdir -p data
	docker-compose up --build

backup-data:
	. ./config.env; \
	mkdir -p $$backup_dir; \
	tar -czf $$backup_dir/data_backup_$$(date +%Y%m%d_%H%M%S).tar.gz data/*
restore-data:
	. ./config.env; \
	latest_backup=$$(ls -t $$backup_dir/data_backup_*.tar.gz | head -n1); \
	if [ -z "$$latest_backup" ]; then \
		echo "No backup file found in $$backup_dir."; exit 1; \
	fi; \
	tar -xzf $$latest_backup -C data --strip-components=1
