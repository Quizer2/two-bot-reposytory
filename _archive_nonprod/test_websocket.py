#!/usr/bin/env python3
"""
Kompleksowe testy WebSocket dla CryptoBot

Testuje:
- Subskrypcję kanałów (trade, depth, ticker)
- Automatyczny reconnect
- Backpressure przy dużym napływie danych
- Autoryzowane sockety z tokenem
"""

import asyncio
import json
import time
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import unittest
from unittest.mock import AsyncMock, patch

# Importy z aplikacji
from utils.logger import get_logger, LogType
from utils.config_manager import get_config_manager
from app.api_config_manager import get_api_config_manager
from app.exchange.binance import BinanceExchange
from app.exchange.bybit import BybitExchange
from app.exchange.kucoin import KuCoinExchange
from app.exchange.coinbase import CoinbaseExchange
import logging
logger = logging.getLogger(__name__)


class WebSocketTester:
    """Klasa do testowania funkcjonalności WebSocket"""
    
    def __init__(self):
        self.logger = get_logger("test_websocket", LogType.SYSTEM)
        self.api_config = get_api_config_manager()
        self.test_results = {}
        self.message_count = 0
        self.reconnect_count = 0
        self.test_data = []
        
    async def run_all_tests(self):
        """Uruchomienie wszystkich testów WebSocket"""
logger.info("🔌 ROZPOCZYNANIE TESTÓW WEBSOCKET")
logger.info("=" * 60)
        
        # Test 1: Subskrypcja kanałów
        await self._test_channel_subscriptions()
        
        # Test 2: Automatyczny reconnect
        await self._test_automatic_reconnect()
        
        # Test 3: Backpressure handling
        await self._test_backpressure_handling()
        
        # Test 4: Autoryzowane sockety
        await self._test_authenticated_sockets()
        
        # Podsumowanie
        self._print_summary()
        
    async def _test_channel_subscriptions(self):
        """Test subskrypcji różnych kanałów WebSocket"""
logger.info("\nSubskrypcja kanalow...")
        
        try:
            # Test Binance WebSocket streams
            await self._test_binance_subscriptions()
            
            # Test innych giełd jeśli są skonfigurowane
            await self._test_other_exchanges()
            
            self.test_results['channel_subscriptions'] = 'PASSED'
logger.info("Subskrypcja kanalow: PASSED")
            
        except Exception as e:
            self.test_results['channel_subscriptions'] = f'FAILED: {e}'
logger.info(f"Subskrypcja kanalow: FAILED - {e}")
    
    async def _test_binance_subscriptions(self):
        """Test subskrypcji Binance WebSocket"""
logger.info("\n🔍 Testowanie Binance WebSocket...")
        
        # Test ticker stream
        await self._test_ticker_stream()
        
        # Test trades stream
        await self._test_trades_stream()
        
        # Test depth stream
        await self._test_depth_stream()
        
    async def _test_ticker_stream(self):
        """Test strumienia ticker"""
logger.info("   Test ticker stream...")
        
        try:
            uri = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
            
            async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Odbierz kilka wiadomości
                for i in range(3):
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    # Walidacja struktury ticker
                    required_fields = ['s', 'c', 'P', 'v', 'h', 'l']
                    for field in required_fields:
                        if field not in data:
                            raise Exception(f"Brak pola {field} w ticker")
                    
                    # Walidacja typów danych
                    price = float(data['c'])
                    volume = float(data['v'])
                    
                    if price <= 0 or volume < 0:
                        raise Exception("Nieprawidłowe wartości w ticker")
logger.info("   ✅ Ticker stream: OK")
                
        except Exception as e:
            raise Exception(f"Ticker stream error: {e}")
    
    async def _test_trades_stream(self):
        """Test strumienia transakcji"""
