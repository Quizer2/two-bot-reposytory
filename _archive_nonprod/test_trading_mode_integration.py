#!/usr/bin/env python3
"""
Test integracji Trading Mode Manager z powiadomieniami
"""

import asyncio
import sys
import os

# Dodaj ścieżkę do głównego katalogu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.trading_mode_manager import TradingModeManager, TradingMode
from utils.config_manager import get_config_manager
from utils.logger import get_logger
import logging
logger = logging.getLogger(__name__)

async def test_trading_mode_integration():
    """Test integracji Trading Mode Manager"""
    logger = get_logger("test_trading_mode")
    
    try:
        logger.info("🧪 Rozpoczęcie testu integracji Trading Mode Manager...")
        
        # Inicjalizuj Trading Mode Manager
        config = get_config_manager()
        
        # Inicjalizuj IntegratedDataManager (wymagany przez TradingModeManager)
        try:
            from core.integrated_data_manager import get_integrated_data_manager
            data_manager = get_integrated_data_manager()
        except ImportError:
            # Fallback - użyj None jeśli IntegratedDataManager nie jest dostępny
            data_manager = None
        
        trading_manager = TradingModeManager(config, data_manager)
        
        # Inicjalizuj manager
        success = await trading_manager.initialize()
        if not success:
            logger.error("❌ Nie udało się zainicjalizować Trading Mode Manager")
            return False
        
        logger.info(f"✅ Trading Mode Manager zainicjalizowany w trybie: {trading_manager.current_mode.value}")
        
        # Test 1: Sprawdź aktualny tryb
        current_mode = trading_manager.get_current_mode()
        logger.info(f"📊 Aktualny tryb: {current_mode.value}")
        
        # Test 2: Przełącz na Live Trading
        logger.info("🔄 Przełączanie na Live Trading...")
        success = await trading_manager.switch_mode(TradingMode.LIVE)
        if success:
            logger.info("✅ Przełączono na Live Trading")
        else:
            logger.warning("⚠️ Nie udało się przełączyć na Live Trading (może brakować konfiguracji API)")
        
        # Test 3: Przełącz z powrotem na Paper Trading
        logger.info("🔄 Przełączanie z powrotem na Paper Trading...")
        success = await trading_manager.switch_mode(TradingMode.PAPER)
        if success:
            logger.info("✅ Przełączono na Paper Trading")
        else:
            logger.error("❌ Nie udało się przełączyć na Paper Trading")
            return False
        
        # Test 4: Sprawdź czy tryb został zapisany w konfiguracji
        saved_mode = config.get_setting('app', 'trading.default_mode', 'paper')
        logger.info(f"💾 Tryb zapisany w konfiguracji: {saved_mode}")
        
        # Test 5: Sprawdź salda Paper Trading
        balances = await trading_manager.get_current_balances()
        logger.info(f"💰 Salda Paper Trading: {len(balances)} walut")
        
        logger.info("🎉 Test integracji Trading Mode Manager zakończony pomyślnie!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Błąd podczas testu integracji: {e}")
        return False

async def main():
    """Główna funkcja testowa"""
    success = await test_trading_mode_integration()
    if success:
        pass
logger.info("✅ Wszystkie testy przeszły pomyślnie!")
        sys.exit(0)
        pass
    else:
logger.info("❌ Niektóre testy nie powiodły się!")
        sys.exit(1)
    pass

if __name__ == "__main__":
    asyncio.run(main())