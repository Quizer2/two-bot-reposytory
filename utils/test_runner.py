#!/usr/bin/env python3
"""
🧪 AUTOMATYCZNY RUNNER TESTÓW - MODUŁ STARTOWY
== == == == == == == == == == == == == == == == == == == ==

Moduł do automatycznego uruchamiania testów przy starcie aplikacji.
Zapewnia szybkie sprawdzenie stanu systemu przed uruchomieniem głównej aplikacji.

Autor: CryptoBotDesktop Team
Wersja: 1.0.0
"""

import subprocess
import sys
import os
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from utils.logger import get_logger, LogType
from utils.config_manager import get_config_manager, get_app_setting


@dataclass
class TestResult:
    """Wynik pojedynczego testu"""
    __test__ = False
    name: str
    file: str
    status: str  # PASSED, FAILED, ERROR, TIMEOUT, SKIPPED
    duration: float
    error: Optional[str] = None
    output: Optional[str] = None


class StartupTestRunner:
    """
    Runner testów uruchamianych przy starcie aplikacji
    
    Uruchamia tylko kluczowe testy sprawdzające podstawową funkcjonalność
    systemu przed uruchomieniem głównej aplikacji.
    """
    __test__ = False
    
    def __init__(self):
        self.logger = get_logger("startup_tests")
        self.config_manager = get_config_manager()
        self.project_root = Path(__file__).parent.parent
        self.results: Dict[str, TestResult] = {}
        
        # Konfiguracja testów startowych
        self.startup_tests_enabled = get_app_setting("startup.run_tests", True)
        self.startup_test_timeout = get_app_setting("startup.test_timeout", 30)
        self.critical_tests_only = get_app_setting("startup.critical_tests_only", True)
        
    def is_enabled(self) -> bool:
        """Sprawdza czy testy startowe są włączone"""
        return self.startup_tests_enabled
    
    def get_startup_tests(self) -> List[Tuple[str, str, int]]:
        """
        Zwraca listę testów do uruchomienia przy starcie
        
        Returns:
            Lista krotek (plik_testu, nazwa_testu, timeout)
        """
        if self.critical_tests_only:
            # Tylko krytyczne testy - szybkie sprawdzenie podstawowej funkcjonalności
            return [
                ("test_security.py", "Testy Bezpieczeństwa", 20),
                ("test_integration.py", "Testy Integracyjne (podstawowe)", 30),
            ]
        else:
            # Pełny zestaw testów startowych
            return [
                ("test_security.py", "Testy Bezpieczeństwa", 30),
                ("test_integration.py", "Testy Integracyjne", 45),
                ("test_performance.py", "Testy Wydajności (podstawowe)", 30),
            ]
    
    async def run_test_async(self, test_file: str, test_name: str, timeout: int) -> TestResult:
        """
        Uruchamia pojedynczy test asynchronicznie
        
        Args:
            test_file: Nazwa pliku testowego
            test_name: Nazwa testu do wyświetlenia
            timeout: Timeout w sekundach
            
        Returns:
            Wynik testu
        """
        test_path = self.project_root / test_file
        
        if not test_path.exists():
            self.logger.warning(f"Test file not found: {test_path}")
            return TestResult(
                name=test_name,
                file=test_file,
                status="SKIPPED",
                duration=0.0,
                error=f"Plik testu nie istnieje: {test_file}"
            )
        
        self.logger.info(f"Running startup test: {test_name}")
        start_time = time.time()
        
        try:
            # Przygotuj środowisko
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root)
            env['TEST_MODE'] = 'startup'
            env['STARTUP_TEST'] = 'true'
            env['PYTHONIOENCODING'] = 'utf-8'  # Napraw problem z kodowaniem Unicode
            
            # Uruchom test
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(test_path),
                cwd=str(self.project_root),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                duration = time.time() - start_time
                
                if process.returncode == 0:
                    self.logger.info(f"✅ {test_name}: PASSED ({duration:.1f}s)")
                    return TestResult(
                        name=test_name,
                        file=test_file,
                        status="PASSED",
                        duration=duration,
                        output=stdout.decode('utf-8', errors='ignore')
                    )
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    self.logger.warning(f"❌ {test_name}: FAILED ({duration:.1f}s)")
                    return TestResult(
                        name=test_name,
                        file=test_file,
                        status="FAILED",
                        duration=duration,
                        error=error_msg,
                        output=stdout.decode('utf-8', errors='ignore')
                    )
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration = time.time() - start_time
                self.logger.warning(f"⏰ {test_name}: TIMEOUT ({timeout}s)")
                return TestResult(
                    name=test_name,
                    file=test_file,
                    status="TIMEOUT",
                    duration=duration,
                    error=f"Test przekroczył limit czasu {timeout}s"
                )
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"💥 {test_name}: ERROR - {str(e)}")
            return TestResult(
                name=test_name,
                file=test_file,
                status="ERROR",
                duration=duration,
                error=str(e)
            )
    
    async def run_startup_tests(self, progress_callback=None) -> Tuple[bool, Dict[str, TestResult]]:
        """
        Uruchamia wszystkie testy startowe
        
        Args:
            progress_callback: Funkcja callback do raportowania postępu
            
        Returns:
            Tuple (success, results)
        """
        if not self.is_enabled():
            self.logger.info("Startup tests disabled in configuration")
            return True, {}
        
        self.logger.info("Starting startup tests...")
        start_time = time.time()
        
        tests = self.get_startup_tests()
        total_tests = len(tests)
        
        if total_tests == 0:
            self.logger.info("No startup tests configured")
            return True, {}
        
        # Uruchom testy
        for i, (test_file, test_name, timeout) in enumerate(tests):
            if progress_callback:
                progress = int((i / total_tests) * 100)
                progress_callback(f"Uruchamianie testu: {test_name}", progress)
            
            result = await self.run_test_async(test_file, test_name, timeout)
            self.results[test_file] = result
            
            # Krótka przerwa między testami
            await asyncio.sleep(0.1)
        
        # Analiza wyników
        total_duration = time.time() - start_time
        passed_tests = sum(1 for r in self.results.values() if r.status == "PASSED")
        failed_tests = sum(1 for r in self.results.values() if r.status in ["FAILED", "ERROR", "TIMEOUT"])
        skipped_tests = sum(1 for r in self.results.values() if r.status == "SKIPPED")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        overall_success = success_rate >= 70  # 70% testów musi przejść
        
        # Logowanie wyników
        self.logger.info(f"Startup tests completed in {total_duration:.1f}s")
        self.logger.info(f"Results: {passed_tests} passed, {failed_tests} failed, {skipped_tests} skipped")
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        
        if overall_success:
            self.logger.info("✅ Startup tests PASSED - application can start")
        else:
            self.logger.warning("❌ Startup tests FAILED - application may have issues")
            
            # Loguj szczegóły błędów
            for result in self.results.values():
                if result.status in ["FAILED", "ERROR", "TIMEOUT"]:
                    self.logger.error(f"Failed test {result.name}: {result.error}")
        
        return overall_success, self.results
    
    def save_startup_test_results(self, results: Dict[str, TestResult]):
        """Zapisuje wyniki testów startowych"""
        try:
            logs_dir = self.project_root / "data" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = logs_dir / f"startup_tests_{timestamp}.json"
            
            # Konwertuj wyniki do formatu JSON
            json_results = {
                "timestamp": timestamp,
                "total_tests": len(results),
                "passed": sum(1 for r in results.values() if r.status == "PASSED"),
                "failed": sum(1 for r in results.values() if r.status in ["FAILED", "ERROR", "TIMEOUT"]),
                "skipped": sum(1 for r in results.values() if r.status == "SKIPPED"),
                "tests": {
                    file: {
                        "name": result.name,
                        "status": result.status,
                        "duration": result.duration,
                        "error": result.error
                    }
                    for file, result in results.items()
                }
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Startup test results saved to: {results_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save startup test results: {e}")


def create_startup_test_runner() -> StartupTestRunner:
    """Factory function do tworzenia StartupTestRunner"""
    return StartupTestRunner()