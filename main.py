"""
Entrypoint for the music data warehouse ETL pipeline.
"""

from src.build_dwh import build_data_warehouse

if __name__ == "__main__":
    build_data_warehouse()
