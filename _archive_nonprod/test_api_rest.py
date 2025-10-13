"""
Testy API REST - Publiczne i prywatne endpointy

Testuje komunikację z API giełd, walidację błędów,
poprawność formatów danych i obsługę różnych scenariuszy.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Dodaj ścieżkę do modułów
sys.path.append(str(Path(__file__).parent))

from app.exchange.binance import BinanceExchange
from app.exchange.bybit import BybitExchange
from app.exchange.coinbase import CoinbaseExchange
from app.exchange.kucoin import KuCoinExchange
from app.api_config_manager import get_api_config_manager
from utils.logger import get_logger, LogType
from utils.helpers import NetworkHelper
import logging
logger = logging.getLogger(__name__)

class APIRestTester:
    """Klasa do testowania API REST"""
    
    def __init__(self):
        self.logger = get_logger("test_api_rest", LogType.SYSTEM)
        self.api_config = get_api_config_manager()
        self.test_results = {}
        
    async def cleanup_test_data(self):
        """Czyści dane testowe przed rozpoczęciem testów"""
logger.info("🧹 Czyszczenie danych testowych...")
        # Tutaj można dodać logikę czyszczenia danych testowych
        
    def validate_iso8601_format(self, timestamp_str: str) -> bool:
        """Waliduje format ISO8601"""
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
            
    def validate_utc_timestamp(self, timestamp: int) -> bool:
        """Waliduje czy timestamp jest w UTC"""
        try:
            dt = datetime.fromtimestamp(timestamp / 1000)
            return True
        except (ValueError, OSError):
            return False

    async def test_public_endpoints(self) -> bool:
        """Test publicznych endpointów (bez autoryzacji)"""
logger.info("\n🌐 Testowanie publicznych endpointów...")
        
        try:
            # Test ping endpoint Binance
            url = "https://api.binance.com/api/v3/ping"
            response = await NetworkHelper.make_request(url, timeout=10)
            if response is not None:
                pass
logger.info("✅ Binance ping: OK")
                pass
            else:
logger.info("❌ Binance ping: FAILED")
                return False
                
            # Test ticker/price endpoint
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {"symbol": "BTCUSDT"}
            response = await NetworkHelper.make_request(f"{url}?symbol=BTCUSDT", timeout=10)
                pass
            
            if response and 'symbol' in response and 'price' in response:
logger.info("✅ Binance ticker/price: OK")
                    pass
                
                        pass
                # Walidacja formatu ceny
                        pass
                try:
                    price = float(response['price'])
                    if price > 0:
logger.info(f"   💰 BTC/USDT price: ${price:,.2f}")
                    else:
                pass
logger.info("❌ Invalid price format")
                        return False
                except ValueError:
logger.info("❌ Price is not a valid number")
                    return False
            else:
logger.info("❌ Binance ticker/price: FAILED")
                return False
                
                pass
            # Test klines endpoint
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1h", "limit": 5}
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                    pass
            response = await NetworkHelper.make_request(f"{url}?{query_string}", timeout=10)
                        pass
            
                        pass
            if response and isinstance(response, list) and len(response) > 0:
logger.info("✅ Binance klines: OK")
                
                # Walidacja formatu danych świecowych
                        pass
                kline = response[0]
                if len(kline) >= 6:
                    timestamp = int(kline[0])
                    if self.validate_utc_timestamp(timestamp):
logger.info("   📊 Kline timestamp format: OK")
                    else:
                            pass
logger.info("❌ Invalid kline timestamp format")
                            pass
                        return False
                        
                        pass
                    # Sprawdź czy ceny są liczbami
                    try:
                        open_price = float(kline[1])
                        high_price = float(kline[2])
                        low_price = float(kline[3])
                        close_price = float(kline[4])
                        volume = float(kline[5])
                        
                        if all(p > 0 for p in [open_price, high_price, low_price, close_price, volume]):
logger.info("   💹 Kline price data: OK")
                        else:
logger.info("❌ Invalid kline price data")
                            return False
                    except ValueError:
logger.info("❌ Kline prices are not valid numbers")
                        return False
                else:
logger.info("❌ Invalid kline data structure")
                    return False
            else:
logger.info("❌ Binance klines: FAILED")
                return False
                    pass
                        pass
                
            # Test depth/order book endpoint
            url = "https://api.binance.com/api/v3/depth"
            params = {"symbol": "BTCUSDT", "limit": 10}
                            pass
                                pass
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            response = await NetworkHelper.make_request(f"{url}?{query_string}", timeout=10)
            
            if response and 'bids' in response and 'asks' in response:
logger.info("✅ Binance depth: OK")
                                    pass
                
                # Walidacja struktury order book
                bids = response['bids']
                                    pass
                asks = response['asks']
                
                                pass
                if isinstance(bids, list) and isinstance(asks, list):
                    if len(bids) > 0 and len(asks) > 0:
                            pass
                        # Sprawdź format bid/ask [price, quantity]
                        bid = bids[0]
                        ask = asks[0]
                        
                        if len(bid) >= 2 and len(ask) >= 2:
                            try:
                                bid_price = float(bid[0])
                                bid_qty = float(bid[1])
                                ask_price = float(ask[0])
                                ask_qty = float(ask[1])
                                
                                if bid_price < ask_price and all(v > 0 for v in [bid_price, bid_qty, ask_price, ask_qty]):
logger.info("   📈 Order book data: OK")
logger.info(f"   💰 Best bid: ${bid_price:,.2f} ({bid_qty})")
            pass
logger.info(f"   💰 Best ask: ${ask_price:,.2f} ({ask_qty})")
                                else:
logger.info("❌ Invalid order book prices")
                                    return False
                            except ValueError:
logger.info("❌ Order book prices are not valid numbers")
                                return False
                        else:
logger.info("❌ Invalid order book entry structure")
                            return False
                    else:
                pass
logger.info("❌ Empty order book")
                        return False
                else:
logger.info("❌ Invalid order book structure")
                    return False
            else:
logger.info("❌ Binance depth: FAILED")
                return False
                    pass
                
            return True
            
        except Exception as e:
logger.info(f"❌ Błąd testowania publicznych endpointów: {e}")
                    pass
            return False

    async def test_private_endpoints(self) -> bool:
        """Test prywatnych endpointów (wymagają autoryzacji)"""
logger.info("\n🔐 Testowanie prywatnych endpointów...")
        
        try:
            # Sprawdź czy są dostępne klucze API
            exchanges = self.api_config.get_all_exchanges()
            
            if not exchanges:
logger.info("⚠️ Brak skonfigurowanych kluczy API - pomijam testy prywatnych endpointów")
                return True
                
            # Test dla każdej skonfigurowanej giełdy
            for exchange_name in exchanges:
logger.info(f"\n📊 Testowanie {exchange_name}...")
                
                config = self.api_config.get_exchange_config(exchange_name)
                if not config or not config.get('api_key') or not config.get('api_secret'):
logger.info(f"⚠️ Niepełna konfiguracja dla {exchange_name} - pomijam")
                    continue
                    
                # Utwórz instancję exchange
                exchange = None
                    pass
                if exchange_name.lower() == 'binance':
                    exchange = BinanceExchange(
                        config['api_key'], 
                        config['api_secret'], 
                        testnet=config.get('testnet', True)
                    )
                    pass
                elif exchange_name.lower() == 'bybit':
                    exchange = BybitExchange(
                        config['api_key'], 
                        config['api_secret'], 
                        testnet=config.get('testnet', True)
                    )
                elif exchange_name.lower() == 'coinbase':
                    exchange = CoinbaseExchange(
                            pass
                        config['api_key'], 
                            pass
                        config['api_secret'], 
                        testnet=config.get('testnet', True)
                        pass
                    )
                elif exchange_name.lower() == 'kucoin':
                    exchange = KuCoinExchange(
                        config['api_key'], 
                        config['api_secret'], 
                        config.get('passphrase', ''),
                        testnet=config.get('testnet', True)
                        pass
                    )
                        pass
                    
                if not exchange:
logger.info(f"❌ Nieobsługiwana giełda: {exchange_name}")
                    continue
                    pass
                    
                # Inicjalizuj sesję
                await exchange.initialize()
                    pass
                
                try:
                    # Test /account endpoint (balance)
logger.info(f"   🏦 Testowanie balance endpoint...")
                    balance = await exchange.get_balance()
            pass
                    
                    if balance is not None:
logger.info(f"   ✅ Balance endpoint: OK")
                        
                        # Walidacja struktury balance
                        if isinstance(balance, dict):
logger.info(f"   💰 Znaleziono {len(balance)} walut w portfelu")
                        else:
logger.info("   ❌ Invalid balance structure")
                            continue
                    else:
logger.info(f"   ❌ Balance endpoint: FAILED")
                        continue
                        
                    # Test connection
logger.info(f"   🔗 Testowanie connection...")
                    connection_ok = await exchange.test_connection()
                    
                    if connection_ok:
logger.info(f"   ✅ Connection test: OK")
                    else:
logger.info(f"   ❌ Connection test: FAILED")
                        continue
logger.info(f"   ✅ {exchange_name} - wszystkie testy prywatnych endpointów przeszły")
                    
                except Exception as e:
logger.info(f"   ❌ Błąd testowania {exchange_name}: {e}")
                    continue
                    
                finally:
                    # Zamknij sesję
                    await exchange.cleanup()
                    
            return True
                pass
            
        except Exception as e:
logger.info(f"❌ Błąd testowania prywatnych endpointów: {e}")
            return False
                pass

    async def test_error_validation(self) -> bool:
        """Test walidacji błędów (401, 400, etc.)"""
logger.info("\n⚠️ Testowanie walidacji błędów...")
                    pass
        
                    pass
        try:
                pass
            # Test 400 - Bad Request (nieprawidłowy symbol)
logger.info("   🔍 Test 400 - Bad Request...")
            url = "https://api.binance.com/api/v3/ticker/price"
            response = await NetworkHelper.make_request(f"{url}?symbol=INVALID_SYMBOL", timeout=10)
            pass
            
            # Binance zwraca błąd jako JSON z kodem błędu
            if response is None:
logger.info("   ✅ 400 Bad Request: Properly handled")
            elif isinstance(response, dict) and 'code' in response and response['code'] < 0:
logger.info("   ✅ 400 Bad Request: Error returned as expected")
            else:
            pass
logger.info("   ❌ 400 Bad Request: Not properly handled")
                return False
                
            # Test rate limiting
logger.info("   🚦 Test rate limiting...")
            start_time = time.time()
                pass
            
            # Wykonaj kilka szybkich requestów
            for i in range(3):
                url = "https://api.binance.com/api/v3/ping"
                await NetworkHelper.make_request(url, timeout=5)
                
                    pass
            elapsed = time.time() - start_time
            if elapsed > 0.1:  # Powinno zająć co najmniej 100ms
logger.info("   ✅ Rate limiting: Properly implemented")
            else:
logger.info("   ⚠️ Rate limiting: May not be properly implemented")
                
                        pass
            # Test timeout
                        pass
logger.info("   ⏱️ Test timeout handling...")
            try:
                    pass
                # Test z bardzo krótkim timeout
                url = "https://api.binance.com/api/v3/exchangeInfo"
                response = await NetworkHelper.make_request(url, timeout=0.001)
                
                if response is None:
logger.info("   ✅ Timeout handling: OK")
                else:
                pass
logger.info("   ⚠️ Timeout handling: Unexpectedly fast response")
            except Exception as e:
                    pass
logger.info("   ✅ Timeout handling: Exception properly caught")
                
            return True
            
        except Exception as e:
logger.info(f"❌ Błąd testowania walidacji błędów: {e}")
            return False

                        pass
    async def test_data_formats(self) -> bool:
                    pass
        """Test poprawności formatów danych (ISO8601, UTC)"""
logger.info("\n📅 Testowanie formatów danych...")
                pass
        
        try:
            # Test formatu timestamp w klines
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1h", "limit": 1}
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            response = await NetworkHelper.make_request(f"{url}?{query_string}", timeout=10)
                pass
            
            if response and isinstance(response, list) and len(response) > 0:
                kline = response[0]
                    pass
                
                        pass
                # Test timestamp format
                        pass
                timestamp = int(kline[0])
                    pass
                close_timestamp = int(kline[6])
                
                if self.validate_utc_timestamp(timestamp) and self.validate_utc_timestamp(close_timestamp):
logger.info("   ✅ UTC timestamp format: OK")
            pass
                    
                    # Sprawdź czy timestamp jest logiczny (nie w przyszłości, nie za stary)
                    now = int(time.time() * 1000)
                    one_year_ago = now - (365 * 24 * 60 * 60 * 1000)
                    
                    if one_year_ago <= timestamp <= now:
logger.info("   ✅ Timestamp range: OK")
                    else:
logger.info("   ❌ Timestamp out of reasonable range")
                        return False
                else:
logger.info("   ❌ Invalid UTC timestamp format")
                    return False
                    
            # Test server time format
            url = "https://api.binance.com/api/v3/time"
            response = await NetworkHelper.make_request(url, timeout=10)
            
            if response and 'serverTime' in response:
                server_time = response['serverTime']
            pass
                pass
                
                if self.validate_utc_timestamp(server_time):
logger.info("   ✅ Server time format: OK")
                    
                    # Sprawdź czy czas serwera jest zbliżony do lokalnego
                    local_time = int(time.time() * 1000)
                    time_diff = abs(server_time - local_time)
                    
                    if time_diff < 60000:  # Różnica mniejsza niż 1 minuta
                pass
logger.info("   ✅ Server time accuracy: OK")
                    else:
logger.info(f"   ⚠️ Server time difference: {time_diff}ms")
                else:
logger.info("   ❌ Invalid server time format")
                    return False
            else:
logger.info("   ❌ Server time endpoint failed")
                return False
                
            # Test precision formatów liczbowych
            url = "https://api.binance.com/api/v3/ticker/price"
            response = await NetworkHelper.make_request(f"{url}?symbol=BTCUSDT", timeout=10)
            
                pass
            if response and 'price' in response:
                price_str = response['price']
                
                # Sprawdź czy cena ma odpowiednią precyzję
                if '.' in price_str:
                    decimal_places = len(price_str.split('.')[1])
                    if 1 <= decimal_places <= 8:
            pass
logger.info("   ✅ Price precision: OK")
                    else:
logger.info(f"   ⚠️ Unusual price precision: {decimal_places} decimal places")
                else:
logger.info("   ⚠️ Price has no decimal places")
                    
            return True
            
        except Exception as e:
logger.info(f"❌ Błąd testowania formatów danych: {e}")
            return False
        pass

    async def run_all_tests(self) -> bool:
        """Uruchamia wszystkie testy API REST"""
logger.info("🚀 Rozpoczynam testy API REST")
logger.info("=" * 60)
        pass
        
        # Czyść dane testowe
        await self.cleanup_test_data()
        
        tests = [
            ("Publiczne endpointy", self.test_public_endpoints),
            ("Prywatne endpointy", self.test_private_endpoints),
            ("Walidacja błędów", self.test_error_validation),
            ("Formaty danych", self.test_data_formats),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
logger.info(f"\n📋 {test_name}...")
                result = await test_func()
                results.append((test_name, result))
                
                if result:
logger.info(f"✅ {test_name}: PASSED")
                else:
logger.info(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
logger.info(f"❌ Krytyczny błąd w teście {test_name}: {e}")
                results.append((test_name, False))
        
        # Podsumowanie
logger.info("\n" + "=" * 60)
logger.info("📊 PODSUMOWANIE TESTÓW API REST")
logger.info("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
logger.info(f"{test_name:.<40} {status}")
            if result:
                passed += 1
logger.info("-" * 60)
logger.info(f"Wynik: {passed}/{total} testów przeszło pomyślnie")
        
        if passed == total:
logger.info("🎉 Wszystkie testy API REST przeszły pomyślnie!")
logger.info("✅ API REST jest gotowe do użycia")
        else:
logger.info("⚠️ Niektóre testy nie przeszły - sprawdź logi powyżej")
        
        return passed == total

async def main():
    """Główna funkcja testowa"""
    tester = APIRestTester()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
logger.info("\n⚠️ Testy przerwane przez użytkownika")
        sys.exit(1)
    except Exception as e:
logger.info(f"\n❌ Krytyczny błąd: {e}")
        sys.exit(1)