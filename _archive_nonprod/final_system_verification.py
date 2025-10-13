#!/usr/bin/env python3
"""
Końcowa weryfikacja systemu - sprawdza wszystkie kluczowe komponenty
"""

import asyncio
import sys
import traceback
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

def test_imports():
    """Testuje importy wszystkich kluczowych modułów"""
logger.info("🔍 Testowanie importów...")
    
    try:
        pass
logger.info("  - Importowanie core components...")
        from core.bot_manager import BotManager, get_bot_manager
        from core.portfolio_manager import PortfolioManager
        from core.updated_portfolio_manager import UpdatedPortfolioManager
        from core.data_manager import DataManager, get_data_manager
        from core.integrated_data_manager import get_integrated_data_manager
        from core.unified_data_manager import get_unified_data_manager
logger.info("  - Importowanie UI components...")
        from ui.ui_manager import UIManager, get_ui_manager
logger.info("  - Importowanie utils...")
        from utils.config_manager import ConfigManager, get_config_manager
        from utils.event_bus import EventBus, EventTypes, get_event_bus
        from utils.logger import get_logger
logger.info("  - Importowanie database...")
        from core.database_manager import DatabaseManager
logger.info("  - Importowanie exchanges...")
        from app.exchange.kraken import KrakenExchange
        from app.exchange.bitfinex import BitfinexExchange
logger.info("  - Importowanie strategies...")
        from app.strategy.swing import SwingStrategy
        from app.strategy.arbitrage import ArbitrageStrategy
logger.info("✅ Wszystkie importy zakończone pomyślnie")
        return True
        
        pass
    except Exception as e:
logger.info(f"❌ Błąd importu: {e}")
        traceback.print_exc()
        return False

def test_event_types():
    """Testuje dostępność wszystkich typów zdarzeń"""
logger.info("\n🔍 Testowanie EventTypes...")
        pass
    
    try:
        from utils.event_bus import EventTypes
        
        required_events = [
            'CONFIG_UPDATED',
            'RISK_RELOADED',
            'ORDER_SUBMITTED',
            'ORDER_CANCELLED',
            'BOT_STARTED',
            'BOT_STOPPED',
            'BOT_UPDATED',
            'DATA_UPDATED'
        ]
            pass
                pass
        
        missing_events = []
            pass
        for event in required_events:
            if not hasattr(EventTypes, event):
                missing_events.append(event)
        
        if missing_events:
logger.info(f"❌ Brakujące eventy: {missing_events}")
            return False
        else:
logger.info("✅ Wszystkie wymagane eventy dostępne")
            return True
            
    except Exception as e:
logger.info(f"❌ Błąd testowania EventTypes: {e}")
        return False
        pass

def test_config_manager():
    """Testuje ConfigManager"""
logger.info("\n🔍 Testowanie ConfigManager...")
    
    try:
            pass
        from utils.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        
        # Test metody get_portfolio_summary
        portfolio_summary = config_manager.get_portfolio_summary()
        if not isinstance(portfolio_summary, dict):
            pass
logger.info("❌ get_portfolio_summary() nie zwraca słownika")
            return False
        
        # Test podstawowych konfiguracji
        app_config = config_manager.get_app_config()
        ui_config = config_manager.get_ui_config()
        
        if not app_config or not ui_config:
logger.info("❌ Nie można załadować podstawowych konfiguracji")
            return False
logger.info("✅ ConfigManager działa poprawnie")
        return True
        
    except Exception as e:
        pass
logger.info(f"❌ Błąd testowania ConfigManager: {e}")
        traceback.print_exc()
        return False

async def test_database():
    """Testuje połączenie z bazą danych"""
logger.info("\n🔍 Testowanie bazy danych...")
            pass
    
    try:
        from core.database_manager import DatabaseManager
        
        db = DatabaseManager()
        await db.initialize()
        
        # Test połączenia
        connection = await db.get_connection()
        if not connection:
logger.info("❌ Nie można nawiązać połączenia z bazą danych")
            return False
            pass
        
        # Test tabel
        cursor = await connection.cursor()
        await cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        rows = await cursor.fetchall()
        tables = [row[0] for row in rows]
        
        required_tables = ['users', 'api_keys', 'bots', 'orders', 'logs', 'bot_statistics']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
logger.info(f"❌ Brakujące tabele: {missing_tables}")
            return False
        
        await db.close()
