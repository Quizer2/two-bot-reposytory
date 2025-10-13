"""
Database Manager - Wrapper dla kompatybilności

Zapewnia bezpieczny import DatabaseManager z app.database.
Jeśli import się nie powiedzie (np. z powodu korupcji pliku), podstawia lekki stub,
aby nie blokować importu rdzenia aplikacji.
"""

try:
    from app.database import DatabaseManager  # prefer real implementation
except Exception:
    class DatabaseManager:  # fallback stub
        def __init__(self, db_path: str = "data/database.db"):
            self.db_path = db_path
        async def initialize(self):
            return None
        async def close(self):
            return None
        # Minimal API used w innych modułach – dodaj w razie potrzeby:
        async def add_log(self, **kwargs):
            return None

__all__ = ['DatabaseManager']
