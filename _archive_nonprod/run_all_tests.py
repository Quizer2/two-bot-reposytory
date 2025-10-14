#!/usr/bin/env python3
"""
🧪 CRYPTOBOTDESKTOP - AUTOMATYCZNY RUNNER TESTÓW
== == == == == == == == == == == == == == == == == == == ==

Skrypt uruchamiający wszystkie testy aplikacji CryptoBotDesktop
z automatycznym raportowaniem wyników i analizą problemów.

Autor: CryptoBotDesktop Team
Wersja: 1.0.0
Data: 2024
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

class TestRunner:
    __test__ = False
    """Klasa zarządzająca uruchamianiem testów"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.test_directory = Path(__file__).parent
        
    def setup_environment(self):
        """Przygotuj środowisko testowe"""
logger.info("🔧 Przygotowywanie środowiska testowego...")
        
        # Ustaw PYTHONPATH
        current_dir = str(self.test_directory)
        os.environ['PYTHONPATH'] = current_dir
        os.environ['TEST_MODE'] = 'true'
logger.info(f"   📁 PYTHONPATH: {current_dir}")
logger.info(f"   🧪 TEST_MODE: true")
        
    def run_test(self, test_file, test_name, timeout=300):
        """
        Uruchom pojedynczy test
        
        Args:
            test_file (str): Nazwa pliku testowego
            test_name (str): Nazwa testu do wyświetlenia
            timeout (int): Timeout w sekundach
            
        Returns:
            dict: Wyniki testu
        """
logger.info(f"\n{'='*60}")
logger.info(f"🧪 URUCHAMIANIE: {test_name}")
logger.info(f"📄 Plik: {test_file}")
logger.info(f"{'='*60}")
        
        test_start = time.time()
        
        try:
            # Sprawdź czy plik istnieje
            test_path = self.test_directory / test_file
            if not test_path.exists():
                return {
                    'name': test_name,
                    'file': test_file,
                    'status': 'MISSING',
                    'duration': 0,
                    'error': f'Plik {test_file} nie istnieje'
                }
            
            # Uruchom test
            result = subprocess.run(
                [sys.executable, str(test_path)], 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=str(self.test_directory)
            )
            
            duration = time.time() - test_start
            
            # Analizuj wyniki
            if result.returncode == 0:
                status = 'PASSED'
logger.info(f"✅ {test_name}: ZALICZONY ({duration:.1f}s)")
            else:
                status = 'FAILED'
logger.info(f"❌ {test_name}: NIEZALICZONY ({duration:.1f}s)")
                if result.stderr:
                    pass
