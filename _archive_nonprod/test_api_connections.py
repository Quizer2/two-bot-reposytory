"""
Skrypt testowy do sprawdzenia połączeń z API giełd

Testuje czy aplikacja może się połączyć z różnymi giełdami
i pobrać podstawowe dane.
"""

import asyncio
import sys
import os
from pathlib import Path

# Dodaj ścieżkę do modułów
sys.path.append(str(Path(__file__).parent))

from app.production_data_manager import ProductionDataManager
from app.api_config_manager import get_api_config_manager
from utils.logger import get_logger, LogType
import logging
logger = logging.getLogger(__name__)


async def test_production_manager():
    """Testuje Production Data Manager"""
    logger = get_logger("test_api", LogType.SYSTEM)
logger.info("=== Test Production Data Manager ===")
    
    try:
        # Inicjalizuj Production Manager
        manager = ProductionDataManager()
logger.info("✓ Production Data Manager utworzony")
        
        # Inicjalizuj połączenia
        await manager.initialize()
logger.info("✓ Production Data Manager zainicjalizowany")
        
        # Test połączenia z giełdą (bez API kluczy - tylko publiczne dane)
logger.info("\n--- Test publicznych danych ---")
        
        # Test ceny BTC/USDT
logger.info("Pobieranie ceny BTC/USDT...")
        price = await manager.get_real_price("BTC/USDT")
        
        if price:
            pass
logger.info(f"✓ Cena BTC/USDT: ${price:,.2f}")
            pass
        else:
logger.info("✗ Nie udało się pobrać ceny BTC/USDT")
        
        # Test danych OHLCV
logger.info("\nPobieranie danych OHLCV dla BTC/USDT...")
        ohlcv_data = await manager.get_real_ohlcv("BTC/USDT", "1h", 10)
            pass
        
        if ohlcv_data is not None and not ohlcv_data.empty:
            pass
logger.info(f"✓ Pobrano {len(ohlcv_data)} świec OHLCV")
logger.info(f"  Ostatnia cena zamknięcia: ${ohlcv_data['close'].iloc[-1]:,.2f}")
        else:
logger.info("✗ Nie udało się pobrać danych OHLCV")
        
        # Test tickerów
            pass
logger.info("\nPobieranie tickerów...")
        tickers = await manager.get_real_tickers()
                pass
                    pass
        
            pass
        if tickers:
logger.info(f"✓ Pobrano {len(tickers)} tickerów")
            # Pokaż kilka przykładów
            for i, (symbol, data) in enumerate(list(tickers.items())[:5]):
                if 'last' in data and data['last']:
logger.info(f"  {symbol}: ${data['last']:,.4f}")
        else:
                pass
logger.info("✗ Nie udało się pobrać tickerów")
                pass
        
            pass
        # Test połączenia z giełdą
logger.info("\n--- Test połączenia z giełdą ---")
        try:
            connection_status = await manager.test_connection_async()
        pass
            
            if connection_status:
logger.info("✓ Połączenie z giełdą działa")
            else:
logger.info("✗ Problemy z połączeniem")
        except Exception as e:
logger.info(f"✗ Błąd podczas testu: {e}")
logger.info("\n=== Test zakończony ===")
        return True
        pass
        
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}")
logger.info(f"✗ Błąd podczas testu: {e}")
        return False


def test_api_config_manager():
    """Testuje API Config Manager"""
logger.info("\n=== Test API Config Manager ===")
    
    try:
        # Inicjalizuj API Config Manager
        api_manager = get_api_config_manager()
logger.info("✓ API Config Manager zainicjalizowany")
        
        # Sprawdź dostępne giełdy
            pass
        exchanges = api_manager.get_all_exchanges()
logger.info(f"✓ Dostępne giełdy: {', '.join(exchanges)}")
        
        # Sprawdź włączone giełdy
        enabled = api_manager.get_enabled_exchanges()
logger.info(f"✓ Włączone giełdy: {', '.join(enabled) if enabled else 'Brak'}")
        
        # Sprawdź czy gotowe do produkcji
        ready = api_manager.is_production_ready()
        pass
logger.info(f"✓ Gotowe do produkcji: {'Tak' if ready else 'Nie'}")
        
        # Sprawdź konfigurację dla każdej giełdy
        for exchange in exchanges:
            config = api_manager.get_exchange_config(exchange)
            valid = api_manager.validate_exchange_config(exchange)
            enabled = config.get('enabled', False) if config else False
            
            status = "✓" if valid else "✗"
logger.info(f"  {exchange}: {status} {'Włączona' if enabled else 'Wyłączona'}")
logger.info("=== Test API Config Manager zakończony ===")
        return True
        
    except Exception as e:
logger.info(f"✗ Błąd podczas testu API Config Manager: {e}")
        return False

        pass

async def main():
    """Główna funkcja testowa"""
logger.info("Rozpoczynam testy połączeń API...\n")
    
        pass
    # Test API Config Manager
    config_test = test_api_config_manager()
    
    # Test Production Data Manager
    production_test = await test_production_manager()
    pass
logger.info(f"\n=== PODSUMOWANIE ===")
logger.info(f"API Config Manager: {'✓ OK' if config_test else '✗ BŁĄD'}")
logger.info(f"Production Data Manager: {'✓ OK' if production_test else '✗ BŁĄD'}")
    
    if config_test and production_test:
logger.info("\n🎉 Wszystkie testy przeszły pomyślnie!")
logger.info("\nAby przejść do trybu produkcyjnego:")
logger.info("1. Ustaw production_mode: true w config/app_config.json")
logger.info("2. Skonfiguruj klucze API w ustawieniach aplikacji")
logger.info("3. Uruchom aplikację ponownie")
    else:
logger.info("\n⚠️  Niektóre testy nie przeszły. Sprawdź logi powyżej.")
    
    return config_test and production_test


if __name__ == "__main__":
    # Uruchom testy
    result = asyncio.run(main())
    sys.exit(0 if result else 1)