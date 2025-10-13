"""
Base Bot - Bazowa klasa dla wszystkich botów tradingowych
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional, Any

from utils.logger import get_logger
import logging
logger = logging.getLogger(__name__)

class BaseBot(ABC):
    """Bazowa klasa dla wszystkich botów tradingowych"""
    
    def __init__(self, pair: str, db_manager, risk_manager, notification_manager, 
                 bot_id: Optional[int] = None):
        """
        Inicjalizacja bazowego bota
        
        Args:
            pair: Para handlowa (np. 'BTC/USDT')
            db_manager: Manager bazy danych
            risk_manager: Manager zarządzania ryzykiem
            notification_manager: Manager powiadomień
            bot_id: ID bota w bazie danych
        """
        self.pair = pair
        self.db_manager = db_manager
        self.risk_manager = risk_manager
        self.notification_manager = notification_manager
        self.bot_id = bot_id
        
        # Stan bota
        self.is_running = False
        self.last_activity = datetime.now()
        self.bot_type = "base"
        
        # Exchange adapter (będzie ustawiony przez BotManager)
        self.exchange = None
        
        # Logger
        self.logger = get_logger(f"BaseBot-{self.bot_id}")
        
        # Statystyki
        self.statistics = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'win_rate': 0.0,
            'start_time': datetime.now(),
            'last_trade_time': None
        }
    
    @abstractmethod
    async def run(self):
        """Główna pętla bota - musi być zaimplementowana w klasach pochodnych"""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict:
        """Pobranie statystyk bota - musi być zaimplementowana w klasach pochodnych"""
        pass
    
    async def start(self):
        """Uruchomienie bota"""
        if self.is_running:
            self.logger.warning("Bot już działa")
            return
        
        self.logger.info(f"Uruchamianie bota {self.bot_type} dla {self.pair}")
        self.is_running = True
        self.last_activity = datetime.now()
        
        try:
            await self.run()
        except Exception as e:
            self.logger.error(f"Błąd podczas działania bota: {e}")
            raise
        finally:
            self.is_running = False
    
    async def stop(self):
        """Zatrzymanie bota"""
        self.logger.info(f"Zatrzymywanie bota {self.bot_type}")
        self.is_running = False
    
    async def pause(self):
        """Wstrzymanie bota"""
        self.logger.info(f"Wstrzymywanie bota {self.bot_type}")
        self.is_running = False
    
    async def resume(self):
        """Wznowienie bota"""
        self.logger.info(f"Wznawianie bota {self.bot_type}")
        await self.start()
    
    def set_exchange(self, exchange):
        """Ustawienie adaptera giełdy"""
        self.exchange = exchange
        self.logger.info(f"Ustawiono adapter giełdy: {exchange.__class__.__name__}")
    
    async def update_activity(self):
        """Aktualizacja czasu ostatniej aktywności"""
        self.last_activity = datetime.now()
    
    async def log_trade(self, trade_data: Dict):
        """Zapisanie informacji o transakcji"""
        try:
            await self.update_activity()
            
            # Aktualizacja statystyk
            self.statistics['total_trades'] += 1
            self.statistics['last_trade_time'] = datetime.now()
            
            if trade_data.get('status') == 'filled':
                self.statistics['successful_trades'] += 1
                
                # Obliczenie P&L jeśli dostępne
                pnl = trade_data.get('pnl', 0)
                if pnl > 0:
                    self.statistics['total_profit'] += pnl
                elif pnl < 0:
                    self.statistics['total_loss'] += abs(pnl)
            else:
                self.statistics['failed_trades'] += 1
            
            # Obliczenie win rate
            if self.statistics['total_trades'] > 0:
                self.statistics['win_rate'] = (
                    self.statistics['successful_trades'] / self.statistics['total_trades']
                ) * 100
            
            # Zapisanie w bazie danych
            if self.bot_id:
                await self.db_manager.add_order(
                    bot_id=self.bot_id,
                    exchange_order_id=trade_data.get('order_id'),
                    side=trade_data.get('side'),
                    amount=trade_data.get('amount'),
                    price=trade_data.get('price'),
                    status=trade_data.get('status')
                )
            
            self.logger.info(f"Zarejestrowano transakcję: {trade_data}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas rejestrowania transakcji: {e}")
    
    async def log_error(self, error_message: str, error_type: str = "error"):
        """Zapisanie błędu w logach"""
        try:
            await self.update_activity()
            
            if self.bot_id:
                await self.db_manager.add_log(
                    bot_id=self.bot_id,
                    log_type=error_type,
                    message=error_message
                )
            
            # Wysłanie powiadomienia o błędzie
            await self.notification_manager.send_error_notification(
                self.bot_id, error_message
            )
            
            self.logger.error(error_message)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania błędu: {e}")
    
    async def log_info(self, message: str):
        """Zapisanie informacji w logach"""
        try:
            await self.update_activity()
            
            if self.bot_id:
                await self.db_manager.add_log(
                    bot_id=self.bot_id,
                    log_type="info",
                    message=message
                )
            
            self.logger.info(message)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania informacji: {e}")
    
    async def check_balance(self, currency: str) -> float:
        """Sprawdzenie salda dla danej waluty"""
        try:
            if not self.exchange:
                self.logger.error("Brak adaptera giełdy")
                return 0.0
            
            balance = await self.exchange.get_balance(currency)
            return balance
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania salda {currency}: {e}")
            return 0.0
    
    async def get_current_price(self) -> Optional[float]:
        """Pobranie aktualnej ceny dla pary"""
        try:
            if not self.exchange:
                self.logger.error("Brak adaptera giełdy")
                return None
            
            price = await self.exchange.get_current_price(self.pair)
            return price
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania ceny dla {self.pair}: {e}")
            return None
    
    async def create_order(self, side: str, amount: float, order_type: str = "market", 
                          price: Optional[float] = None) -> Optional[Dict]:
        """Utworzenie zlecenia"""
        try:
            if not self.exchange:
                self.logger.error("Brak adaptera giełdy")
                return None
            
            # Sprawdzenie zarządzania ryzykiem
            if side == 'buy':
                cost = amount * (price or await self.get_current_price() or 0)
                balance = await self.check_balance('USDT')  # Zakładamy USDT jako walutę bazową
                
                if not await self.risk_manager.check_position_size_limit(
                    self.bot_id, cost, balance
                ):
                    await self.log_error("Zlecenie odrzucone przez zarządzanie ryzykiem")
                    return None
            
            # Trace log przed składaniem zlecenia
            logger.info(f"TRACE: order.submitted - symbol={self.pair}, side={side}, amount={amount}, type={order_type}, strategy={self.bot_type}")
            
            # Utworzenie zlecenia
            if order_type == "market":
                order = await self.exchange.create_market_order(
                    pair=self.pair,
                    side=side,
                    amount=amount
                )
            else:
                order = await self.exchange.create_limit_order(
                    pair=self.pair,
                    side=side,
                    amount=amount,
                    price=price
                )
            
            if order:
                # Rejestracja transakcji
                await self.log_trade({
                    'order_id': order.get('id'),
                    'side': side,
                    'amount': amount,
                    'price': order.get('price'),
                    'status': order.get('status'),
                    'type': order_type
                })
            
            return order
            
        except Exception as e:
            await self.log_error(f"Błąd podczas tworzenia zlecenia: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Anulowanie zlecenia"""
        try:
            if not self.exchange:
                self.logger.error("Brak adaptera giełdy")
                return False
            
            result = await self.exchange.cancel_order(order_id)
            
            if result:
                await self.log_info(f"Anulowano zlecenie {order_id}")
                return True
            else:
                await self.log_error(f"Nie udało się anulować zlecenia {order_id}")
                return False
                
        except Exception as e:
            await self.log_error(f"Błąd podczas anulowania zlecenia {order_id}: {e}")
            return False
    
    async def get_open_orders(self) -> list:
        """Pobranie otwartych zleceń"""
        try:
            if not self.exchange:
                self.logger.error("Brak adaptera giełdy")
                return []
            
            orders = await self.exchange.get_open_orders(self.pair)
            return orders or []
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania otwartych zleceń: {e}")
            return []
    
    async def get_trade_history(self, limit: int = 100) -> list:
        """Pobranie historii transakcji"""
        try:
            if not self.exchange:
                self.logger.error("Brak adaptera giełdy")
                return []
            
            trades = await self.exchange.get_trade_history(self.pair, limit)
            return trades or []
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania historii transakcji: {e}")
            return []
    
    def get_basic_statistics(self) -> Dict:
        """Pobranie podstawowych statystyk bota"""
        uptime = datetime.now() - self.statistics['start_time']
        
        return {
            'bot_id': self.bot_id,
            'bot_type': self.bot_type,
            'pair': self.pair,
            'is_running': self.is_running,
            'uptime_seconds': uptime.total_seconds(),
            'last_activity': self.last_activity.isoformat(),
            'total_trades': self.statistics['total_trades'],
            'successful_trades': self.statistics['successful_trades'],
            'failed_trades': self.statistics['failed_trades'],
            'win_rate': self.statistics['win_rate'],
            'total_profit': self.statistics['total_profit'],
            'total_loss': self.statistics['total_loss'],
            'net_profit': self.statistics['total_profit'] - self.statistics['total_loss'],
            'last_trade_time': self.statistics['last_trade_time'].isoformat() if self.statistics['last_trade_time'] else None
        }
    
    async def validate_parameters(self, parameters: Dict) -> bool:
        """Walidacja parametrów bota - może być nadpisana w klasach pochodnych"""
        return True
    
    async def update_parameters(self, parameters: Dict):
        """Aktualizacja parametrów bota - może być nadpisana w klasach pochodnych"""
        pass
    
    def __str__(self):
        return f"{self.bot_type.upper()}Bot(id={self.bot_id}, pair={self.pair}, running={self.is_running})"
    
    def __repr__(self):
        return self.__str__()