#!/usr/bin/env python3
"""
Test inicjalizacji bazy danych
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów
sys.path.insert(0, str(Path(__file__).parent))

async def test_database_initialization():
    """Test inicjalizacji bazy danych"""
logger.info("🔍 Test inicjalizacji bazy danych...")
    
    try:
        # Import DatabaseManager
        from core.database_manager import DatabaseManager
logger.info("✅ Import DatabaseManager - OK")
        
        # Utwórz instancję
        db_manager = DatabaseManager()
logger.info("✅ Utworzenie instancji DatabaseManager - OK")
        
        # Test inicjalizacji
        await db_manager.initialize()
logger.info("✅ Inicjalizacja bazy danych - OK")
        
        # Test połączenia
        conn = await db_manager.get_connection()
logger.info("✅ Połączenie z bazą danych - OK")
        
        # Test sprawdzenia tabel
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
logger.info(f"✅ Znalezione tabele: {[table[0] for table in tables]}")
        
        # Zamknij połączenie
        await db_manager.close()
logger.info("✅ Zamknięcie połączenia - OK")
logger.info("\n🎉 Test inicjalizacji bazy danych zakończony pomyślnie!")
        return True
        
    except Exception as e:
        pass
logger.info(f"\n❌ Błąd podczas testu inicjalizacji bazy danych: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Główna funkcja testowa"""
    success = await test_database_initialization()
    return 0 if success else 1

    pass
if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)