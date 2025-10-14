"""
Database Manager - Wrapper dla kompatybilności

Zapewnia bezpieczny import DatabaseManager z app.database.
Jeśli import się nie powiedzie (np. z powodu korupcji pliku), podstawia lekki stub,
aby nie blokować importu rdzenia aplikacji.
"""

from pathlib import Path
from typing import Union

try:
    from app.database import DatabaseManager as _AppDatabaseManager  # prefer real implementation

    class DatabaseManager(_AppDatabaseManager):  # type: ignore[misc]
        def __init__(self, db_path: Union[str, Path] = "data/database.db"):
            super().__init__(db_path)

except Exception:
    class DatabaseManager:  # fallback stub
        def __init__(self, db_path: Union[str, Path] = "data/database.db"):
            self.db_path = str(db_path)

        async def initialize(self):
            return None

        async def close(self):
            return None

        # Minimal API used w innych modułach – dodaj w razie potrzeby:
        async def add_log(self, **kwargs):
            return None

__all__ = ['DatabaseManager']
