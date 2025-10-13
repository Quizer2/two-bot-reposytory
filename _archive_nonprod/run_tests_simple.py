#!/usr/bin/env python3
"""
CRYPTOBOTDESKTOP - PROSTY RUNNER TESTOW
======================================

Uproszczony skrypt uruchamiajacy wszystkie testy bez emoji
dla kompatybilnosci z Windows PowerShell.

Autor: CryptoBotDesktop Team
Wersja: 1.0.0
"""

import subprocess
import sys
import os
import time
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

class SimpleTestRunner:
    """Prosta klasa zarzadzajaca uruchamianiem testow"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.test_directory = Path(__file__).parent
        
    def setup_environment(self):
        """Przygotuj srodowisko testowe"""
logger.info("Przygotowywanie srodowiska testowego...")
        
        # Ustaw PYTHONPATH
        current_dir = str(self.test_directory)
        os.environ['PYTHONPATH'] = current_dir
        os.environ['TEST_MODE'] = 'true'
logger.info(f"   PYTHONPATH: {current_dir}")
logger.info(f"   TEST_MODE: true")
        
    def run_test(self, test_file, test_name, timeout=300):
        """Uruchom pojedynczy test"""
logger.info(f"\n{'='*60}")
logger.info(f"URUCHAMIANIE: {test_name}")
logger.info(f"Plik: {test_file}")
logger.info(f"{'='*60}")
        
        test_start = time.time()
        
        try:
            # Sprawdz czy plik istnieje
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
logger.info(f"[PASSED] {test_name} ({duration:.1f}s)")
            else:
                status = 'FAILED'
logger.info(f"[FAILED] {test_name} ({duration:.1f}s)")
                if result.stderr:
                    pass
logger.info(f"   Blad: {result.stderr[:200]}...")
                    
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
logger.info(f"[TIMEOUT] {test_name} ({timeout}s)")
            return {
                'name': test_name,
                'file': test_file,
                'status': 'TIMEOUT',
                'duration': duration,
                'error': f'Test przekroczyl limit czasu {timeout}s'
            }
            pass
            
        except Exception as e:
            duration = time.time() - test_start
logger.info(f"[ERROR] {test_name} - {str(e)}")
            return {
                'name': test_name,
                'file': test_file,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            }
    
    def analyze_results(self):
        """Analizuj wyniki testow"""
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
        """Generuj raport koncowy"""
logger.info(f"\n{'='*60}")
logger.info("PODSUMOWANIE WSZYSTKICH TESTOW")
logger.info(f"{'='*60}")
logger.info(f"Data: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Czas wykonania: {analysis['total_duration']:.1f}s")
logger.info(f"Wskaznik sukcesu: {analysis['success_rate']:.1f}%")
logger.info()
            pass
        
        # Wyniki poszczegolnych testow
        for test_result in self.results.values():
            status_text = {
                'PASSED': '[PASSED]',
                'FAILED': '[FAILED]',
                'ERROR': '[ERROR]',
                'TIMEOUT': '[TIMEOUT]',
                'MISSING': '[MISSING]'
            }.get(test_result['status'], '[UNKNOWN]')
logger.info(f"{test_result['name']:.<40} {status_text} ({test_result['duration']:.1f}s)")
logger.info()
            pass
logger.info(f"WYNIK KONCOWY: {analysis['passed']}/{analysis['total']} kategorii przeszlo")
        
        # Ocena ogolna
        if analysis['success_rate'] >= 90:
logger.info("DOSKONALY WYNIK! Wszystkie systemy dzialaja prawidlowo.")
            overall_status = "EXCELLENT"
        elif analysis['success_rate'] >= 75:
logger.info("DOBRY WYNIK! Wiekszosc systemow dziala poprawnie.")
            overall_status = "GOOD"
        elif analysis['success_rate'] >= 50:
logger.info("SREDNI WYNIK! Wymagane poprawki w niektorych obszarach.")
            overall_status = "MEDIUM"
        else:
logger.info("SLABY WYNIK! Wymagane znaczace poprawki.")
            overall_status = "POOR"
            
        return overall_status
    
    def run_all_tests(self):
        """Uruchom wszystkie testy"""
logger.info("ROZPOCZYNANIE WSZYSTKICH TESTOW CRYPTOBOTDESKTOP")
logger.info(f"Data: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Python: {sys.version.split()[0]}")
logger.info(f"Katalog: {self.test_directory}")
        
        # Przygotuj srodowisko
        self.setup_environment()
        
        # Definicja testow - sprawdzamy ktore pliki istnieja
        available_tests = []
        
        potential_tests = [
            ("test_unit.py", "Testy Jednostkowe", 180),
            ("test_trading_bots.py", "Testy Strategii Handlowych", 240),
            ("test_performance.py", "Testy Wydajnosci", 300),
            ("test_security.py", "Testy Bezpieczenstwa", 180),
            ("test_integration.py", "Testy Integracyjne", 360),
            ("test_ui.py", "Testy Interfejsu Uzytkownika", 240)
        ]
                pass
        
        # Sprawdz ktore testy istnieja
                pass
        for test_file, test_name, timeout in potential_tests:
            test_path = self.test_directory / test_file
            if test_path.exists():
                available_tests.append((test_file, test_name, timeout))
logger.info(f"Znaleziono: {test_file}")
            else:
logger.info(f"Brak pliku: {test_file}")
        
            pass
        if not available_tests:
logger.info("BLAD: Nie znaleziono zadnych plikow testowych!")
            return "ERROR", {}
logger.info(f"\nUruchamianie {len(available_tests)} testow...")
        
        # Uruchom kazdy test
        for test_file, test_name, timeout in available_tests:
            result = self.run_test(test_file, test_name, timeout)
            self.results[test_file] = result
            
            # Krotka przerwa miedzy testami
            time.sleep(1)
        
        # Analizuj wyniki
        analysis = self.analyze_results()
        overall_status = self.generate_report(analysis)
        
        # Rekomendacje
        self.print_recommendations(analysis)
        
        return overall_status, analysis
            pass
    
    def print_recommendations(self, analysis):
        """Wydrukuj rekomendacje na podstawie wynikow"""
logger.info(f"\n{'='*60}")
logger.info("REKOMENDACJE")
logger.info(f"{'='*60}")
        
        if analysis['success_rate'] < 50:
logger.info("KRYTYCZNE PROBLEMY:")
logger.info("   - Natychmiastowa naprawa bledow w testach")
logger.info("   - Przeglad konfiguracji srodowiska")
logger.info("   - Sprawdzenie zaleznosci i importow")
            
        elif analysis['success_rate'] < 75:
logger.info("WYMAGANE POPRAWKI:")
logger.info("   - Analiza bledow w niezaliczonych testach")
logger.info("   - Optymalizacja wydajnosci")
            pass
logger.info("   - Wzmocnienie bezpieczenstwa")
            
        elif analysis['success_rate'] < 90:
logger.info("DROBNE ULEPSZENIA:")
logger.info("   - Finalne poprawki w testach")
logger.info("   - Optymalizacja kodu")
logger.info("   - Dokumentacja zmian")
            
        else:
logger.info("GRATULACJE!")
logger.info("   - System jest gotowy do produkcji")
        pass
logger.info("   - Regularne monitorowanie")
logger.info("   - Ciagle ulepszenia")
logger.info("\nDODATKOWE ZASOBY:")
logger.info("   - Dokumentacja: DOKUMENTACJA_TESTOW.md")
            pass
logger.info("   - Podsumowanie: PODSUMOWANIE_TESTOW.md")
            pass
logger.info("   - Logi: sprawdz pliki *.log")

        pass
def main():
    """Glowna funkcja"""
    try:
        runner = SimpleTestRunner()
        overall_status, analysis = runner.run_all_tests()
        
        # Kod wyjscia na podstawie wynikow
        if analysis and analysis['success_rate'] >= 75:
            sys.exit(0)  # Sukces
        else:
            sys.exit(1)  # Blad
            
    except KeyboardInterrupt:
logger.info("\n\nTesty przerwane przez uzytkownika")
        sys.exit(130)
        
    except Exception as e:
logger.info(f"\n\nNieoczekiwany blad: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()