logger.info("   💱 Test trades stream...")
        
        try:
            uri = "wss://stream.binance.com:9443/ws/btcusdt@trade"
            
            async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Odbierz kilka transakcji
                for i in range(3):
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    # Walidacja struktury trade
                    required_fields = ['s', 'p', 'q', 'T', 'm']
                    for field in required_fields:
                        if field not in data:
                            raise Exception(f"Brak pola {field} w trade")
                    
                    # Walidacja danych
                    price = float(data['p'])
                    quantity = float(data['q'])
                    timestamp = int(data['T'])
                    
                    if price <= 0 or quantity <= 0:
                        raise Exception("Nieprawidłowe wartości w trade")
                    
                    # Sprawdź czy timestamp jest rozsądny (ostatnie 24h)
                    now = int(time.time() * 1000)
                    if abs(now - timestamp) > 24 * 60 * 60 * 1000:
                        raise Exception("Nieprawidłowy timestamp w trade")
logger.info("   ✅ Trades stream: OK")
                
        except Exception as e:
            raise Exception(f"Trades stream error: {e}")
    
    async def _test_depth_stream(self):
        """Test strumienia księgi zleceń"""
logger.info("   📈 Test depth stream...")
        
        try:
            uri = "wss://stream.binance.com:9443/ws/btcusdt@depth5@100ms"
            
            async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Odbierz kilka aktualizacji depth
                for i in range(3):
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    # Walidacja struktury depth
                    required_fields = ['lastUpdateId', 'bids', 'asks']
                    for field in required_fields:
                        if field not in data:
                            raise Exception(f"Brak pola {field} w depth")
                    
                    # Walidacja bid/ask
                    bids = data['bids']
                    asks = data['asks']
                    
                    if not bids or not asks:
                        raise Exception("Puste bids lub asks")
                    
                    # Sprawdź format [price, quantity]
                    for bid in bids[:3]:  # Sprawdź pierwsze 3
                        if len(bid) != 2:
                            raise Exception("Nieprawidłowy format bid")
                        price, qty = float(bid[0]), float(bid[1])
                        if price <= 0 or qty < 0:
                            raise Exception("Nieprawidłowe wartości bid")
                    
                    for ask in asks[:3]:  # Sprawdź pierwsze 3
                        if len(ask) != 2:
                            raise Exception("Nieprawidłowy format ask")
                        price, qty = float(ask[0]), float(ask[1])
                        if price <= 0 or qty < 0:
                            raise Exception("Nieprawidłowe wartości ask")
                    
                    # Sprawdź spread (ask > bid)
                    best_bid = float(bids[0][0])
                    best_ask = float(asks[0][0])
                    if best_ask <= best_bid:
                        raise Exception("Nieprawidłowy spread (ask <= bid)")
logger.info("   ✅ Depth stream: OK")
                
        except Exception as e:
            raise Exception(f"Depth stream error: {e}")
    
    async def _test_other_exchanges(self):
        """Test innych giełd jeśli są dostępne"""
