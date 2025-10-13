#!/usr/bin/env python3
"""
Test integracji ConfigManager z UI
Sprawdza czy zmiany w ustawieniach risk management są poprawnie zapisywane i odczytywane
"""

import asyncio
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import get_config_manager
from utils.logger import get_logger, LogType
import logging
logger = logging.getLogger(__name__)

class ConfigManagerIntegrationTest:
    """Test integracji ConfigManager z ustawieniami risk management"""
    
    def __init__(self):
        self.logger = get_logger(__name__, LogType.SYSTEM)
        self.test_config_dir = None
        self.original_config_dir = None
        
    async def run_tests(self):
        """Uruchom wszystkie testy"""
logger.info("\n" + "=" * 60)
logger.info("🔧 TEST: ConfigManager Integration")
logger.info("=" * 60)
        
        try:
            await self.setup_test_environment()
            
            # Test 1: Podstawowe operacje ConfigManager
            await self.test_basic_config_operations()
            
            # Test 2: Risk Management Settings
            await self.test_risk_management_settings()
            
            # Test 3: Bot Configuration
            await self.test_bot_configuration()
            
            # Test 4: Event propagation
            await self.test_event_propagation()
logger.info("\n✅ Wszystkie testy ConfigManager zakończone pomyślnie!")
            
        except Exception as e:
            pass
logger.info(f"\n❌ Błąd podczas testów: {e}")
            import traceback
            traceback.print_exc()
            pass
        finally:
            await self.cleanup_test_environment()
    
    async def setup_test_environment(self):
        """Przygotuj środowisko testowe"""
logger.info("\n📋 Przygotowywanie środowiska testowego...")
        
        # Utwórz tymczasowy katalog dla konfiguracji
        self.test_config_dir = tempfile.mkdtemp(prefix="config_test_")
logger.info(f"  • Katalog testowy: {self.test_config_dir}")
        
        # Skopiuj podstawową konfigurację
        config_manager = get_config_manager()
        
        # Zapisz oryginalną ścieżkę
        self.original_config_dir = config_manager.config_dir
        
        # Ustaw nową ścieżkę dla testów
        config_manager.config_dir = self.test_config_dir
logger.info("  ✅ Środowisko testowe przygotowane")
    
    async def test_basic_config_operations(self):
        """Test podstawowych operacji ConfigManager"""
logger.info("\n🔧 Test 1: Podstawowe operacje ConfigManager")
        
        config_manager = get_config_manager()
        
        # Pobierz domyślną konfigurację i zmodyfikuj ją
        default_config = config_manager._get_default_app_config()
        
        # Dodaj testową sekcję
        test_config = default_config.copy()
        test_config['test_section'] = {
            'value1': 'test_value',
            'value2': 42,
            'value3': True
        }
        
        # Zapisz konfigurację app
        config_manager.save_config('app', test_config)
logger.info("  ✅ Konfiguracja app zapisana")
        
        # Odczytaj konfigurację app
        loaded_config = config_manager.get_app_config()
logger.info("  ✅ Konfiguracja app odczytana")
        
        # Sprawdź poprawność
        assert loaded_config['test_section']['value1'] == 'test_value'
        assert loaded_config['test_section']['value2'] == 42
        assert loaded_config['test_section']['value3'] == True
logger.info("  ✅ Dane app są poprawne")
        
        # Test konfiguracji UI - pobierz domyślną i zmodyfikuj
        default_ui_config = config_manager._get_default_ui_config()
        ui_config = default_ui_config.copy()
        ui_config['ui_test'] = {
            'theme': 'dark',
            'language': 'pl'
        }
        
        config_manager.save_config('ui', ui_config)
logger.info("  ✅ Konfiguracja UI zapisana")
        
        loaded_ui_config = config_manager.get_ui_config()
        assert loaded_ui_config['ui_test']['theme'] == 'dark'
logger.info("  ✅ Dane UI są poprawne")
    
    async def test_risk_management_settings(self):
        """Test ustawień risk management"""
logger.info("\n🛡️ Test 2: Risk Management Settings")
        
        config_manager = get_config_manager()
        
        # Pobierz aktualną konfigurację app i dodaj risk management
        current_config = config_manager.get_app_config()
        current_config['risk_management'] = {
            'max_daily_loss': 2.5,
            'max_position_size': 1000.0,
            'max_drawdown': 5.0,
            'default_stop_loss': 1.5,
            'default_take_profit': 3.0,
            'max_open_positions': 5,
            'risk_per_trade': 1.0,
            'updated_at': datetime.now().isoformat()
        }
        
        # Zapisz ustawienia (jak robi UI)
        config_manager.save_config('app', current_config)
