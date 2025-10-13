"""
Trading Engine - Silnik handlowy do komunikacji z giełdami
"""

import asyncio
import logging
import json
import hmac
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import requests

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

@dataclass
class OrderRequest:
    """Żądanie złożenia zlecenia"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good Till Canceled
    client_order_id: Optional[str] = None

@dataclass
class OrderResponse:
    """Odpowiedź na zlecenie"""
    order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    status: OrderStatus
    filled_quantity: float
    remaining_quantity: float
    average_price: Optional[float]
    commission: float
    commission_asset: str
    timestamp: datetime
    error_message: Optional[str] = None

@dataclass
class Balance:
    """Saldo na koncie"""
    asset: str
    free: float
    locked: float
    total: float

@dataclass
class Trade:
    """Wykonana transakcja"""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    commission_asset: str
    timestamp: datetime

class TradingEngine:
    """Silnik handlowy - komunikacja z giełdami, wykonywanie zleceń"""
    
    def __init__(self):
        self.exchanges = {}
        self.active_orders: Dict[str, OrderResponse] = {}
        self.trade_history: List[Trade] = []
        self.balances: Dict[str, Balance] = {}
        
        # Konfiguracja giełd
        self.exchange_configs = {
            'binance': {
                'name': 'Binance',
                'base_url': 'https://api.binance.com',
                'testnet_url': 'https://testnet.binance.vision',
                'enabled': False,
                'testnet': True,
                'api_key': '',
                'api_secret': ''
            },
            'bybit': {
                'name': 'Bybit',
                'base_url': 'https://api.bybit.com',
                'testnet_url': 'https://api-testnet.bybit.com',
                'enabled': False,
                'testnet': True,
                'api_key': '',
                'api_secret': ''
            }
        }
        
        # Tryb demo
        self.demo_mode = True
        self.demo_balance = {
            'USDT': Balance('USDT', 10000.0, 0.0, 10000.0),
            'BTC': Balance('BTC', 0.0, 0.0, 0.0),
            'ETH': Balance('ETH', 0.0, 0.0, 0.0)
        }
    
    async def initialize(self, exchange_configs: Dict[str, Dict[str, Any]] = None):
        """Inicjalizuje silnik handlowy"""
        try:
            if exchange_configs:
                self.exchange_configs.update(exchange_configs)
            
            # Sprawdź połączenia z giełdami
            for exchange_name, config in self.exchange_configs.items():
                if config.get('enabled', False):
                    success = await self._test_exchange_connection(exchange_name)
                    if success:
                        logger.info(f"Successfully connected to {exchange_name}")
                    else:
                        logger.warning(f"Failed to connect to {exchange_name}")
            
            logger.info("TradingEngine initialized")
            
        except Exception as e:
            logger.error(f"Error initializing TradingEngine: {e}")
    
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Składa zlecenie"""
        try:
            # Dodaj trace log przed składaniem zlecenia
            logger.info("TRACE: order.submitted - symbol=%s qty=%s type=%s" % (order_request.symbol, order_request.quantity, getattr(order_request.order_type,"value",order_request.order_type)))
            
            if self.demo_mode:
                # Demo mode: synthesize a realistic OrderResponse and register active orders
                order_id = f"demo_{int(time.time() * 1000)}"
                if order_request.order_type == OrderType.MARKET:
                    status = OrderStatus.FILLED
                    filled_quantity = float(order_request.quantity)
                    remaining_quantity = 0.0
                else:
                    status = OrderStatus.NEW
                    filled_quantity = 0.0
                    remaining_quantity = float(order_request.quantity)
                price = float(order_request.price or 0.0)
                resp = OrderResponse(
                    order_id=order_id,
                    client_order_id=order_request.client_order_id,
                    symbol=order_request.symbol,
                    side=order_request.side,
                    order_type=order_request.order_type,
                    quantity=float(order_request.quantity),
                    price=price,
                    status=status,
                    filled_quantity=filled_quantity,
                    remaining_quantity=remaining_quantity,
                    average_price=(price if status == OrderStatus.FILLED else None),
                    commission=0.0,
                    commission_asset="USDT",
                    timestamp=datetime.now(),
                    error_message=None,
                )
                if resp.status in (OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED):
                    self.active_orders[resp.order_id] = resp
                return resp
            
            # Wybierz giełdę (domyślnie Binance)
            exchange = 'binance'
            if self.exchange_configs[exchange].get('enabled', False):
                return await self._place_real_order(exchange, order_request)
            else:
                return await self._place_demo_order(order_request)
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return OrderResponse(
                order_id="",
                client_order_id=order_request.client_order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_request.price,
                status=OrderStatus.REJECTED,
                filled_quantity=0.0,
                remaining_quantity=order_request.quantity,
                average_price=None,
                commission=0.0,
                commission_asset="USDT",
                timestamp=datetime.now(),
                error_message=str(e)
            )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Anuluje zlecenie"""
        try:
            if self.demo_mode:
                # Demo mode: cancel locally stored order
                if order_id in self.active_orders:
                    order = self.active_orders[order_id]
                    order.status = OrderStatus.CANCELED
                    logger.info(f"Demo order canceled: {order_id}")
                    return True
                return False
            
            # Implementacja anulowania na prawdziwej giełdzie
            exchange = 'binance'
            if self.exchange_configs[exchange].get('enabled', False):
                return await self._cancel_real_order(exchange, order_id, symbol)
            else:
                return await self._cancel_demo_order(order_id)
                
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    async def submit_order(self, symbol: str, side: str, amount: float, 
                          price: Optional[float] = None, order_type: str = 'market',
                          **kwargs) -> Optional[OrderResponse]:
        """
        Consistent interface for order submission (compatible with base exchange)
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order quantity
            price: Order price (for limit orders)
            order_type: 'market', 'limit', 'stop_loss', 'take_profit'
            **kwargs: Additional parameters
            
        Returns:
            OrderResponse object or None if failed
        """
        try:
            # Convert string parameters to enums
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            # Map order type strings to enum
            order_type_map = {
                'market': OrderType.MARKET,
                'limit': OrderType.LIMIT,
                'stop_loss': OrderType.STOP_LOSS,
                'take_profit': OrderType.TAKE_PROFIT
            }
            order_type_enum = order_type_map.get(order_type.lower(), OrderType.MARKET)
            
            # Create OrderRequest
            order_request = OrderRequest(
                symbol=symbol,
                side=order_side,
                order_type=order_type_enum,
                quantity=amount,
                price=price,
                client_order_id=kwargs.get('client_order_id'),
                time_in_force=kwargs.get('time_in_force', 'GTC')
            )
            
            # Use existing place_order method
            return await self.place_order(order_request)
            
        except Exception as e:
            logger.error(f"Error in submit_order: {e}")
            return None
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderResponse]:
        """
        Get order status (consistent interface)
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            OrderResponse object or None if not found
        """
        try:
            # Check active orders first
            if order_id in self.active_orders:
                return self.active_orders[order_id]
            
            if self.demo_mode:
                return None  # Demo orders are stored in active_orders
            
            # For real orders, query the exchange
            exchange = 'binance'
            if self.exchange_configs[exchange].get('enabled', False):
                return await self._get_real_order_status(exchange, order_id, symbol)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """
        Get open orders (consistent interface)
        
        Args:
            symbol: Trading pair symbol (if None, all symbols)
            
        Returns:
            List of OrderResponse objects
        """
        try:
            open_orders = []
            
            for order_id, order in self.active_orders.items():
                # Filter by symbol if specified
                if symbol and order.symbol != symbol:
                    continue
                
                # Only include open orders
                if order.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]:
                    open_orders.append(order)
            
            return open_orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    

    
    async def get_balances(self) -> Dict[str, Balance]:
        """Pobiera salda konta"""
        try:
            if self.demo_mode:
                return self.demo_balance.copy()
            
            # Implementacja pobierania sald z prawdziwej giełdy
            exchange = 'binance'
            if self.exchange_configs[exchange].get('enabled', False):
                return await self._get_real_balances(exchange)
            else:
                return self.demo_balance.copy()
                
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
            return {}
    
    async def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Trade]:
        """Pobiera historię transakcji"""
        try:
            if symbol:
                return [trade for trade in self.trade_history if trade.symbol == symbol][-limit:]
            else:
                return self.trade_history[-limit:]
                
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
async def _place_demo_order(self, order_request: OrderRequest) -> OrderResponse:
    """Składa zlecenie w trybie demo"""
    try:
        order_id = f"demo_{int(time.time() * 1000)}"
        if order_request.order_type == OrderType.MARKET:
            status = OrderStatus.FILLED
            filled_quantity = float(order_request.quantity)
            remaining_quantity = 0.0
        else:
            status = OrderStatus.NEW
            filled_quantity = 0.0
            remaining_quantity = float(order_request.quantity)
        price = float(getattr(order_request, "price", 0.0) or 0.0)
        return OrderResponse(
            order_id=order_id,
            symbol=order_request.symbol,
            status=status,
            filled_quantity=filled_quantity,
            remaining_quantity=remaining_quantity,
            price=price,
            message="demo"
        )
    except Exception as e:
        logger.exception("Demo order failed")
        raise

    
    async def _cancel_demo_order(self, order_id: str) -> bool:
        """Anuluje zlecenie demo"""
        try:
            if order_id in self.active_orders:
                order = self.active_orders[order_id]
                order.status = OrderStatus.CANCELED
                logger.info(f"Demo order canceled: {order_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error canceling demo order: {e}")
            return False
    
    async def _test_exchange_connection(self, exchange_name: str) -> bool:
        """Testuje połączenie z giełdą"""
        try:
            config = self.exchange_configs[exchange_name]
            base_url = config['testnet_url'] if config.get('testnet', True) else config['base_url']
            
            if exchange_name == 'binance':
                url = f"{base_url}/api/v3/ping"
                response = requests.get(url, timeout=5)
                return response.status_code == 200
            
            return False
            
        except Exception as e:
            logger.error(f"Error testing connection to {exchange_name}: {e}")
            return False
    
    async def _place_real_order(self, exchange: str, order_request: OrderRequest) -> OrderResponse:
        """Składa rzeczywiste zlecenie na giełdzie"""
        # Implementacja będzie dodana w przyszłości
        logger.warning("Real order placement not implemented yet, using demo mode")
        return await self._place_demo_order(order_request)
    
    async def _cancel_real_order(self, exchange: str, order_id: str, symbol: str) -> bool:
        """Anuluje rzeczywiste zlecenie na giełdzie"""
        # Implementacja będzie dodana w przyszłości
        logger.warning("Real order cancellation not implemented yet")
        return False
    
    async def _get_real_order_status(self, exchange: str, order_id: str, symbol: str) -> Optional[OrderResponse]:
        """Pobiera status rzeczywistego zlecenia"""
        # Implementacja będzie dodana w przyszłości
        return None
    
    async def _get_real_balances(self, exchange: str) -> Dict[str, Balance]:
        """Pobiera rzeczywiste salda z giełdy"""
        # Implementacja będzie dodana w przyszłości
        return self.demo_balance.copy()


# Singleton instance
_trading_engine_instance = None

def get_trading_engine() -> TradingEngine:
    """Zwraca singleton instancję TradingEngine"""
    global _trading_engine_instance
    if _trading_engine_instance is None:
        _trading_engine_instance = TradingEngine()
    return _trading_engine_instance