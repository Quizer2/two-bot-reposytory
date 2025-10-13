import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.strategy.dca import DCAStrategy
from app.bot_manager import BotType
import logging
logger = logging.getLogger(__name__)

# Mock exchange dla testów
class MockExchange:
    def __init__(self):
        self.name = "mock_exchange"
    
    async def get_balance(self, symbol):
        return {"free": 1000.0, "used": 0.0, "total": 1000.0}
    
    async def create_order(self, symbol, type, side, amount, price=None):
        return {"id": "mock_order_123", "status": "filled"}

# Mock database manager
class MockDatabaseManager:
    async def get_orders_by_bot_id(self, bot_id):
        return []

# Mock risk manager
class MockRiskManager:
    def __init__(self):
        pass

async def test_strategy_creation():
    """Test tworzenia strategii DCA"""
logger.info("Test tworzenia strategii DCA...")
    
    # Parametry strategii
    parameters = {
        'pair': 'BTCUSDT',
        'amount': 100.0,
        'interval': 3600,  # 1 godzina
        'max_orders': 10,
        'price_deviation': 0.02
    }
    
    try:
        # Tworzenie strategii DCA
        strategy = DCAStrategy(
            bot_id=999,
            exchange_name='binance',
            parameters=parameters
        )
logger.info(f"✓ Strategia DCA utworzona pomyślnie")
logger.info(f"  - Bot ID: {strategy.bot_id}")
logger.info(f"  - Exchange: {strategy.exchange_name}")
logger.info(f"  - Para: {strategy.parameters['pair']}")
logger.info(f"  - Kwota: {strategy.parameters['amount']}")
        
        # Test inicjalizacji z mock komponentami
        mock_db = MockDatabaseManager()
        mock_risk = MockRiskManager()
        mock_exchange = MockExchange()
        
        result = await strategy.initialize(mock_db, mock_risk, mock_exchange)
        
        if result:
            pass
logger.info("✓ Strategia zainicjalizowana pomyślnie")
            pass
        else:
logger.info("✗ Błąd inicjalizacji strategii")
logger.info("Test zakończony pomyślnie!")
        pass
        
    except Exception as e:
logger.info(f"✗ Błąd podczas testu: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_strategy_creation())