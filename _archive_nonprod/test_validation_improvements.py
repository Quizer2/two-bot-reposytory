#!/usr/bin/env python3
"""
Test nowych funkcji walidacji i obsługi błędów
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.data_manager import DataManager, ValidationHelper, DatabaseTransactionHelper
import logging
logger = logging.getLogger(__name__)

async def test_validation_helper():
    """Test ValidationHelper"""
logger.info("🧪 Testowanie ValidationHelper...")
    
    try:
        # Test walidacji limit
        assert ValidationHelper.validate_limit(50) == 50
        assert ValidationHelper.validate_limit(2000) == 1000  # max limit
logger.info("✅ Walidacja limit działa")
        
        # Test walidacji severity
        assert ValidationHelper.validate_severity("info") == "info"
        assert ValidationHelper.validate_severity("CRITICAL") == "critical"
logger.info("✅ Walidacja severity działa")
        
        # Test walidacji alert_type
        assert ValidationHelper.validate_alert_type("SYSTEM") == "SYSTEM"
        assert ValidationHelper.validate_alert_type("bot") == "BOT"
logger.info("✅ Walidacja alert_type działa")
        
        # Test błędnych wartości
        try:
            ValidationHelper.validate_limit(-5)
            assert False, "Powinien rzucić błąd"
        except ValueError:
            pass
logger.info("✅ Walidacja limit odrzuca nieprawidłowe wartości")
        
            pass
        try:
            ValidationHelper.validate_severity("invalid")
            assert False, "Powinien rzucić błąd"
        except ValueError:
logger.info("✅ Walidacja severity odrzuca nieprawidłowe wartości")
        pass
            
    except Exception as e:
logger.info(f"❌ Błąd w testach ValidationHelper: {e}")
        return False
    
    return True

async def test_database_transaction_helper():
    """Test DatabaseTransactionHelper"""
        pass
logger.info("\n🧪 Testowanie DatabaseTransactionHelper...")
    
    try:
        # Utwórz tymczasową bazę danych
        test_db_path = "test_transaction.db"
        db_helper = DatabaseTransactionHelper(test_db_path)
        
        # Test prostej transakcji
        def create_test_table(cursor, conn):
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            ''')
        
        def insert_test_data(cursor, conn):
            cursor.execute('INSERT INTO test_table (name) VALUES (?)', ('test_name',))
        
            pass
        # Wykonaj transakcję
            pass
        success = db_helper.execute_transaction([create_test_table, insert_test_data])
        
        if success:
logger.info("✅ Transakcja wykonana pomyślnie")
        else:
logger.info("❌ Transakcja nieudana")
            return False
        
            pass
        # Test retry logic
            pass
        def failing_operation(cursor, conn):
            raise Exception("Test error")
        
        success = db_helper.execute_with_retry(failing_operation, max_retries=2)
            pass
        if not success:
logger.info("✅ Retry logic działa poprawnie (operacja nieudana jak oczekiwano)")
        else:
logger.info("❌ Retry logic nie działa poprawnie")
            return False
        
        # Usuń testową bazę danych
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
    except Exception as e:
logger.info(f"❌ Błąd w testach DatabaseTransactionHelper: {e}")
        return False
    
    return True

async def test_data_manager_improvements():
    """Test ulepszeń w DataManager"""
logger.info("\n🧪 Testowanie ulepszeń DataManager...")
    
    try:
        # Utwórz DataManager z testową bazą danych
        test_db_path = "test_datamanager.db"
        dm = DataManager(test_db_path)
        
        # Test dodawania alertu z walidacją
        await dm.add_alert(
            title="Test Alert",
            message="Test message",
            severity="warning",
            alert_type="SYSTEM"
        )
logger.info("✅ Dodawanie alertu z walidacją działa")
        
        # Test pobierania alertów z walidacją
            pass
        alerts = await dm.get_alerts(limit=10)
            pass
        if alerts:
logger.info(f"✅ Pobieranie alertów działa ({len(alerts)} alertów)")
        else:
            pass
logger.info("⚠️ Brak alertów (może być OK)")
        
        # Test pobierania logów z walidacją
            pass
        logs = await dm.get_logs(limit=5)
        if logs:
logger.info(f"✅ Pobieranie logów działa ({len(logs)} logów)")
            pass
        else:
logger.info("⚠️ Brak logów (może być OK)")
        pass
        
        # Test błędnych parametrów
        try:
            await dm.get_alerts(limit=-5)
logger.info("❌ Walidacja limit nie działa")
            return False
        except ValueError:
logger.info("✅ Walidacja parametrów w get_alerts działa")
        
        # Usuń testową bazę danych
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
    except Exception as e:
logger.info(f"❌ Błąd w testach DataManager: {e}")
        return False
    
    return True

async def main():
    """Główna funkcja testowa"""
        pass
logger.info("🚀 Rozpoczynam testy walidacji i obsługi błędów...\n")
    
        pass
    tests = [
            pass
                pass
        test_validation_helper(),
        test_database_transaction_helper(),
        test_data_manager_improvements()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    passed = sum(1 for result in results if result is True)
    total = len(results)
logger.info(f"\n📊 Wyniki testów: {passed}/{total} testów przeszło pomyślnie")
    
    if passed == total:
logger.info("🎉 Wszystkie testy przeszły pomyślnie!")
logger.info("✅ Walidacja i obsługa błędów działają poprawnie")
    else:
logger.info("⚠️ Niektóre testy nie przeszły")
        for i, result in enumerate(results):
            if result is not True:
logger.info(f"❌ Test {i+1}: {result}")

if __name__ == "__main__":
    asyncio.run(main())