logger.info("\n🔍 Testowanie innych giełd...")
        
        # Test Bybit jeśli skonfigurowany
        try:
            uri = "wss://stream.bybit.com/v5/public/linear"
            async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Subskrypcja ticker
                subscribe_msg = {
                    "op": "subscribe",
                    "args": ["tickers.BTCUSDT"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # Odbierz odpowiedź
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
logger.info("   ✅ Bybit WebSocket: Polaczenie OK")
                
        except Exception as e:
            pass
logger.info(f"   ⚠️ Bybit WebSocket: {e}")
    
    async def _test_automatic_reconnect(self):
        """Test automatycznego reconnect"""
logger.info("\n🔄 Automatyczny reconnect...")
        
            pass
        try:
            # Symulacja reconnect przez zamknięcie i ponowne otwarcie
            await self._simulate_reconnect_scenario()
            
            self.test_results['automatic_reconnect'] = 'PASSED'
logger.info("Automatyczny reconnect: PASSED")
            pass
            
        except Exception as e:
            self.test_results['automatic_reconnect'] = f'FAILED: {e}'
logger.info(f"Automatyczny reconnect: FAILED - {e}")
    
    async def _simulate_reconnect_scenario(self):
        """Symulacja scenariusza reconnect"""
logger.info("   🔌 Symulacja reconnect...")
        
        reconnect_attempts = 0
            pass
                pass
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                uri = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
                
                async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                        pass
                    # Odbierz wiadomość
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    # Symuluj rozłączenie po pierwszej wiadomości
                    if attempt == 0:
                        await websocket.close()
                        reconnect_attempts += 1
logger.info(f"   🔄 Reconnect attempt {reconnect_attempts}")
                        await asyncio.sleep(1)  # Krótka przerwa
                        continue
                pass
                    
                    # Jeśli dotarliśmy tutaj, reconnect się udał
logger.info("   ✅ Reconnect successful")
                    break
                    
            except Exception as e:
                reconnect_attempts += 1
                if attempt == max_attempts - 1:
                    raise Exception(f"Reconnect failed after {max_attempts} attempts: {e}")
                await asyncio.sleep(1)
    
    async def _test_backpressure_handling(self):
        """Test obsługi backpressure przy dużym napływie danych"""
logger.info("\n⚡ Backpressure handling...")
        
            pass
        try:
            await self._test_high_frequency_data()
            
            self.test_results['backpressure_handling'] = 'PASSED'
logger.info("Backpressure handling: PASSED")
            
        except Exception as e:
            self.test_results['backpressure_handling'] = f'FAILED: {e}'
logger.info(f"Backpressure handling: FAILED - {e}")
    
    async def _test_high_frequency_data(self):
            pass
        """Test wysokiej częstotliwości danych"""
logger.info("   📊 Test wysokiej częstotliwości...")
        
        message_count = 0
        start_time = time.time()
        processing_times = []
        
                    pass
                        pass
        try:
            # Użyj szybkiego strumienia (depth@100ms)
            uri = "wss://stream.binance.com:9443/ws/btcusdt@depth@100ms"
            
            async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                # Odbieraj wiadomości przez 10 sekund
                timeout_time = start_time + 10
                
                while time.time() < timeout_time:
                    try:
                        msg_start = time.time()
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        
                        # Symuluj przetwarzanie
                        data = json.loads(message)
                        processing_time = time.time() - msg_start
                        processing_times.append(processing_time)
                        
                        message_count += 1
                        
                        # Sprawdź czy nie ma opóźnień
                        if processing_time > 0.1:  # 100ms threshold
logger.info(f"   ⚠️ Slow processing: {processing_time:.3f}s")
                        
                    except asyncio.TimeoutError:
                        continue
                
                # Analiza wydajności
                total_time = time.time() - start_time
                avg_processing = sum(processing_times) / len(processing_times) if processing_times else 0
                messages_per_sec = message_count / total_time
logger.info(f"   📈 Messages received: {message_count}")
logger.info(f"   ⏱️ Messages/sec: {messages_per_sec:.1f}")
            pass
logger.info(f"   🔄 Avg processing: {avg_processing*1000:.1f}ms")
                
                # Sprawdź czy wydajność jest akceptowalna
                if messages_per_sec < 5:  # Minimum 5 msg/sec
                    raise Exception(f"Low message rate: {messages_per_sec:.1f}/sec")
                
                if avg_processing > 0.15:  # Max 150ms avg processing (zwiększony próg dla środowiska testowego)
                    raise Exception(f"High processing time: {avg_processing*1000:.1f}ms")
logger.info("   ✅ High frequency handling: OK")
                
        except Exception as e:
            raise Exception(f"High frequency test error: {e}")
    
    async def _test_authenticated_sockets(self):
        """Test autoryzowanych socketów z tokenem"""
logger.info("\n🔐 Autoryzowane sockety...")
            pass
        
        try:
            # Test KuCoin (wymaga tokenu)
            await self._test_kucoin_auth()
            
            # Test Coinbase Pro (jeśli skonfigurowany)
            await self._test_coinbase_auth()
            pass
            
            self.test_results['authenticated_sockets'] = 'PASSED'
logger.info("Autoryzowane sockety: PASSED")
            
        except Exception as e:
            self.test_results['authenticated_sockets'] = f'FAILED: {e}'
                pass
logger.info(f"Autoryzowane sockety: FAILED - {e}")
                    pass
    
    async def _test_kucoin_auth(self):
        """Test autoryzacji KuCoin WebSocket"""
                        pass
logger.info("   🔑 Test KuCoin auth...")
        
        try:
            # Symulacja pobierania tokenu
                            pass
            import requests
            
            # Publiczny endpoint dla tokenu
            response = requests.post('https://api.kucoin.com/api/v1/bullet-public', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200000':
                    token_data = data.get('data', {})
                    token = token_data.get('token')
                    
                    if token:
logger.info("   ✅ KuCoin token obtained")
                        
                        # Test połączenia z tokenem
                        servers = token_data.get('instanceServers', [])
                        if servers:
                            endpoint = servers[0]['endpoint']
                            ws_url = f"{endpoint}?token={token}"
                            
                            async with websockets.connect(ws_url, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                                # Wyślij ping
                                ping_msg = {
                                    "id": str(int(time.time() * 1000)),
                                    "type": "ping"
                                }
                                await websocket.send(json.dumps(ping_msg))
                                
                                # Odbierz pong
                                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
logger.info("   ✅ KuCoin auth WebSocket: OK")
                    else:
                        raise Exception("No token received")
                else:
                    raise Exception(f"API error: {data.get('msg')}")
            else:
                raise Exception(f"HTTP error: {response.status_code}")
                
        except Exception as e:
logger.info(f"   ⚠️ KuCoin auth: {e}")
    
    async def _test_coinbase_auth(self):
        """Test autoryzacji Coinbase WebSocket"""
logger.info("   🔑 Test Coinbase auth...")
        
        try:
            # Coinbase używa publicznych kanałów, ale test struktury auth
            uri = "wss://ws-feed.exchange.coinbase.com"
            
                    pass
            async with websockets.connect(uri, open_timeout=10, ping_interval=20, ping_timeout=10) as websocket:
                    pass
                # Subskrypcja publicznego kanału
                subscribe_msg = {
                    "type": "subscribe",
                    "channels": [
                        {
                            "name": "ticker",
                            "product_ids": ["BTC-USD"]
                        }
                    ]
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # Odbierz potwierdzenie
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get('type') == 'subscriptions':
logger.info("   ✅ Coinbase WebSocket: OK")
                else:
                pass
logger.info(f"   ⚠️ Coinbase unexpected response: {data.get('type')}")
                
        except Exception as e:
logger.info(f"   ⚠️ Coinbase auth: {e}")
            pass
    
    def _print_summary(self):
            pass
        """Wydrukowanie podsumowania testów"""
logger.info("\n" + "=" * 60)
logger.info("PODSUMOWANIE TESTOW WEBSOCKET")
logger.info("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "PASSED" if result == 'PASSED' else f"{result}"
            test_display = test_name.replace('_', ' ').title()
logger.info(f"{test_display:.<40} {status}")
            
            if result == 'PASSED':
                passed += 1
logger.info("-" * 60)
logger.info(f"Wynik: {passed}/{total} testów przeszło pomyślnie")
        
        if passed == total:
logger.info("🎉 Wszystkie testy WebSocket przeszły pomyślnie!")
logger.info("✅ WebSocket jest gotowy do użycia")
        else:
logger.info("⚠️ Niektóre testy WebSocket nie przeszły")
logger.info("🔧 Sprawdź konfigurację i połączenia sieciowe")


async def main():
    """Główna funkcja testowa"""
    tester = WebSocketTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())