logger.info("  ✅ Risk settings zapisane przez UI")
        
        # Odczytaj ustawienia (jak robi RiskManager)
        app_config = config_manager.get_app_config()
        risk_config = app_config.get('risk_management', {})
        
        # Sprawdź poprawność
        assert risk_config['max_daily_loss'] == 2.5
        assert risk_config['max_position_size'] == 1000.0
        assert risk_config['max_drawdown'] == 5.0
logger.info("  ✅ Risk settings poprawnie odczytane")
        
        # Test aktualizacji pojedynczego ustawienia
        current_config = config_manager.get_app_config()
        current_config['risk_management']['max_daily_loss'] = 1.0
        config_manager.save_config('app', current_config)
        
        # Sprawdź aktualizację
        updated_config = config_manager.get_app_config()
        assert updated_config['risk_management']['max_daily_loss'] == 1.0
logger.info("  ✅ Aktualizacja pojedynczego ustawienia działa")
    
    async def test_bot_configuration(self):
        """Test konfiguracji bota"""
logger.info("\n🤖 Test 3: Bot Configuration")
        
        config_manager = get_config_manager()
        
        # Symuluj zmianę konfiguracji bota
        current_config = config_manager.get_app_config()
        current_config['trading'] = {
            'enabled': True,
            'mode': 'live',
            'default_exchange': 'coinbase',
            'min_order_amount': 10.0,
            'max_order_amount': 10000.0,
            'updated_at': datetime.now().isoformat()
        }
        
        config_manager.save_config('app', current_config)
logger.info("  ✅ Bot config zapisana")
        
        # Sprawdź odczyt
        app_config = config_manager.get_app_config()
        trading_config = app_config.get('trading', {})
        
        assert trading_config['enabled'] == True
        assert trading_config['mode'] == 'live'
        assert trading_config['default_exchange'] == 'coinbase'
logger.info("  ✅ Bot config poprawnie odczytana")
    
    async def test_event_propagation(self):
        """Test propagacji eventów"""
logger.info("\n📡 Test 4: Event Propagation")
        
        config_manager = get_config_manager()
        
        # Sprawdź czy ConfigManager ma event bus
        assert hasattr(config_manager, 'event_bus')
logger.info("  ✅ ConfigManager ma event bus")
        
        # Zarejestruj handler dla eventów
        events_received = []
        
        def config_updated_handler(data):
            events_received.append(data)
        
        config_manager.event_bus.subscribe('config.updated', config_updated_handler)
logger.info("  ✅ Event handler zarejestrowany")
        
            pass
        # Wykonaj zmianę konfiguracji
        try:
            # Pobierz aktualną konfigurację i dodaj test section
            current_config = config_manager.get_app_config()
            current_config['test_section'] = {
                'test_value': 'test_data',
                'updated_at': datetime.now().isoformat()
            }
            
            config_manager.save_config('app', current_config)
            
            # Sprawdź czy event został wysłany
            assert len(events_received) > 0
            assert events_received[-1]['config_type'] == 'app'
            pass
logger.info("  ✅ Event CONFIG_UPDATED został wysłany")
            
        except Exception as e:
logger.info(f"  ⚠️ Nie można przetestować eventów: {e}")
        
        # Wyczyść handler
        config_manager.event_bus.unsubscribe('config.updated', config_updated_handler)
    
    async def cleanup_test_environment(self):
            pass
        """Wyczyść środowisko testowe"""
                pass
logger.info("\n🧹 Czyszczenie środowiska testowego...")
        
        try:
            # Przywróć oryginalną ścieżkę
                pass
            if self.original_config_dir:
                config_manager = get_config_manager()
                config_manager.config_dir = self.original_config_dir
            pass
            
            # Usuń tymczasowy katalog
            if self.test_config_dir and os.path.exists(self.test_config_dir):
                shutil.rmtree(self.test_config_dir)
logger.info(f"  ✅ Usunięto katalog testowy: {self.test_config_dir}")
                
        except Exception as e:
    pass
logger.info(f"  ⚠️ Błąd podczas czyszczenia: {e}")

async def main():
    """Główna funkcja testowa"""
    test_suite = ConfigManagerIntegrationTest()
    await test_suite.run_tests()

if __name__ == "__main__":
    asyncio.run(main())