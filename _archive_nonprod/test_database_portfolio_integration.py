#!/usr/bin/env python3
"""
Test integracji bazy danych z PortfolioManager
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów
sys.path.insert(0, str(Path(__file__).parent))

async def test_database_portfolio_integration():
    """Test integracji bazy danych z PortfolioManager"""
logger.info("🔍 Test integracji bazy danych z PortfolioManager...")
    
    try:
        # 1. Test DatabaseManager
logger.info("\n1️⃣ Test DatabaseManager...")
        from core.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.initialize()
logger.info("✅ DatabaseManager zainicjalizowany")
        
        # 2. Test DataManager
logger.info("\n2️⃣ Test DataManager...")
        try:
            from core.data_manager import DataManager, get_data_manager
            data_manager = get_data_manager()
logger.info("✅ DataManager dostępny")
        except Exception as e:
            pass
logger.info(f"⚠️ DataManager problem: {e}")
            data_manager = None
        
        # 3. Test PortfolioManager
logger.info("\n3️⃣ Test PortfolioManager...")
            pass
        try:
            from core.portfolio_manager import PortfolioManager
            portfolio_manager = PortfolioManager(data_manager=data_manager)
logger.info("✅ PortfolioManager utworzony")
            
                pass
            # Test metod
                pass
            if hasattr(portfolio_manager, 'get_portfolio_summary'):
logger.info("✅ get_portfolio_summary dostępne")
            else:
logger.info("❌ get_portfolio_summary niedostępne")
                
        except Exception as e:
logger.info(f"❌ PortfolioManager błąd: {e}")
            portfolio_manager = None
            pass
        
        # 4. Test UpdatedPortfolioManager
logger.info("\n4️⃣ Test UpdatedPortfolioManager...")
        try:
            from core.updated_portfolio_manager import UpdatedPortfolioManager
                pass
            updated_portfolio_manager = UpdatedPortfolioManager(data_manager=data_manager)
                pass
logger.info("✅ UpdatedPortfolioManager utworzony")
            
            # Test metod
            if hasattr(updated_portfolio_manager, 'get_enhanced_portfolio_summary'):
logger.info("✅ get_enhanced_portfolio_summary dostępne")
            else:
logger.info("❌ get_enhanced_portfolio_summary niedostępne")
                
            pass
                pass
        except Exception as e:
                    pass
logger.info(f"❌ UpdatedPortfolioManager błąd: {e}")
            updated_portfolio_manager = None
        
                        pass
        # 5. Test integracji z bazą danych
                        pass
logger.info("\n5️⃣ Test integracji z bazą danych...")
        if portfolio_manager and db_manager:
                    pass
            try:
                # Sprawdź czy PortfolioManager może używać bazy danych
                if hasattr(portfolio_manager, 'data_manager') and portfolio_manager.data_manager:
logger.info("✅ PortfolioManager ma data_manager")
                    
                    # Sprawdź czy data_manager ma połączenie z bazą
                    if hasattr(portfolio_manager.data_manager, 'db_helper'):
            pass
                pass
logger.info("✅ DataManager ma db_helper")
                    else:
logger.info("⚠️ DataManager nie ma db_helper")
                        
                else:
logger.info("❌ PortfolioManager nie ma data_manager")
                pass
                    
            except Exception as e:
logger.info(f"❌ Błąd integracji: {e}")
        
        # 6. Test podstawowych operacji
logger.info("\n6️⃣ Test podstawowych operacji...")
        if portfolio_manager:
            try:
                # Test pobrania podsumowania portfela
                summary = await portfolio_manager.get_portfolio_summary()
logger.info(f"✅ Portfolio summary: {type(summary).__name__}")
logger.info(f"   Total value: {summary.total_value}")
logger.info(f"   Positions: {len(summary.positions)}")
                
            except Exception as e:
logger.info(f"⚠️ Portfolio summary błąd: {e}")
        
        # Zamknij połączenia
        await db_manager.close()
logger.info("\n🎉 Test integracji zakończony!")
        return True
        
    except Exception as e:
logger.info(f"\n❌ Błąd podczas testu integracji: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Główna funkcja testowa"""
    success = await test_database_portfolio_integration()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)