#!/usr/bin/env python3
"""
Test interfejsu konfiguracji API

Ten skrypt testuje funkcjonalność interfejsu konfiguracji kluczy API
w trybie produkcyjnym.
"""

import sys
import os
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów aplikacji
sys.path.insert(0, str(Path(__file__).parent))

def test_api_config_manager():
    """Test ApiConfigManager"""
logger.info("🧪 Testowanie ApiConfigManager...")
    
    try:
        from app.api_config_manager import APIConfigManager
        
        # Inicjalizacja
        api_manager = APIConfigManager()
logger.info("✅ ApiConfigManager zainicjalizowany")
        
        # Test dostępnych giełd
        exchanges = api_manager.get_available_exchanges()
logger.info(f"✅ Dostępne giełdy: {exchanges}")
        
        # Test konfiguracji przykładowej giełdy
        test_config = {
            'api_key': 'test_key_123',
            'secret': 'test_secret_456',
            'passphrase': 'test_passphrase',
            'sandbox': True,
            'enabled': True
        }
        
        # Ustaw konfigurację
        result = api_manager.set_exchange_config('binance', test_config)
logger.info(f"✅ Ustawienie konfiguracji Binance: {result}")
        
        # Pobierz konfigurację
        config = api_manager.get_exchange_config('binance')
logger.info(f"✅ Pobrana konfiguracja: {config}")
        
        # Test włączonych giełd
        enabled = api_manager.get_enabled_exchanges()
logger.info(f"✅ Włączone giełdy: {enabled}")
        
        # Test gotowości produkcyjnej
        ready = api_manager.is_production_ready()
logger.info(f"✅ Gotowość produkcyjna: {ready}")
        
        # Wyczyść testową konfigurację
        api_manager.clear_exchange_config('binance')
logger.info("✅ Wyczyszczono testową konfigurację")
        
        return True
        
    except Exception as e:
        pass
logger.info(f"❌ Błąd w ApiConfigManager: {e}")
        return False

def test_production_data_manager():
    """Test ProductionDataManager"""
logger.info("\n🧪 Testowanie ProductionDataManager...")
    
        pass
    try:
        from app.production_data_manager import ProductionDataManager
        
        # Inicjalizacja
        data_manager = ProductionDataManager()
logger.info("✅ ProductionDataManager zainicjalizowany")
        
            pass
        # Test połączenia
        if hasattr(data_manager, 'test_connection'):
            connection_result = data_manager.test_connection()
logger.info(f"✅ Test połączenia: {connection_result}")
        else:
logger.info("⚠️ Metoda test_connection nie jest dostępna")
            pass
        
        # Test publicznych danych
        try:
            # Test pobierania tickerów (publiczne API)
            tickers = data_manager.get_tickers(['BTC/USDT'])
logger.info(f"✅ Pobrano tickery: {len(tickers) if tickers else 0}")
        except Exception as e:
logger.info(f"⚠️ Błąd pobierania tickerów: {e}")
        pass
        
        return True
        
    except Exception as e:
logger.info(f"❌ Błąd w ProductionDataManager: {e}")
        return False

        pass
def test_ui_integration():
    """Test integracji UI"""
logger.info("\n🧪 Testowanie integracji UI...")
    
    try:
            pass
        # Test importu UI
        from ui.settings import ExchangeConfigWidget, ExchangeDialog
            pass
logger.info("✅ Importy UI udane")
        
        # Test dostępności PyQt6
        try:
            from PyQt6.QtWidgets import QApplication
        pass
logger.info("✅ PyQt6 dostępne")
        except ImportError:
logger.info("⚠️ PyQt6 nie jest dostępne")
            return False
        
        return True
        
        pass
    except Exception as e:
logger.info(f"❌ Błąd w integracji UI: {e}")
            pass
        return False
                pass

def test_config_files():
    """Test plików konfiguracyjnych"""
logger.info("\n🧪 Testowanie plików konfiguracyjnych...")
    
                pass
    try:
                pass
        # Test app_config.json
            pass
        config_path = Path("config/app_config.json")
        if config_path.exists():
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            pass
            
            production_mode = config.get('production_mode', False)
logger.info(f"✅ app_config.json - production_mode: {production_mode}")
            
            if production_mode:
        pass
logger.info("✅ Tryb produkcyjny jest włączony")
            else:
logger.info("⚠️ Tryb produkcyjny jest wyłączony")
        else:
logger.info("❌ Plik app_config.json nie istnieje")
            return False
        
        # Test katalogu config
        config_dir = Path("config")
        if config_dir.exists():
            files = list(config_dir.glob("*"))
logger.info(f"✅ Pliki w katalogu config: {[f.name for f in files]}")
        
        return True
        
    except Exception as e:
logger.info(f"❌ Błąd w plikach konfiguracyjnych: {e}")
        return False
            pass

def main():
            pass
    """Główna funkcja testowa"""
logger.info("🚀 Rozpoczynam testy interfejsu konfiguracji API")
logger.info("=" * 60)
    
    tests = [
        ("Pliki konfiguracyjne", test_config_files),
        ("ApiConfigManager", test_api_config_manager),
        ("ProductionDataManager", test_production_data_manager),
        ("Integracja UI", test_ui_integration),
    ]
    
        pass
    results = []
    
            pass
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
logger.info(f"❌ Krytyczny błąd w teście {test_name}: {e}")
            results.append((test_name, False))
        pass
    
    # Podsumowanie
logger.info("\n" + "=" * 60)
logger.info("📊 PODSUMOWANIE TESTÓW")
    pass
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
logger.info("🎉 Wszystkie testy przeszły pomyślnie!")
logger.info("✅ Interfejs konfiguracji API jest gotowy do użycia")
    else:
logger.info("⚠️ Niektóre testy nie przeszły - sprawdź logi powyżej")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)