logger.info(f"   🔍 Błąd: {result.stderr[:200]}...")
                    
            return {
                'name': test_name,
                'file': test_file,
                'status': status,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
            pass
        except subprocess.TimeoutExpired:
            duration = time.time() - test_start
logger.info(f"⏰ {test_name}: TIMEOUT ({timeout}s)")
            return {
                'name': test_name,
                'file': test_file,
                'status': 'TIMEOUT',
                'duration': duration,
                'error': f'Test przekroczył limit czasu {timeout}s'
            }
            pass
            
        except Exception as e:
            duration = time.time() - test_start
logger.info(f"💥 {test_name}: BŁĄD - {str(e)}")
            return {
                'name': test_name,
                'file': test_file,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            }
    
    def analyze_results(self):
        """Analizuj wyniki testów"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['status'] == 'PASSED')
        failed_tests = sum(1 for r in self.results.values() if r['status'] == 'FAILED')
        error_tests = sum(1 for r in self.results.values() if r['status'] in ['ERROR', 'TIMEOUT', 'MISSING'])
        
        total_duration = sum(r['duration'] for r in self.results.values())
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'errors': error_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': total_duration
        }
    
    def generate_report(self, analysis):
        """Generuj raport końcowy"""
logger.info(f"\n{'='*60}")
logger.info("📊 PODSUMOWANIE WSZYSTKICH TESTÓW")
logger.info(f"{'='*60}")
logger.info(f"📅 Data: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"⏱️  Czas wykonania: {analysis['total_duration']:.1f}s")
logger.info(f"📈 Wskaźnik sukcesu: {analysis['success_rate']:.1f}%")
logger.info()
            pass
        
        # Wyniki poszczególnych testów
        for test_result in self.results.values():
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'ERROR': '💥',
                'TIMEOUT': '⏰',
                'MISSING': '📄'
            }.get(test_result['status'], '❓')
logger.info(f"{test_result['name']:.<40} {status_icon} {test_result['status']} ({test_result['duration']:.1f}s)")
logger.info()
            pass
logger.info(f"🎯 WYNIK KOŃCOWY: {analysis['passed']}/{analysis['total']} kategorii przeszło")
        
        # Ocena ogólna
        if analysis['success_rate'] >= 90:
logger.info("🏆 DOSKONAŁY WYNIK! Wszystkie systemy działają prawidłowo.")
            overall_status = "EXCELLENT"
        elif analysis['success_rate'] >= 75:
logger.info("✅ DOBRY WYNIK! Większość systemów działa poprawnie.")
            overall_status = "GOOD"
        elif analysis['success_rate'] >= 50:
logger.info("⚠️ ŚREDNI WYNIK! Wymagane poprawki w niektórych obszarach.")
            overall_status = "MEDIUM"
        else:
logger.info("❌ SŁABY WYNIK! Wymagane znaczące poprawki.")
            overall_status = "POOR"
            
        return overall_status
    
    def save_results(self, analysis, overall_status):
        """Zapisz wyniki do pliku JSON"""
        report_data = {
            'timestamp': self.start_time.isoformat(),
            'overall_status': overall_status,
            'analysis': analysis,
            'detailed_results': self.results,
            'environment': {
                'python_version': sys.version,
                'platform': sys.platform,
                'working_directory': str(self.test_directory)
            }
            pass
        }
        
        # Zapisz do pliku
        report_file = self.test_directory / f"test_results_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
logger.info(f"\n💾 Szczegółowy raport zapisany: {report_file}")
        
    def run_all_tests(self):
        """Uruchom wszystkie testy"""
logger.info("🚀 ROZPOCZYNANIE WSZYSTKICH TESTÓW CRYPTOBOTDESKTOP")
logger.info(f"📅 Data: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"🐍 Python: {sys.version.split()[0]}")
logger.info(f"📁 Katalog: {self.test_directory}")
        
        # Przygotuj środowisko
        self.setup_environment()
        
        # Definicja testów
        tests = [
            ("test_unit.py", "Testy Jednostkowe", 180),
            ("test_trading_bots.py", "Testy Strategii Handlowych", 240),
            ("test_performance.py", "Testy Wydajności", 300),
            ("test_security.py", "Testy Bezpieczeństwa", 180),
            ("test_integration.py", "Testy Integracyjne", 360),
            ("test_ui.py", "Testy Interfejsu Użytkownika", 240)
        ]
        
        # Uruchom każdy test
        for test_file, test_name, timeout in tests:
            result = self.run_test(test_file, test_name, timeout)
            self.results[test_file] = result
            
            # Krótka przerwa między testami
            time.sleep(1)
        
        # Analizuj wyniki
        analysis = self.analyze_results()
        overall_status = self.generate_report(analysis)
        
        # Zapisz wyniki
        self.save_results(analysis, overall_status)
        
        # Rekomendacje
        self.print_recommendations(analysis)
        
        return overall_status, analysis
    
    def print_recommendations(self, analysis):
            pass
        """Wydrukuj rekomendacje na podstawie wyników"""
logger.info(f"\n{'='*60}")
logger.info("💡 REKOMENDACJE")
logger.info(f"{'='*60}")
        
        if analysis['success_rate'] < 50:
logger.info("🚨 KRYTYCZNE PROBLEMY:")
logger.info("   • Natychmiastowa naprawa błędów w testach")
logger.info("   • Przegląd konfiguracji środowiska")
logger.info("   • Sprawdzenie zależności i importów")
            
        elif analysis['success_rate'] < 75:
logger.info("⚠️ WYMAGANE POPRAWKI:")
logger.info("   • Analiza błędów w niezaliczonych testach")
logger.info("   • Optymalizacja wydajności")
logger.info("   • Wzmocnienie bezpieczeństwa")
            
            pass
        elif analysis['success_rate'] < 90:
logger.info("✨ DROBNE ULEPSZENIA:")
logger.info("   • Finalne poprawki w testach")
logger.info("   • Optymalizacja kodu")
logger.info("   • Dokumentacja zmian")
            
        else:
logger.info("🎉 GRATULACJE!")
logger.info("   • System jest gotowy do produkcji")
logger.info("   • Regularne monitorowanie")
logger.info("   • Ciągłe ulepszenia")
        pass
logger.info("\n📚 DODATKOWE ZASOBY:")
logger.info("   • Dokumentacja: DOKUMENTACJA_TESTOW.md")
logger.info("   • Podsumowanie: PODSUMOWANIE_TESTOW.md")
logger.info("   • Logi: sprawdź pliki *.log")
            pass

            pass
def main():
    """Główna funkcja"""
        pass
    try:
        runner = TestRunner()
        overall_status, analysis = runner.run_all_tests()
        pass
        
        # Kod wyjścia na podstawie wyników
        if analysis['success_rate'] >= 75:
            sys.exit(0)  # Sukces
        else:
            sys.exit(1)  # Błąd
            
    except KeyboardInterrupt:
logger.info("\n\n⏹️ Testy przerwane przez użytkownika")
        sys.exit(130)
        
    except Exception as e:
logger.info(f"\n\n💥 Nieoczekiwany błąd: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()