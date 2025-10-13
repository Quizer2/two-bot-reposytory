#!/usr/bin/env python3
"""
Test integracji AI Trading Bot ze wszystkimi dostępnymi giełdami

Sprawdza kompatybilność AI Trading Bot z:
- Binance
- Bybit  
- KuCoin
- Coinbase
- Kraken
- Bitfinex
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, List, Any
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_ai_all_exchanges():
    """Test AI Trading Bot ze wszystkimi dostępnymi giełdami"""
logger.info("🤖 Test AI Trading Bot ze wszystkimi giełdami")
logger.info("=" * 60)
    
    try:
        # Import wszystkich giełd
        from app.exchange.binance import BinanceExchange
        from app.exchange.bybit import BybitExchange
        from app.exchange.kucoin import KuCoinExchange
        from app.exchange.coinbase import CoinbaseExchange
        from app.exchange.kraken import KrakenExchange
        from app.exchange.bitfinex import BitfinexExchange
        from app.strategy.ai_trading_bot import AITradingBot
        from app.bot_manager import BotManager, BotType
        from core.database_manager import DatabaseManager
        from app.risk_management import RiskManager
logger.info("✅ Wszystkie importy zakończone pomyślnie")
        
        # Konfiguracja testowych giełd
        exchanges_config = {
            'binance': {
                'class': BinanceExchange,
                'params': {'api_key': 'test_binance_key', 'api_secret': 'test_binance_secret', 'testnet': True},
                'pair': 'BTC/USDT'
            },
            'bybit': {
                'class': BybitExchange,
                'params': {'api_key': 'test_bybit_key', 'api_secret': 'test_bybit_secret', 'testnet': True},
                'pair': 'BTC/USDT'
            },
            'kucoin': {
                'class': KuCoinExchange,
                'params': {'api_key': 'test_kucoin_key', 'api_secret': 'test_kucoin_secret', 'passphrase': 'test_pass', 'testnet': True},
                'pair': 'BTC/USDT'
            },
            'coinbase': {
                'class': CoinbaseExchange,
                'params': {'api_key': 'test_coinbase_key', 'api_secret': 'test_coinbase_secret', 'testnet': True},
                'pair': 'BTC/USD'
            },
            'kraken': {
                'class': KrakenExchange,
                'params': {'api_key': 'test_kraken_key', 'api_secret': 'test_kraken_secret', 'testnet': True},
                'pair': 'BTC/USD'
            },
            'bitfinex': {
                'class': BitfinexExchange,
                'params': {'api_key': 'test_bitfinex_key', 'api_secret': 'test_bitfinex_secret', 'testnet': True},
                'pair': 'BTC/USD'
            }
        }
        
        # Wyniki testów
        test_results = {
            'exchange_creation': {},
            'ai_bot_creation': {},
            'ai_bot_initialization': {},
            'bot_manager_integration': {}
        }
        
        # Test 1: Tworzenie instancji giełd
logger.info("\n📊 Test 1: Tworzenie instancji wszystkich giełd")
logger.info("-" * 50)
        
        exchanges = {}
        for exchange_name, config in exchanges_config.items():
            try:
                exchange_class = config['class']
                exchange_params = config['params']
                
                exchange = exchange_class(**exchange_params)
                exchanges[exchange_name] = exchange
logger.info(f"✅ {exchange_name.upper()}: {exchange.get_exchange_name()}")
                test_results['exchange_creation'][exchange_name] = True
                
            except Exception as e:
                pass
logger.info(f"❌ {exchange_name.upper()}: {e}")
                test_results['exchange_creation'][exchange_name] = False
        
        # Test 2: Tworzenie AI Trading Bot dla każdej giełdy
logger.info("\n🧠 Test 2: Tworzenie AI Trading Bot dla każdej giełdy")
logger.info("-" * 50)
        
        ai_bots = {}
            pass
                pass
        for exchange_name, exchange in exchanges.items():
            try:
                pair = exchanges_config[exchange_name]['pair']
                
                # Parametry AI Trading Bot
                ai_parameters = {
                    'pair': pair,
                    'budget': 1000.0 + (len(exchange_name) * 100),  # Różne budżety dla testów
                    'target_hourly_profit': 2.0 + (len(exchange_name) * 0.1),
                    'initial_balance': 1000.0,
                    'risk_percentage': 2.0,
                    'max_positions': 3,
                    'learning_rate': 0.001,
                    'model_update_frequency': 100,
                    'use_reinforcement_learning': True,
                    'feature_engineering_enabled': True,
                    'sentiment_analysis_enabled': exchange_name in ['kraken', 'bitfinex'],  # Tylko dla niektórych
                    'ensemble_models': True
                }
                
                ai_bot = AITradingBot(
                    bot_id=f"test_ai_{exchange_name}",
                    parameters=ai_parameters
                )
                
                ai_bots[exchange_name] = ai_bot
logger.info(f"✅ {exchange_name.upper()}: AI Bot utworzony")
logger.info(f"   - Bot ID: {ai_bot.bot_id}")
logger.info(f"   - Pair: {ai_bot.pair}")
logger.info(f"   - Budget: ${ai_bot.max_budget}")
logger.info(f"   - Target Profit: ${ai_bot.target_hourly_profit}/h")
logger.info(f"   - Sentiment Analysis: {ai_parameters['sentiment_analysis_enabled']}")
                
                test_results['ai_bot_creation'][exchange_name] = True
                
            except Exception as e:
logger.info(f"❌ {exchange_name.upper()}: {e}")
                test_results['ai_bot_creation'][exchange_name] = False
        
        # Test 3: Inicjalizacja AI botów
logger.info("\n⚙️ Test 3: Inicjalizacja AI botów")
logger.info("-" * 50)
        
        # Tymczasowe managery dla testów inicjalizacji
        db_manager = DatabaseManager()
            pass
                pass
        risk_manager = RiskManager()
        
        for exchange_name, ai_bot in ai_bots.items():
            try:
                exchange = exchanges[exchange_name]
                await ai_bot.initialize(db_manager, risk_manager, exchange)
                pass
logger.info(f"✅ {exchange_name.upper()}: AI Bot zainicjalizowany")
logger.info(f"   - Exchange: {ai_bot.exchange.get_exchange_name()}")
                test_results['ai_bot_initialization'][exchange_name] = True
                
            except Exception as e:
logger.info(f"⚠️ {exchange_name.upper()}: Inicjalizacja - {e}")
                test_results['ai_bot_initialization'][exchange_name] = False
        
            pass
        # Test 4: Integracja z BotManager
            pass
logger.info("\n🔧 Test 4: Integracja z BotManager")
logger.info("-" * 50)
        
        # Sprawdź czy AI jest w BotType
        if hasattr(BotType, 'AI'):
logger.info("✅ BotType.AI dostępny")
            pass
                pass
        else:
logger.info("❌ BotType.AI nie jest dostępny")
            return False
        
        # Test tworzenia AI bota przez BotManager dla każdej giełdy
        # Używamy tego samego db_manager co wcześniej
        
        for exchange_name, exchange in exchanges.items():
            try:
                bot_manager = BotManager(db_manager, exchange)
                
                # Parametry dla BotManager
                strategy_params = {
                    'initial_balance': 1500.0,
                    'target_hourly_profit': 3.0,
                    'risk_percentage': 1.8,
                    'max_positions': 4,
                    'learning_rate': 0.0008,
                    'model_update_frequency': 120,
                    'use_reinforcement_learning': True,
                    'feature_engineering_enabled': True,
                    'sentiment_analysis_enabled': True,
                    'ensemble_models': False
                }
                    pass
                
                pair = exchanges_config[exchange_name]['pair']
                ai_strategy = await bot_manager.create_strategy_instance(
                    bot_type=BotType.AI,
                    pair=pair,
                    parameters=strategy_params,
                    bot_id=1000 + len(exchange_name)
                )
                
                if ai_strategy:
logger.info(f"✅ {exchange_name.upper()}: AI Strategy przez BotManager")
logger.info(f"   - Type: {type(ai_strategy).__name__}")
logger.info(f"   - Exchange: {ai_strategy.exchange.get_exchange_name()}")
logger.info(f"   - Pair: {ai_strategy.pair}")
                    test_results['bot_manager_integration'][exchange_name] = True
                else:
logger.info(f"❌ {exchange_name.upper()}: Nie udało się utworzyć AI Strategy")
                    test_results['bot_manager_integration'][exchange_name] = False
                    
            except Exception as e:
logger.info(f"⚠️ {exchange_name.upper()}: BotManager - {e}")
                test_results['bot_manager_integration'][exchange_name] = False
        
        # Test 5: Podsumowanie wyników
logger.info("\n📊 Test 5: Podsumowanie wyników")
logger.info("=" * 60)
        
                pass
        total_exchanges = len(exchanges_config)
        
        for test_name, results in test_results.items():
            passed = sum(1 for result in results.values() if result)
            failed = total_exchanges - passed
            success_rate = (passed / total_exchanges) * 100 if total_exchanges > 0 else 0
logger.info(f"\n{test_name.replace('_', ' ').title()}:")
logger.info(f"  ✅ Passed: {passed}/{total_exchanges} ({success_rate:.1f}%)")
            pass
logger.info(f"  ❌ Failed: {failed}/{total_exchanges}")
            
            if failed > 0:
                failed_exchanges = [name for name, result in results.items() if not result]
logger.info(f"  Failed exchanges: {', '.join(failed_exchanges)}")
        
        # Sprawdź ogólny sukces
        all_tests_passed = all(
            all(results.values()) for results in test_results.values()
        )
logger.info(f"\n{'='*60}")
        if all_tests_passed:
logger.info("🎉 WSZYSTKIE TESTY PRZESZŁY POMYŚLNIE!")
logger.info("AI Trading Bot jest kompatybilny ze wszystkimi giełdami!")
        else:
logger.info("⚠️ NIEKTÓRE TESTY NIE PRZESZŁY")
logger.info("AI Trading Bot wymaga dodatkowych poprawek dla niektórych giełd")
logger.info(f"{'='*60}")
        
        return all_tests_passed
        
        pass
    except Exception as e:
logger.info(f"❌ Krytyczny błąd testu: {e}")
        import traceback
        traceback.print_exc()
        return False

    pass
async def main():
    """Główna funkcja testowa"""
logger.info(f"🚀 Rozpoczęcie testów AI Trading Bot - {datetime.now()}")
    
    success = await test_ai_all_exchanges()
    
    if success:
logger.info("\n✅ Test zakończony sukcesem!")
        return 0
    else:
logger.info("\n❌ Test zakończony niepowodzeniem!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)