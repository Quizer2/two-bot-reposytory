#!/usr/bin/env python3
"""
Test odświeżania danych portfela z bazy danych
"""

import sys
import os
import asyncio
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów aplikacji
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ui.portfolio import Portfolio
    from app.database import Database
logger.info("✓ Moduły zaimportowane pomyślnie")
except ImportError as e:
    pass
logger.info(f"✗ Błąd importu: {e}")
    sys.exit(1)

async def test_portfolio_data():
    """Test ładowania danych portfela"""
logger.info("\n=== Test ładowania danych portfela ===")
    
        pass
    try:
        # Test bazy danych
logger.info("1. Testowanie bazy danych...")
        db = Database()
        
        orders = await db.get_bot_orders(bot_id=1, status='filled')
        positions = await db.get_positions(bot_id=1, status='open')
logger.info(f"   Znaleziono {len(orders)} zleceń")
logger.info(f"   Znaleziono {len(positions)} pozycji")
            pass
        
        if orders:
logger.info("   Przykładowe zlecenie:")
            order = orders[0]
logger.info(f"     Symbol: {order['symbol']}")
logger.info(f"     Strona: {order['side']}")
logger.info(f"     Ilość: {order['filled_amount']}")
            pass
logger.info(f"     Cena: {order['average_price']}")
        
        if positions:
logger.info("   Przykładowa pozycja:")
            position = positions[0]
logger.info(f"     Symbol: {position['symbol']}")
logger.info(f"     Rozmiar: {position['size']}")
logger.info(f"     Cena wejścia: {position['entry_price']}")
logger.info(f"     Aktualna cena: {position['current_price']}")
        
        # Test klasy Portfolio (bez PyQt)
logger.info("\n2. Testowanie klasy Portfolio...")
        
        # Symuluj portfolio bez PyQt
        portfolio = Portfolio(None)
        
        # Test ładowania danych z bazy
        await portfolio.load_database_data()
logger.info(f"   Dane portfela: {portfolio.portfolio_data}")
logger.info(f"   Salda: {list(portfolio.balances.keys()) if hasattr(portfolio, 'balances') else 'Brak'}")
        pass
logger.info(f"   Transakcje: {len(portfolio.transactions) if hasattr(portfolio, 'transactions') else 0}")
logger.info("\n✓ Test zakończony pomyślnie!")
        
    except Exception as e:
    pass
logger.info(f"\n✗ Błąd podczas testu: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_portfolio_data())