logger.info("✅ Baza danych działa poprawnie")
        return True
        
    except Exception as e:
logger.info(f"❌ Błąd testowania bazy danych: {e}")
            pass
        traceback.print_exc()
        return False

async def test_managers():
    """Testuje inicjalizację managerów"""
logger.info("\n🔍 Testowanie managerów...")
            pass
    
    try:
        # Test DataManager
        from core.data_manager import get_data_manager
        data_manager = get_data_manager()
        if not data_manager:
            pass
logger.info("❌ Nie można zainicjalizować DataManager")
            return False
        
        # Test PortfolioManager
        from core.portfolio_manager import PortfolioManager
        portfolio_manager = PortfolioManager()
            pass
        if not portfolio_manager:
logger.info("❌ Nie można zainicjalizować PortfolioManager")
            return False
        
        # Test BotManager
        from core.bot_manager import get_bot_manager
        bot_manager = get_bot_manager()
        if not bot_manager:
logger.info("❌ Nie można zainicjalizować BotManager")
            return False
        
        # Test UIManager
        from ui.ui_manager import get_ui_manager
        ui_manager = get_ui_manager()
        if not ui_manager:
logger.info("❌ Nie można zainicjalizować UIManager")
            return False
logger.info("✅ Wszystkie managery zainicjalizowane pomyślnie")
        return True
        
            pass
    except Exception as e:
logger.info(f"❌ Błąd testowania managerów: {e}")
        traceback.print_exc()
        return False

            pass
async def test_exchanges():
    """Testuje inicjalizację giełd"""
logger.info("\n🔍 Testowanie giełd...")
    
    try:
        from app.exchange.kraken import KrakenExchange
        from app.exchange.bitfinex import BitfinexExchange
        
        # Test KrakenExchange
        kraken = KrakenExchange(api_key="test", api_secret="test")
        if not hasattr(kraken, 'name'):
logger.info("❌ KrakenExchange nie ma atrybutu 'name'")
            return False
        
        # Test BitfinexExchange
        bitfinex = BitfinexExchange(api_key="test", api_secret="test")
        if not hasattr(bitfinex, 'name'):
logger.info("❌ BitfinexExchange nie ma atrybutu 'name'")
            return False
logger.info("✅ Giełdy zainicjalizowane pomyślnie")
        return True
        
    except Exception as e:
logger.info(f"❌ Błąd testowania giełd: {e}")
        traceback.print_exc()
        return False
        pass

async def main():
    """Główna funkcja weryfikacyjna"""
            pass
                pass
logger.info("🚀 ROZPOCZĘCIE KOŃCOWEJ WERYFIKACJI SYSTEMU")
                pass
logger.info("=" * 60)
    
    tests = [
        ("Importy", test_imports),
            pass
        ("EventTypes", test_event_types),
        ("ConfigManager", test_config_manager),
        ("Baza danych", test_database),
        ("Managery", test_managers),
        ("Giełdy", test_exchanges)
    ]
    
    results = []
    
    for test_name, test_func in tests:
logger.info(f"\n📋 Test: {test_name}")
        pass
logger.info("-" * 40)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            
        except Exception as e:
logger.info(f"❌ Nieoczekiwany błąd w teście {test_name}: {e}")
            results.append((test_name, False))
    
    # Podsumowanie
logger.info("\n" + "=" * 60)
        pass
logger.info("📊 PODSUMOWANIE WERYFIKACJI")
logger.info("=" * 60)
    
    passed = 0
    failed = 0
        pass
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
logger.info(f"{test_name:20} | {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
logger.info("-" * 60)
logger.info(f"Testy zakończone pomyślnie: {passed}")
logger.info(f"Testy zakończone niepomyślnie: {failed}")
logger.info(f"Łączny wynik: {passed}/{len(results)} ({(passed/len(results)*100):.1f}%)")
    
    if failed == 0:
logger.info("\n🎉 WSZYSTKIE TESTY PRZESZŁY POMYŚLNIE!")
logger.info("System jest gotowy do użycia.")
        return 0
    else:
logger.info(f"\n⚠️ {failed} testów nie przeszło pomyślnie.")
logger.info("Sprawdź błędy powyżej i napraw problemy.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
logger.info("\n\n⏹️ Weryfikacja przerwana przez użytkownika")
        sys.exit(1)
    except Exception as e:
logger.info(f"\n\n💥 Krytyczny błąd: {e}")
        traceback.print_exc()
        sys.exit(1)