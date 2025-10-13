"""
Unified Data Manager - central orchestrator with defensive imports.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

# Lazy imports inside methods to avoid hard failures on import time

class UnifiedDataManager:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.data_manager = None
        self.production_data_manager = None
        self.portfolio_manager = None
        self.market_data_manager = None
        self.trading_engine = None
        self.strategy_engine = None
        self.components_ready: Dict[str, bool] = {}
        self.last_updated: Optional[datetime] = None
        # --- UI callbacks registry for compatibility with IntegratedDataManager ---
        self.ui_callbacks: Dict[str, list] = {
            'portfolio_update': [],
            'system_status_update': [],
            'bot_status_update': [],
            'order_update': [],
            'price_update': [],
            'market_data_update': [],
            'ticker_update': [],
            'strategy_signal': [],
            'strategy_execution': []
        }

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize all components in a safe, step-by-step manner.
        """
        try:
            logging.getLogger(__name__).info("Initializing UnifiedDataManager...")

            # 1) DataManager
            try:
                from core.data_manager import DataManager
                self.data_manager = DataManager()
                if hasattr(self.data_manager, "ensure_initialized"):
                    await self.data_manager.ensure_initialized()
                self.components_ready["data_manager"] = True
                logging.getLogger(__name__).info("✅ DataManager initialized")
            except Exception:
                logging.getLogger(__name__).exception("DataManager init failed")
                self.components_ready["data_manager"] = False

            # 2) ProductionDataManager (conditional)
            try:
                production_mode = False
                if self.config_manager and hasattr(self.config_manager, "get_setting"):
                    production_mode = bool(self.config_manager.get_setting("app", "production_mode", False))
                if production_mode:
                    try:
                        # prefer a factory if provided
                        from core.integrated_data_manager import get_production_data_manager
                        self.production_data_manager = get_production_data_manager()
                    except Exception:
                        self.production_data_manager = None
                    if self.production_data_manager and hasattr(self.production_data_manager, "initialize"):
                        await self.production_data_manager.initialize()
                    self.components_ready["production_data_manager"] = True
                    logging.getLogger(__name__).info("✅ ProductionDataManager initialized")
                else:
                    self.components_ready["production_data_manager"] = False
            except Exception:
                logging.getLogger(__name__).exception("ProductionDataManager init failed")
                self.components_ready["production_data_manager"] = False

            # 3) PortfolioManager
            try:
                from core.portfolio_manager import PortfolioManager
                self.portfolio_manager = PortfolioManager(self.data_manager)
                self.components_ready["portfolio_manager"] = True
                logging.getLogger(__name__).info("✅ PortfolioManager initialized")
            except Exception:
                logging.getLogger(__name__).exception("PortfolioManager init failed")
                self.components_ready["portfolio_manager"] = False

            # 4) MarketDataManager
            try:
                from core.market_data_manager import MarketDataManager
                self.market_data_manager = MarketDataManager()
                if hasattr(self.market_data_manager, "start"):
                    await self.market_data_manager.start()
                self.components_ready["market_data_manager"] = True
                logging.getLogger(__name__).info("✅ MarketDataManager initialized")
            except Exception:
                logging.getLogger(__name__).exception("MarketDataManager init failed")
                self.components_ready["market_data_manager"] = False

            # 5) Trading engine marker (some apps init via BotManager)
            try:
                if config and config.get("enable_trading", False):
                    self.components_ready["trading_engine"] = True
                    logging.getLogger(__name__).info("✅ TradingEngine ready for initialization")
                else:
                    self.components_ready["trading_engine"] = False
            except Exception:
                logging.getLogger(__name__).exception("TradingEngine flag set failed")
                self.components_ready["trading_engine"] = False

            self.last_updated = datetime.now(timezone.utc)
            logging.getLogger(__name__).info("UnifiedDataManager initialized successfully")
            return True

        except Exception:
            logging.getLogger(__name__).exception("UnifiedDataManager.initialize fatal error")
            return False

    # === UI subscription compatibility methods ===
    def subscribe_to_ui_updates(self, event_type: str, callback):
        """Compatibility: allow UI to subscribe to updates via UnifiedDataManager."""
        try:
            if event_type not in self.ui_callbacks:
                # create bucket if unknown event type
                self.ui_callbacks[event_type] = []
            self.ui_callbacks[event_type].append(callback)
            logging.getLogger(__name__).info(f"UI subscribed to {event_type} updates (UDM)")
        except Exception:
            logging.getLogger(__name__).exception("subscribe_to_ui_updates failed in UnifiedDataManager")

    def unsubscribe_from_ui_updates(self, event_type: str, callback):
        """Compatibility: allow UI to unsubscribe from updates via UnifiedDataManager."""
        try:
            if event_type in self.ui_callbacks and callback in self.ui_callbacks[event_type]:
                self.ui_callbacks[event_type].remove(callback)
                logging.getLogger(__name__).info(f"UI unsubscribed from {event_type} updates (UDM)")
        except Exception:
            logging.getLogger(__name__).exception("unsubscribe_from_ui_updates failed in UnifiedDataManager")

    async def notify_ui_update(self, event_type: str, data: Any):
        """Notify all subscribers of a UI update. Accepts sync or async callbacks."""
        try:
            callbacks = self.ui_callbacks.get(event_type, [])
            for cb in list(callbacks):
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(data)
                    else:
                        result = cb(data)
                        if asyncio.iscoroutine(result):
                            await result
                except Exception:
                    logging.getLogger(__name__).exception(f"Error in UI callback for {event_type} (UDM)")
        except Exception:
            logging.getLogger(__name__).exception("notify_ui_update failed in UnifiedDataManager")


_GLOBAL_UDM = None

def get_unified_data_manager(config_manager=None):
    """Compatibility factory used by other modules."""
    global _GLOBAL_UDM
    if _GLOBAL_UDM is None:
        _GLOBAL_UDM = UnifiedDataManager(config_manager=config_manager)
    return _GLOBAL_UDM


class UnifiedSystemStatus:
    """Lightweight compatibility placeholder for status struct."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
