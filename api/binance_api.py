"""
Binance API Integration Module

Obsługuje wszystkie endpointy API Binance zgodnie z wymaganiami:
- Publiczne WebSocket API
- REST API dla danych historycznych
- Dane świecowe w czasie rzeczywistym
"""

import asyncio
import json
import websockets
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import logging
from utils.net_wrappers import net_guard
from utils.http_logging import log_request

class BinanceAPI:
    """Klasa do obsługi API Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.ws_base_url = "wss://stream.binance.com:9443/ws"
        self.logger = logging.getLogger(__name__)
        self.websocket = None
        self.is_connected = False
        self.callbacks = {}
        
    @net_guard('api:get_klines')
    def get_klines(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 100) -> pd.DataFrame:
        """
        Pobiera dane świecowe z REST API
        
        Args:
            symbol: Para handlowa (np. BTCUSDT)
            interval: Interwał czasowy (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Liczba świec (max 1000)
        """
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'limit': limit
            }
            
            log_request(self.logger, 'GET', url, headers=None, params=params)
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Konwersja do DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Konwersja typów danych
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Pobrano {len(df)} świec dla {symbol}")
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania danych świecowych: {e}")
            return pd.DataFrame()
    
    @net_guard('api:get_24hr_ticker')
    def get_24hr_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """Pobiera statystyki 24h dla pary"""
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {'symbol': symbol.upper()}
            
            log_request(self.logger, 'GET', url, headers=None, params=params)
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania statystyk 24h: {e}")
            return {}
    
    @net_guard('api:get_orderbook')
    def get_orderbook(self, symbol: str = "BTCUSDT", limit: int = 100) -> Dict:
        """Pobiera księgę zleceń"""
        try:
            url = f"{self.base_url}/api/v3/depth"
            params = {
                'symbol': symbol.upper(),
                'limit': limit
            }
            
            log_request(self.logger, 'GET', url, headers=None, params=params)
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania księgi zleceń: {e}")
            return {}
    
    @net_guard('api:get_recent_trades')
    def get_recent_trades(self, symbol: str = "BTCUSDT", limit: int = 100) -> List[Dict]:
        """Pobiera ostatnie transakcje"""
        try:
            url = f"{self.base_url}/api/v3/trades"
            params = {
                'symbol': symbol.upper(),
                'limit': limit
            }
            
            log_request(self.logger, 'GET', url, headers=None, params=params)
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania ostatnich transakcji: {e}")
            return []
    
    async def connect_websocket(self, symbol: str = "BTCUSDT"):
        """Łączy się z WebSocket API dla danych w czasie rzeczywistym"""
        try:
            # Stream dla świec 1m i ticker
            streams = [
                f"{symbol.lower()}@kline_1m",
                f"{symbol.lower()}@ticker"
            ]
            
            ws_url = f"{self.ws_base_url}/{'/'.join(streams)}"
            
            self.websocket = await websockets.connect(ws_url, open_timeout=10, ping_interval=20, ping_timeout=10)
            self.is_connected = True
            
            self.logger.info(f"Połączono z WebSocket dla {symbol}")
            
            # Nasłuchuj wiadomości
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_websocket_message(data)
                except json.JSONDecodeError:
                    self.logger.error("Błąd dekodowania wiadomości WebSocket")
                    
        except Exception as e:
            self.logger.error(f"Błąd połączenia WebSocket: {e}")
            self.is_connected = False
    
    async def handle_websocket_message(self, data: Dict):
        """Obsługuje wiadomości z WebSocket"""
        try:
            if 'stream' in data:
                stream = data['stream']
                payload = data['data']
                
                if '@kline_' in stream:
                    # Dane świecowe
                    kline = payload['k']
                    if kline['x']:  # Świeca zamknięta
                        candle_data = {
                            'symbol': kline['s'],
                            'timestamp': datetime.fromtimestamp(kline['t'] / 1000),
                            'open': float(kline['o']),
                            'high': float(kline['h']),
                            'low': float(kline['l']),
                            'close': float(kline['c']),
                            'volume': float(kline['v'])
                        }
                        
                        # Wywołaj callback jeśli istnieje
                        if 'kline' in self.callbacks:
                            self.callbacks['kline'](candle_data)
                
                elif '@ticker' in stream:
                    # Dane ticker
                    ticker_data = {
                        'symbol': payload['s'],
                        'price': float(payload['c']),
                        'change': float(payload['P']),
                        'volume': float(payload['v'])
                    }
                    
                    # Wywołaj callback jeśli istnieje
                    if 'ticker' in self.callbacks:
                        self.callbacks['ticker'](ticker_data)
                        
        except Exception as e:
            self.logger.error(f"Błąd obsługi wiadomości WebSocket: {e}")
    
    def set_callback(self, event_type: str, callback: Callable):
        """Ustawia callback dla określonego typu wydarzenia"""
        self.callbacks[event_type] = callback
    
    async def disconnect_websocket(self):
        """Rozłącza WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.logger.info("Rozłączono WebSocket")
    
    @net_guard('api:get_exchange_info')
    def get_exchange_info(self) -> Dict:
        """Pobiera informacje o giełdzie"""
        try:
            url = f"{self.base_url}/api/v3/exchangeInfo"
            log_request(self.logger, 'GET', url, headers=None, params=None)
            response = requests.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania informacji o giełdzie: {e}")
            return {}
    
    @net_guard('api:get_server_time')
    def get_server_time(self) -> Dict:
        """Pobiera czas serwera"""
        try:
            url = f"{self.base_url}/api/v3/time"
            log_request(self.logger, 'GET', url, headers=None, params=None)
            response = requests.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania czasu serwera: {e}")
            return {}


# Singleton instance
binance_api = BinanceAPI()


def get_binance_api() -> BinanceAPI:
    """Zwraca instancję API Binance"""
    return binance_api