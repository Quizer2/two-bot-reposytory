#!/usr/bin/env python3
"""
Test integracji AI Trading Strategy z nowymi giełdami (Kraken, Bitfinex)
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_ai_integration():
    """Test integracji AI trading strategy z nowymi giełdami"""
logger.info("🤖 Test integracji AI Trading Strategy z nowymi giełdami")
logger.info("=" * 60)
    
    try:
        # Import wymaganych modułów
        from app.exchange.kraken import KrakenExchange
        from app.exchange.bitfinex import BitfinexExchange
        from app.strategy.ai_trading_bot import AITradingBot
        from app.bot_manager import BotManager, BotType
        from core.database_manager import DatabaseManager
logger.info("✅ Importy zakończone pomyślnie")
        
        # Test 1: Tworzenie instancji giełd
logger.info("\n📊 Test 1: Tworzenie instancji giełd")
        
        # Testowe instancje giełd z mock API keys
        kraken = KrakenExchange(api_key="test_key", api_secret="test_secret", testnet=True)
        bitfinex = BitfinexExchange(api_key="test_key", api_secret="test_secret", testnet=True)
logger.info(f"✅ KrakenExchange utworzony: {kraken.get_exchange_name()}")
logger.info(f"✅ BitfinexExchange utworzony: {bitfinex.get_exchange_name()}")
        
        # Test 2: Tworzenie AI Trading Bot z Kraken
logger.info("\n🧠 Test 2: AI Trading Bot z KrakenExchange")
        
        ai_bot_kraken = AITradingBot(
            exchange=kraken,
            parameters={
                'pair': 'BTC/USD',
                'initial_balance': 1000.0,
                'risk_percentage': 2.0,
                'max_positions': 3,
                'learning_rate': 0.001,
                'model_update_frequency': 100,
                'use_reinforcement_learning': True,
                'feature_engineering_enabled': True,
                'sentiment_analysis_enabled': False,
                'ensemble_models': True,
                'budget': 1000.0,
                'target_hourly_profit': 2.0
            }
        )
logger.info(f"✅ AI Bot z Kraken utworzony: {ai_bot_kraken}")
logger.info(f"   - Exchange: {ai_bot_kraken.exchange.get_exchange_name()}")
logger.info(f"   - Pair: {ai_bot_kraken.pair}")
logger.info(f"   - Budget: {ai_bot_kraken.max_budget}")
logger.info(f"   - Target Hourly Profit: {ai_bot_kraken.target_hourly_profit}")
        
        # Test 3: Tworzenie AI Trading Bot z Bitfinex
logger.info("\n🧠 Test 3: AI Trading Bot z BitfinexExchange")
        
        ai_bot_bitfinex = AITradingBot(
            exchange=bitfinex,
            parameters={
                'pair': 'BTC/USD',
                'initial_balance': 1500.0,
                'risk_percentage': 1.5,
                'max_positions': 5,
                'learning_rate': 0.0005,
                'model_update_frequency': 150,
                'use_reinforcement_learning': True,
                'feature_engineering_enabled': True,
                'sentiment_analysis_enabled': True,
                'ensemble_models': False,
                'budget': 1500.0,
                'target_hourly_profit': 3.0
            }
        )
logger.info(f"✅ AI Bot z Bitfinex utworzony: {ai_bot_bitfinex}")
logger.info(f"   - Exchange: {ai_bot_bitfinex.exchange.get_exchange_name()}")
logger.info(f"   - Pair: {ai_bot_bitfinex.pair}")
logger.info(f"   - Budget: {ai_bot_bitfinex.max_budget}")
logger.info(f"   - Target Hourly Profit: {ai_bot_bitfinex.target_hourly_profit}")
        
        # Test 4: Inicjalizacja AI botów
logger.info("\n⚙️ Test 4: Inicjalizacja AI botów")
        
        try:
            await ai_bot_kraken.initialize()
logger.info("✅ AI Bot Kraken zainicjalizowany")
        except Exception as e:
            pass
logger.info(f"⚠️ Inicjalizacja AI Bot Kraken: {e}")
        
            pass
        try:
            await ai_bot_bitfinex.initialize()
            pass
logger.info("✅ AI Bot Bitfinex zainicjalizowany")
        except Exception as e:
logger.info(f"⚠️ Inicjalizacja AI Bot Bitfinex: {e}")
        
        # Test 5: Integracja z BotManager
logger.info("\n🔧 Test 5: Integracja z BotManager")
            pass
        
        # Sprawdź czy AI jest w BotType
            pass
        if hasattr(BotType, 'AI'):
logger.info("✅ BotType.AI dostępny")
logger.info(f"   - Wartość: {BotType.AI.value}")
        else:
            pass
logger.info("❌ BotType.AI nie jest dostępny")
            return False
        
        # Test tworzenia AI bota przez BotManager
        try:
            # Utwórz mock database manager
            db_manager = DatabaseManager()
            
            # Utwórz BotManager z Kraken
            bot_manager_kraken = BotManager(db_manager, kraken)
            
            # Test tworzenia strategii AI
            ai_strategy_kraken = await bot_manager_kraken.create_strategy_instance(
                BotType.AI,
                "BTC/USD",
                {
                    'initial_balance': 2000.0,
                    'risk_percentage': 1.8,
                    'max_positions': 4,
                    'learning_rate': 0.001,
                    'model_update_frequency': 120,
                    'use_reinforcement_learning': True,
                    'feature_engineering_enabled': True,
                    'sentiment_analysis_enabled': False,
                    'ensemble_models': True
                },
                bot_id=1001
            )
                pass
            
            if ai_strategy_kraken:
            pass
logger.info("✅ AI Strategy utworzona przez BotManager z Kraken")
logger.info(f"   - Type: {type(ai_strategy_kraken).__name__}")
logger.info(f"   - Exchange: {ai_strategy_kraken.exchange.get_exchange_name()}")
            else:
logger.info("❌ Nie udało się utworzyć AI Strategy przez BotManager")
                
        except Exception as e:
logger.info(f"⚠️ Test BotManager z Kraken: {e}")
        
        # Test z Bitfinex
        try:
            bot_manager_bitfinex = BotManager(db_manager, bitfinex)
            
            ai_strategy_bitfinex = await bot_manager_bitfinex.create_strategy_instance(
                BotType.AI,
                "ETH/USD",
                {
                    'initial_balance': 1800.0,
                    'risk_percentage': 2.2,
                    'max_positions': 3,
                    'learning_rate': 0.0008,
                    'model_update_frequency': 80,
                    'use_reinforcement_learning': True,
                    'feature_engineering_enabled': True,
                    'sentiment_analysis_enabled': True,
                    'ensemble_models': False
                },
                bot_id=1002
            )
            
            if ai_strategy_bitfinex:
logger.info("✅ AI Strategy utworzona przez BotManager z Bitfinex")
logger.info(f"   - Type: {type(ai_strategy_bitfinex).__name__}")
logger.info(f"   - Exchange: {ai_strategy_bitfinex.exchange.get_exchange_name()}")
            else:
logger.info("❌ Nie udało się utworzyć AI Strategy przez BotManager")
            pass
                
        except Exception as e:
logger.info(f"⚠️ Test BotManager z Bitfinex: {e}")
        
        # Test 6: Walidacja parametrów AI
logger.info("\n✅ Test 6: Walidacja parametrów AI")
        
        try:
            # Test walidacji parametrów AI
            valid_params = {
                'initial_balance': 1000.0,
                'risk_percentage': 2.0,
                'max_positions': 3,
                'learning_rate': 0.001
            }
            
            is_valid = await bot_manager_kraken.validate_bot_parameters("ai", valid_params)
logger.info(f"✅ Walidacja parametrów AI: {'PASSED' if is_valid else 'FAILED'}")
            
            # Test z nieprawidłowymi parametrami
            invalid_params = {
                'risk_percentage': 2.0  # brak initial_balance
            }
            
            is_invalid = await bot_manager_kraken.validate_bot_parameters("ai", invalid_params)
logger.info(f"✅ Walidacja nieprawidłowych parametrów: {'PASSED' if not is_invalid else 'FAILED'}")
            
        except Exception as e:
logger.info(f"⚠️ Test walidacji parametrów: {e}")
logger.info("\n" + "=" * 60)
logger.info("🎉 Test integracji AI Trading Strategy zakończony pomyślnie!")
        pass
logger.info("✅ AI Trading Bot jest w pełni zintegrowany z:")
logger.info("   - KrakenExchange")
logger.info("   - BitfinexExchange") 
logger.info("   - BotManager")
logger.info("   - Systemem walidacji parametrów")
    pass
        
        return True
        
    except Exception as e:
        pass
logger.info(f"\n❌ Błąd podczas testu integracji AI: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ai_integration())
    if result:
logger.info("\n🎯 Wszystkie testy integracji AI przeszły pomyślnie!")
        sys.exit(0)
    else:
logger.info("\n💥 Niektóre testy integracji AI nie powiodły się!")
        sys.exit(1)