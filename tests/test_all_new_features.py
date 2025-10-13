#!/usr/bin/env python3
"""
Główny plik testowy dla wszystkich nowych funkcji

Uruchamia testy dla:
- Strategii Swing Trading
- Strategii Arbitrage  
- Nowych giełd (Kraken, Bitfinex)
- Integracji z istniejącym systemem
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Dodaj ścieżkę do głównego katalogu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów testowych
from test_swing_strategy import run_swing_strategy_tests
from test_arbitrage_strategy import run_arbitrage_strategy_tests
from test_new_exchanges import run_new_exchanges_tests
import logging
logger = logging.getLogger(__name__)


class TestRunner:
    __test__ = False
    """Klasa do uruchamiania i raportowania testów"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def start_testing(self):
        """Rozpocznij sesję testową"""
        self.start_time = time.time()
        logger.info("=" * 80)
        logger.info("🚀 URUCHAMIANIE TESTÓW NOWYCH FUNKCJI")
        logger.info("=" * 80)
        logger.info(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🐍 Python: {sys.version}")
        logger.info(f"📁 Katalog: {os.getcwd()}")
        logger.info("=" * 80)
    
    def end_testing(self):
        """Zakończ sesję testową"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info("\n" + "=" * 80)
        logger.info("📊 PODSUMOWANIE TESTÓW")
        logger.info("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        failed_tests = total_tests - passed_tests
        logger.info(f"⏱️  Czas wykonania: {duration:.2f} sekund")
        logger.info(f"📈 Łącznie testów: {total_tests}")
        logger.info(f"✅ Zakończone pomyślnie: {passed_tests}")
        logger.info(f"❌ Nieudane: {failed_tests}")
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0.0
        logger.info(f"📊 Wskaźnik sukcesu: {success_rate:.1f}%")
        logger.info("\n📋 Szczegóły:")
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {status} {test_name}")
        
        if failed_tests == 0:
            logger.info("\n🎉 Wszystkie testy zakończone pomyślnie!")
            logger.info("🚀 Nowe funkcje są gotowe do użycia!")
        else:
            logger.info(f"\n⚠️  {failed_tests} testów nie powiodło się.")
            logger.info("🔧 Sprawdź logi powyżej i popraw błędy.")
            logger.info("=" * 80)
    
    async def run_test_suite(self, test_name, test_function):
        """Uruchom pojedynczy zestaw testów"""
        logger.info(f"\n🔄 Uruchamianie: {test_name}")
        logger.info("-" * 60)
        try:
            result = await test_function()
            self.results[test_name] = bool(result)
            if result:
                logger.info(f"✅ {test_name}: ZAKOŃCZONE POMYŚLNIE")
            else:
                logger.info(f"❌ {test_name}: NIEUDANE")
        except Exception as e:
            logger.info(f"💥 {test_name}: BŁĄD KRYTYCZNY")
            logger.info(f"   Szczegóły: {str(e)}")
            self.results[test_name] = False
        finally:
            logger.info("-" * 60)


async def run_comprehensive_tests():
    """Uruchom wszystkie testy nowych funkcji"""
    
    runner = TestRunner()
    runner.start_testing()
    
    # Lista testów do uruchomienia
    test_suites = [
        ("Strategia Swing Trading", run_swing_strategy_tests),
        ("Strategia Arbitrage", run_arbitrage_strategy_tests),
        ("Nowe Giełdy (Kraken & Bitfinex)", run_new_exchanges_tests),
    ]
    
    # Uruchom wszystkie testy
    for test_name, test_function in test_suites:
        await runner.run_test_suite(test_name, test_function)
        
        # Krótka przerwa między testami
        await asyncio.sleep(1)
    
    # Zakończ i pokaż podsumowanie
    runner.end_testing()
    
    # Zwróć wynik ogólny
    return all(runner.results.values())


async def run_quick_validation():
    """Szybka walidacja podstawowych funkcji"""
    logger.info("\n🔍 SZYBKA WALIDACJA PODSTAWOWYCH FUNKCJI")
    logger.info("=" * 50)
    
    validation_results = {}
    
    # Test 1: Import strategii
    try:
        from app.strategy.swing import SwingStrategy
        from app.strategy.arbitrage import ArbitrageStrategy
        logger.info("✅ Import strategii: OK")
        validation_results['strategy_imports'] = True
    except Exception as e:
        logger.info(f"❌ Import strategii: BŁĄD - {e}")
        validation_results['strategy_imports'] = False
    
    # Test 2: Import giełd
    try:
        from app.exchange.kraken import KrakenExchange
        from app.exchange.bitfinex import BitfinexExchange
        logger.info("✅ Import giełd: OK")
        validation_results['exchange_imports'] = True
    except Exception as e:
        logger.info(f"❌ Import giełd: BŁĄD - {e}")
        validation_results['exchange_imports'] = False
    
    # Test 3: Sprawdzenie factory
    try:
        from app.exchange import AVAILABLE_EXCHANGES
        if 'kraken' in AVAILABLE_EXCHANGES and 'bitfinex' in AVAILABLE_EXCHANGES:
            logger.info("✅ Factory pattern: OK")
            validation_results['factory_pattern'] = True
        else:
            logger.info("❌ Factory pattern: Brak nowych giełd w AVAILABLE_EXCHANGES")
            validation_results['factory_pattern'] = False
    except Exception as e:
        logger.info(f"❌ Factory pattern: BŁĄD - {e}")
        validation_results['factory_pattern'] = False
    
    # Test 4: Sprawdzenie UI
    try:
        # Sprawdź czy plik UI istnieje i zawiera nowe strategie
        ui_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'bot_management.py')
        if os.path.exists(ui_file):
            with open(ui_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'Swing Trading' in content and 'Arbitrage' in content:
                    logger.info("✅ Aktualizacja UI: OK")
                    validation_results['ui_updates'] = True
                else:
                    logger.info("❌ Aktualizacja UI: Brak nowych strategii")
                    validation_results['ui_updates'] = False
        else:
            logger.info("❌ Aktualizacja UI: Plik nie istnieje")
            validation_results['ui_updates'] = False
    except Exception as e:
        logger.info(f"❌ Aktualizacja UI: BŁĄD - {e}")
        validation_results['ui_updates'] = False
    
    logger.info("=" * 50)
    
    # Podsumowanie walidacji
    passed = sum(1 for result in validation_results.values() if result)
    total = len(validation_results)
    
    if passed == total:
        logger.info("🎉 Wszystkie podstawowe funkcje działają poprawnie!")
        return True
    else:
        logger.info(f"⚠️  {total - passed} z {total} funkcji wymaga uwagi.")
        return False

if __name__ == "__main__":
    logger.info("🤖 SYSTEM TESTÓW NOWYCH FUNKCJI TRADING BOTA")
    logger.info("Wersja: 1.0")
    logger.info("Autor: AI Assistant")
    
    # Uruchom szybką walidację
    quick_result = asyncio.run(run_quick_validation())
    
    if quick_result:
        logger.info("\n✅ Szybka walidacja zakończona pomyślnie!")
        logger.info("🚀 Przechodzę do pełnych testów...")
        
        # Uruchom pełne testy
        full_result = asyncio.run(run_comprehensive_tests())
        
        if full_result:
            logger.info("\n🏆 WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE!")
            logger.info("🎯 Nowe funkcje są w pełni gotowe do użycia!")
            sys.exit(0)
        else:
            logger.info("\n⚠️  NIEKTÓRE TESTY NIE POWIODŁY SIĘ")
            logger.info("🔧 Sprawdź logi i popraw błędy przed wdrożeniem.")
            sys.exit(1)
    else:
        logger.info("\n❌ SZYBKA WALIDACJA NIEUDANA")
        logger.info("🔧 Popraw podstawowe błędy przed uruchomieniem pełnych testów.")
        sys.exit(1)