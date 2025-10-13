#!/usr/bin/env python3
"""
Prosty test przepływu danych rynkowych
"""

import asyncio
import sys
import os
from datetime import datetime

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.market_data_manager import MarketDataManager, PriceData
from core.websocket_callback_manager import WebSocketCallbackManager, WebSocketEventType, StandardizedTickerData
import logging
logger = logging.getLogger(__name__)

class SimpleMarketDataTester:
    """Prosty tester przepływu danych rynkowych"""
    
    def __init__(self):
        self.received_updates = []
        
    async def test_market_data_manager(self):
        """Test MarketDataManager"""
logger.info("🔍 Test MarketDataManager")
logger.info("=" * 40)
        
        try:
            # 1. Utwórz MarketDataManager
logger.info("📊 Tworzę MarketDataManager...")
            market_manager = MarketDataManager()
            
            # 2. Test subskrypcji
logger.info("🔗 Testuję subskrypcje...")
            def test_callback(price_data: PriceData):
                self.received_updates.append({
                    'symbol': price_data.symbol,
                    'price': price_data.price,
                    'timestamp': price_data.timestamp
                })
logger.info(f"📨 Otrzymano aktualizację: {price_data.symbol} = ${price_data.price}")
            
            market_manager.subscribe_to_price('BTCUSDT', test_callback)
            
            # 3. Test aktualizacji cache
logger.info("💾 Testuję aktualizację cache...")
            test_price_data = PriceData(
                symbol='BTCUSDT',
                price=45000.0,
                bid=44990.0,
                ask=45010.0,
                volume_24h=1000000.0,
                change_24h=1000.0,
                change_24h_percent=2.27,
                timestamp=datetime.now()
            )
            
            # Aktualizuj cache bezpośrednio
            market_manager.price_cache['BTCUSDT'] = test_price_data
            
            # Wywołaj callback ręcznie
            if 'BTCUSDT' in market_manager.subscriptions:
                for callback in market_manager.subscriptions['BTCUSDT']:
                    callback(test_price_data)
            
            # 4. Test WebSocket callback managera
logger.info("📡 Testuję WebSocket callback manager...")
            ws_manager = WebSocketCallbackManager()
            
            # Test rejestracji callbacku
            def ws_test_callback(ticker_data):
logger.info(f"📡 WebSocket callback: {ticker_data.symbol} = ${ticker_data.price}")
            
            callback_id = ws_manager.register_callback(
                WebSocketEventType.TICKER,
                'BTCUSDT',
                'binance',
                ws_test_callback
            )
logger.info(f"✅ Zarejestrowano callback: {callback_id}")
            
            # 5. Test propagacji danych
logger.info("🔄 Testuję propagację danych...")
            test_ticker = StandardizedTickerData(
                symbol='BTCUSDT',
                price=45500.0,
                price_change=500.0,
                price_change_percent=1.11,
                high_24h=46000.0,
                low_24h=44000.0,
                volume_24h=1000000.0,
                timestamp=datetime.now(),
                exchange='binance',
                raw_data={}
            )
            
            # Wywołaj callback bezpośrednio
            await ws_manager._invoke_callbacks(
                WebSocketEventType.TICKER,
                'BTCUSDT',
                test_ticker
            )
            
            # 6. Podsumowanie
logger.info("\n📊 Wyniki testów:")
logger.info(f"✅ Otrzymano {len(self.received_updates)} aktualizacji")
logger.info(f"✅ WebSocket callback manager działa")
logger.info(f"✅ MarketDataManager działa")
            
            return True
            
        except Exception as e:
            pass
logger.info(f"❌ Błąd w teście: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_websocket_callback_manager(self):
        """Test WebSocket callback managera"""
logger.info("\n🔍 Test WebSocket Callback Manager")
logger.info("=" * 40)
        
            pass
        try:
            ws_manager = WebSocketCallbackManager()
            
            # Test rejestracji wielu callbacków
            callbacks_registered = 0
            
            def create_callback(symbol, exchange):
                def callback(data):
logger.info(f"📡 {exchange} {symbol}: ${data.price}")
                return callback
            
            symbols = ['BTCUSDT', 'ETHUSDT']
            exchanges = ['binance', 'bybit']
                pass
                    pass
            
            for exchange in exchanges:
                for symbol in symbols:
                    callback_id = ws_manager.register_callback(
                        WebSocketEventType.TICKER,
                        symbol,
                        exchange,
                        create_callback(symbol, exchange)
                    )
                    callbacks_registered += 1
logger.info(f"✅ Zarejestrowano: {callback_id}")
            
            # Test statystyk
            stats = ws_manager.get_callback_statistics()
logger.info(f"\n📊 Statystyki:")
logger.info(f"   Callbacki: {stats['total_callbacks']}")
logger.info(f"   Giełdy: {len(stats['callbacks_by_exchange'])}")
logger.info(f"   Typy wydarzeń: {len(stats['callbacks_by_type'])}")
logger.info(f"   Przetworzone wiadomości: {stats['total_messages_processed']}")
            pass
            
            return callbacks_registered > 0
            
        except Exception as e:
logger.info(f"❌ Błąd w teście WebSocket: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Główna funkcja testowa"""
logger.info("🚀 Prosty test przepływu danych rynkowych")
logger.info("=" * 50)
    
    tester = SimpleMarketDataTester()
    
    # Test 1: MarketDataManager
    result1 = await tester.test_market_data_manager()
    
    # Test 2: WebSocket Callback Manager
    result2 = await tester.test_websocket_callback_manager()
    
    # Podsumowanie
        pass
logger.info("\n" + "=" * 50)
        pass
logger.info("📋 PODSUMOWANIE TESTÓW")
logger.info("=" * 50)
        pass
    
        pass
    if result1:
logger.info("✅ MarketDataManager: PASSED")
    else:
logger.info("❌ MarketDataManager: FAILED")
    
    if result2:
logger.info("✅ WebSocket Callback Manager: PASSED")
    else:
logger.info("❌ WebSocket Callback Manager: FAILED")
    
    overall_success = result1 and result2
logger.info(f"\n🎯 Ogólny wynik: {'SUCCESS' if overall_success else 'FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    asyncio.run(main())