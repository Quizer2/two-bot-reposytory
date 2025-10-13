"""
Portfolio Manager - Zarządzanie portfelem i obliczenia finansowe
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json

from .data_manager import DataManager, PortfolioData

logger = logging.getLogger(__name__)

@dataclass
class AssetPosition:
    """Pozycja w danym aktywie"""
    symbol: str
    amount: float
    average_price: float
    current_price: float
    value: float
    profit_loss: float
    profit_loss_percent: float
    last_updated: datetime

@dataclass
class PortfolioSummary:
    """Podsumowanie portfela"""
    total_value: float
    available_balance: float
    invested_amount: float
    total_profit_loss: float
    total_profit_loss_percent: float
    daily_change: float
    daily_change_percent: float
    positions: List[AssetPosition]
    last_updated: datetime

class PortfolioManager:
    """Manager portfela - oblicza wartości, zyski/straty, zarządza pozycjami"""
    
    def __init__(self, data_manager: Optional[DataManager] = None):
        # Jeśli nie podano data_manager, użyj domyślnego
        if data_manager is None:
            from .data_manager import get_data_manager
            data_manager = get_data_manager()
        
        self.data_manager = data_manager
        self.cache: Dict[str, Any] = {}
        self.cache_duration = timedelta(minutes=1)  # Częstsze odświeżanie dla danych portfela
        self.last_cache_update: Dict[str, datetime] = {}
    
    async def initialize(self):
        """Inicjalizuje PortfolioManager"""
        logger.info("PortfolioManager initialized successfully")
        
    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Pobiera pełne podsumowanie portfela"""
        try:
            cache_key = "portfolio_summary"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Pobierz dane z DataManager
            portfolio_data = await self.data_manager.get_portfolio_data()
            
            # Oblicz pozycje
            positions = await self._calculate_positions(portfolio_data.assets)
            
            # Oblicz zmiany dzienne
            daily_change, daily_change_percent = await self._calculate_daily_changes(positions)
            
            summary = PortfolioSummary(
                total_value=portfolio_data.total_value,
                available_balance=portfolio_data.available_balance,
                invested_amount=portfolio_data.invested_amount,
                total_profit_loss=portfolio_data.profit_loss,
                total_profit_loss_percent=portfolio_data.profit_loss_percent,
                daily_change=daily_change,
                daily_change_percent=daily_change_percent,
                positions=positions,
                last_updated=datetime.now()
            )
            
            self._update_cache(cache_key, summary)
            return summary
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return await self._get_default_portfolio_summary()
    
    async def _calculate_positions(self, assets: List[Dict[str, Any]]) -> List[AssetPosition]:
        """Oblicza pozycje dla każdego aktywa"""
        positions = []
        
        for asset in assets:
            try:
                symbol = asset.get('symbol', '')
                amount = float(asset.get('amount', 0))
                value = float(asset.get('value', 0))
                change_24h = float(asset.get('change_24h', 0))
                
                # Oblicz cenę bieżącą
                current_price = value / amount if amount > 0 else 0
                
                # Oblicz średnią cenę zakupu (przykładowa logika)
                average_price = current_price * (1 - change_24h / 100)
                
                # Oblicz zysk/stratę
                profit_loss = value - (amount * average_price)
                profit_loss_percent = (profit_loss / (amount * average_price) * 100) if amount * average_price > 0 else 0
                
                position = AssetPosition(
                    symbol=symbol,
                    amount=amount,
                    average_price=average_price,
                    current_price=current_price,
                    value=value,
                    profit_loss=profit_loss,
                    profit_loss_percent=profit_loss_percent,
                    last_updated=datetime.now()
                )
                
                positions.append(position)
                
            except Exception as e:
                logger.error(f"Error calculating position for asset {asset}: {e}")
                continue
        
        return positions
    
    async def _calculate_daily_changes(self, positions: List[AssetPosition]) -> Tuple[float, float]:
        """Oblicza dzienne zmiany portfela"""
        try:
            total_daily_change = sum(pos.value * pos.profit_loss_percent / 100 for pos in positions)
            total_value = sum(pos.value for pos in positions)
            
            daily_change_percent = (total_daily_change / total_value * 100) if total_value > 0 else 0
            
            return total_daily_change, daily_change_percent
            
        except Exception as e:
            logger.error(f"Error calculating daily changes: {e}")
            return 0.0, 0.0
    
    async def update_position(self, symbol: str, amount: float, price: float, transaction_type: str = "buy"):
        """Aktualizuje pozycję po transakcji"""
        try:
            # Pobierz obecne dane portfela
            portfolio_data = await self.data_manager.get_portfolio_data()
            
            # Znajdź aktywo lub stwórz nowe
            asset_found = False
            for asset in portfolio_data.assets:
                if asset['symbol'] == symbol:
                    if transaction_type == "buy":
                        # Dodaj do pozycji
                        old_amount = asset['amount']
                        old_value = asset['value']
                        new_amount = old_amount + amount
                        new_value = old_value + (amount * price)
                        
                        asset['amount'] = new_amount
                        asset['value'] = new_value
                    elif transaction_type == "sell":
                        # Odejmij z pozycji
                        asset['amount'] = max(0, asset['amount'] - amount)
                        asset['value'] = max(0, asset['value'] - (amount * price))
                    
                    asset_found = True
                    break
            
            if not asset_found and transaction_type == "buy":
                # Dodaj nowe aktywo
                new_asset = {
                    'symbol': symbol,
                    'amount': amount,
                    'value': amount * price,
                    'change_24h': 0.0
                }
                portfolio_data.assets.append(new_asset)
            
            # Aktualizuj całkowite wartości
            portfolio_data.total_value = sum(asset['value'] for asset in portfolio_data.assets) + portfolio_data.available_balance
            portfolio_data.invested_amount = sum(asset['value'] for asset in portfolio_data.assets)
            portfolio_data.last_updated = datetime.now()
            
            # Zapisz do bazy danych
            await self._save_portfolio_data(portfolio_data)
            
            # Wyczyść cache
            self._clear_cache()
            
            logger.info(f"Updated position for {symbol}: {transaction_type} {amount} at {price}")
            
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")
    
    async def _save_portfolio_data(self, portfolio_data: PortfolioData):
        """Zapisuje dane portfela do bazy"""
        try:
            # Tutaj powinna być implementacja zapisu do bazy
            # Na razie logujemy
            logger.info(f"Saving portfolio data: {portfolio_data.total_value}")
            
        except Exception as e:
            logger.error(f"Error saving portfolio data: {e}")
    
    async def _get_default_portfolio_summary(self) -> PortfolioSummary:
        """Zwraca domyślne podsumowanie portfela w przypadku błędu"""
        return PortfolioSummary(
            total_value=0.0,
            available_balance=0.0,
            invested_amount=0.0,
            total_profit_loss=0.0,
            total_profit_loss_percent=0.0,
            daily_change=0.0,
            daily_change_percent=0.0,
            positions=[],
            last_updated=datetime.now()
        )
    
    def _is_cache_valid(self, key: str) -> bool:
        """Sprawdza czy cache jest aktualny"""
        if key not in self.cache or key not in self.last_cache_update:
            return False
        
        return datetime.now() - self.last_cache_update[key] < self.cache_duration
    
    def _update_cache(self, key: str, data: Any):
        """Aktualizuje cache"""
        self.cache[key] = data
        self.last_cache_update[key] = datetime.now()
    
    def _clear_cache(self):
        """Czyści cache"""
        self.cache.clear()
        self.last_cache_update.clear()

# Globalna instancja PortfolioManager
_portfolio_manager = None

def get_portfolio_manager(data_manager: Optional[DataManager] = None) -> PortfolioManager:
    """
    Zwraca globalną instancję PortfolioManager (singleton)
    
    Args:
        data_manager: Manager danych (tylko przy pierwszym wywołaniu)
        
    Returns:
        Instancja PortfolioManager
    """
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = PortfolioManager(data_manager)
    return _portfolio_manager

def reset_portfolio_manager():
    """Resetuje globalną instancję PortfolioManager (do testów)"""
    global _portfolio_manager
    _portfolio_manager = None