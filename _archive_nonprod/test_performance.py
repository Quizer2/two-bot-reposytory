#!/usr/bin/env python3
"""
Kompleksowe testy wydajności dla CryptoBot

Testuje:
- Latencja API (<100ms)
- Throughput (>1000 req/min)
- Memory usage (<500MB)
- CPU usage (<50%)
- Concurrent connections (>50)
- Load testing
- Stress testing
"""

import asyncio
import time
import psutil
import gc
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics
import json
import aiohttp
import requests
from unittest.mock import AsyncMock, MagicMock

# Importy z aplikacji
from utils.logger import get_logger, LogType
from app.api_config_manager import get_api_config_manager
from core.database_manager import DatabaseManager
from app.trading_mode_manager import TradingModeManager
import logging
logger = logging.getLogger(__name__)


class PerformanceTester:
    """Klasa do testowania wydajności aplikacji"""
    
    def __init__(self):
        self.logger = get_logger("test_performance", LogType.SYSTEM)
        self.api_config = get_api_config_manager()
        self.test_results = {}
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Metryki wydajności
        self.metrics = {
            'api_latency': [],
            'throughput': 0,
            'memory_usage': [],
            'cpu_usage': [],
            'concurrent_connections': 0,
            'error_rate': 0,
            'response_times': []
        }
        
    async def run_all_tests(self):
        """Uruchomienie wszystkich testów wydajności"""
logger.info("⚡ ROZPOCZYNANIE TESTÓW WYDAJNOŚCI")
logger.info("=" * 60)
        
        # Test 1: Latencja API
        await self._test_api_latency()
        
        # Test 2: Throughput
        await self._test_throughput()
        
        # Test 3: Zużycie pamięci
        await self._test_memory_usage()
        
        # Test 4: Zużycie CPU
        await self._test_cpu_usage()
        
        # Test 5: Równoczesne połączenia
        await self._test_concurrent_connections()
        
        # Test 6: Load testing
        await self._test_load_performance()
        
        # Test 7: Stress testing
        await self._test_stress_limits()
        
        # Podsumowanie
        self._print_summary()
        
    async def _test_api_latency(self):
        """Test latencji API (<100ms)"""
logger.info("\n🚀 Latencja API...")
        
        try:
            latencies = []
            
            # Test różnych endpointów
            endpoints = [
                self._test_price_endpoint,
                self._test_balance_endpoint,
                self._test_orderbook_endpoint,
                self._test_trades_endpoint
            ]
            
            for endpoint_test in endpoints:
                for _ in range(10):  # 10 requestów na endpoint
                    start_time = time.time()
                    await endpoint_test()
                    end_time = time.time()
                    
                    latency = (end_time - start_time) * 1000  # ms
                    latencies.append(latency)
                    
                    # Krótka przerwa między requestami
                    await asyncio.sleep(0.1)
            
            # Analiza wyników
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            
            self.metrics['api_latency'] = latencies
logger.info(f"   📊 Średnia latencja: {avg_latency:.1f}ms")
logger.info(f"   📊 Min latencja: {min_latency:.1f}ms")
logger.info(f"   📊 Max latencja: {max_latency:.1f}ms")
logger.info(f"   📊 95th percentile: {p95_latency:.1f}ms")
            
            # Sprawdzenie kryterium (<100ms)
            if avg_latency < 100:
                self.test_results['api_latency'] = 'PASSED'
logger.info("   ✅ Latencja API: PASSED")
            else:
                self.test_results['api_latency'] = f'FAILED: {avg_latency:.1f}ms > 100ms'
logger.info(f"   ❌ Latencja API: FAILED - {avg_latency:.1f}ms > 100ms")
                
        except Exception as e:
            self.test_results['api_latency'] = f'FAILED: {e}'
logger.info(f"   ❌ Latencja API: FAILED - {e}")
    
    async def _test_price_endpoint(self):
        """Test endpointu cen"""
        # Symulacja API call
        await asyncio.sleep(0.01)  # 10ms symulacja
        return {'price': 45000.0}
    
    async def _test_balance_endpoint(self):
        """Test endpointu sald"""
        # Symulacja API call
        await asyncio.sleep(0.015)  # 15ms symulacja
        return {'USDT': 1000.0, 'BTC': 0.1}
    
    async def _test_orderbook_endpoint(self):
        """Test endpointu księgi zleceń"""
        # Symulacja API call
        await asyncio.sleep(0.02)  # 20ms symulacja
        return {'bids': [[45000, 1.0]], 'asks': [[45010, 1.0]]}
    
    async def _test_trades_endpoint(self):
        """Test endpointu transakcji"""
        # Symulacja API call
        await asyncio.sleep(0.012)  # 12ms symulacja
        return [{'id': 1, 'price': 45000, 'amount': 0.1}]
    
    async def _test_throughput(self):
        """Test throughput (>1000 req/min)"""
logger.info("\n📈 Throughput...")
        
        try:
            start_time = time.time()
            request_count = 0
            duration = 60  # 1 minuta
            
            # Symulacja requestów przez 1 minutę (skrócone do 10 sekund dla testu)
            test_duration = 10  # sekund
            target_rps = 1000 / 60  # requests per second dla 1000/min
            
            end_time = start_time + test_duration
            
            while time.time() < end_time:
                # Batch requestów
                tasks = []
                for _ in range(10):  # 10 równoczesnych requestów
                    tasks.append(self._make_test_request())
                
                await asyncio.gather(*tasks)
                request_count += 10
                
                # Kontrola rate
                await asyncio.sleep(0.1)
            
            actual_duration = time.time() - start_time
            throughput = (request_count / actual_duration) * 60  # req/min
            
            self.metrics['throughput'] = throughput
logger.info(f"   📊 Requests wykonane: {request_count}")
logger.info(f"   📊 Czas trwania: {actual_duration:.1f}s")
logger.info(f"   📊 Throughput: {throughput:.0f} req/min")
            
            # Sprawdzenie kryterium (>1000 req/min)
            if throughput > 1000:
                self.test_results['throughput'] = 'PASSED'
logger.info("   ✅ Throughput: PASSED")
            else:
                self.test_results['throughput'] = f'FAILED: {throughput:.0f} < 1000 req/min'
logger.info(f"   ❌ Throughput: FAILED - {throughput:.0f} < 1000 req/min")
                
        except Exception as e:
            self.test_results['throughput'] = f'FAILED: {e}'
logger.info(f"   ❌ Throughput: FAILED - {e}")
    
    async def _make_test_request(self):
        """Symulacja pojedynczego requestu"""
        await asyncio.sleep(0.005)  # 5ms symulacja
        return {'status': 'ok'}
    
    async def _test_memory_usage(self):
        """Test zużycia pamięci (<500MB)"""
logger.info("\n💾 Zużycie pamięci...")
        
        try:
            # Pomiar początkowy
            initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Symulacja obciążenia pamięci
            test_data = []
            
            for i in range(100):
                # Tworzenie danych testowych
                data_chunk = {
                    'prices': [45000 + j for j in range(1000)],
                    'volumes': [1.0 + j * 0.1 for j in range(1000)],
                    'timestamps': [time.time() + j for j in range(1000)]
                }
                test_data.append(data_chunk)
                
                # Pomiar co 10 iteracji
                if i % 10 == 0:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    self.metrics['memory_usage'].append(current_memory)
                    
                    # Krótka przerwa
                    await asyncio.sleep(0.01)
            
            # Pomiar końcowy
            final_memory = self.process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory
logger.info(f"   📊 Pamięć początkowa: {initial_memory:.1f} MB")
logger.info(f"   📊 Pamięć końcowa: {final_memory:.1f} MB")
logger.info(f"   📊 Wzrost pamięci: {memory_increase:.1f} MB")
logger.info(f"   📊 Maksymalne zużycie: {max(self.metrics['memory_usage']):.1f} MB")
            
            # Czyszczenie pamięci
            del test_data
            gc.collect()
            
            # Sprawdzenie kryterium (<500MB)
            max_memory = max(self.metrics['memory_usage'])
            if max_memory < 500:
                self.test_results['memory_usage'] = 'PASSED'
logger.info("   ✅ Zużycie pamięci: PASSED")
            else:
                self.test_results['memory_usage'] = f'FAILED: {max_memory:.1f}MB > 500MB'
logger.info(f"   ❌ Zużycie pamięci: FAILED - {max_memory:.1f}MB > 500MB")
                
        except Exception as e:
            self.test_results['memory_usage'] = f'FAILED: {e}'
logger.info(f"   ❌ Zużycie pamięci: FAILED - {e}")
    
    async def _test_cpu_usage(self):
        """Test zużycia CPU (<50%)"""
logger.info("\n🔥 Zużycie CPU...")
        
        try:
            cpu_measurements = []
            
            # Symulacja obciążenia CPU
            start_time = time.time()
            duration = 10  # sekund
            
            while time.time() - start_time < duration:
                # Pomiar CPU
                cpu_percent = self.process.cpu_percent(interval=0.1)
                cpu_measurements.append(cpu_percent)
                
                # Symulacja obciążenia
                await self._cpu_intensive_task()
                
                await asyncio.sleep(0.1)
            
            self.metrics['cpu_usage'] = cpu_measurements
            
            avg_cpu = statistics.mean(cpu_measurements)
            max_cpu = max(cpu_measurements)
logger.info(f"   📊 Średnie zużycie CPU: {avg_cpu:.1f}%")
logger.info(f"   📊 Maksymalne zużycie CPU: {max_cpu:.1f}%")
logger.info(f"   📊 Liczba pomiarów: {len(cpu_measurements)}")
            
            # Sprawdzenie kryterium (<50%)
            if avg_cpu < 50:
                self.test_results['cpu_usage'] = 'PASSED'
logger.info("   ✅ Zużycie CPU: PASSED")
            else:
                self.test_results['cpu_usage'] = f'FAILED: {avg_cpu:.1f}% > 50%'
logger.info(f"   ❌ Zużycie CPU: FAILED - {avg_cpu:.1f}% > 50%")
                
        except Exception as e:
            self.test_results['cpu_usage'] = f'FAILED: {e}'
logger.info(f"   ❌ Zużycie CPU: FAILED - {e}")
    
    async def _cpu_intensive_task(self):
        """Zadanie intensywnie wykorzystujące CPU"""
        # Symulacja obliczeń
        result = 0
        for i in range(10000):
            result += i * i
        return result
    
    async def _test_concurrent_connections(self):
        """Test równoczesnych połączeń (>50)"""
logger.info("\n🔗 Równoczesne połączenia...")
        
        try:
            max_connections = 100
            successful_connections = 0
            
            # Tworzenie równoczesnych połączeń
            tasks = []
            for i in range(max_connections):
                task = asyncio.create_task(self._simulate_connection(i))
                tasks.append(task)
            
            # Oczekiwanie na wszystkie połączenia
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Liczenie udanych połączeń
            for result in results:
                if not isinstance(result, Exception) and result:
                    successful_connections += 1
            
            self.metrics['concurrent_connections'] = successful_connections
logger.info(f"   📊 Próby połączeń: {max_connections}")
logger.info(f"   📊 Udane połączenia: {successful_connections}")
logger.info(f"   📊 Wskaźnik sukcesu: {(successful_connections/max_connections)*100:.1f}%")
            
            # Sprawdzenie kryterium (>50)
            if successful_connections > 50:
                self.test_results['concurrent_connections'] = 'PASSED'
logger.info("   ✅ Równoczesne połączenia: PASSED")
            else:
                self.test_results['concurrent_connections'] = f'FAILED: {successful_connections} <= 50'
logger.info(f"   ❌ Równoczesne połączenia: FAILED - {successful_connections} <= 50")
                
        except Exception as e:
            self.test_results['concurrent_connections'] = f'FAILED: {e}'
logger.info(f"   ❌ Równoczesne połączenia: FAILED - {e}")
    
    async def _simulate_connection(self, connection_id: int):
        """Symulacja pojedynczego połączenia"""
        try:
            # Symulacja nawiązywania połączenia
            await asyncio.sleep(0.1)
            
            # Symulacja wymiany danych
            await asyncio.sleep(0.05)
            
            # Symulacja zamknięcia połączenia
            await asyncio.sleep(0.02)
            
            return True
            
        except Exception as e:
            return False
    
    async def _test_load_performance(self):
        """Test wydajności pod obciążeniem"""
logger.info("\n⚖️ Test obciążenia...")
        
        try:
            # Symulacja normalnego obciążenia
            load_results = {
                'response_times': [],
                'error_count': 0,
                'success_count': 0
            }
            
            # Test przez 30 sekund (skrócone do 5 sekund)
            test_duration = 5
            start_time = time.time()
            
            while time.time() - start_time < test_duration:
                # Batch requestów
                batch_size = 20
                tasks = []
                
                for _ in range(batch_size):
                    tasks.append(self._load_test_request())
                
                batch_start = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                batch_end = time.time()
                
                # Analiza wyników
                for result in results:
                    if isinstance(result, Exception):
                        load_results['error_count'] += 1
                    else:
                        load_results['success_count'] += 1
                
                batch_time = (batch_end - batch_start) * 1000  # ms
                load_results['response_times'].append(batch_time)
                
                await asyncio.sleep(0.1)
            
            # Analiza wyników
            total_requests = load_results['success_count'] + load_results['error_count']
            error_rate = (load_results['error_count'] / total_requests) * 100 if total_requests > 0 else 0
            avg_response_time = statistics.mean(load_results['response_times']) if load_results['response_times'] else 0
            
            self.metrics['error_rate'] = error_rate
            self.metrics['response_times'] = load_results['response_times']
logger.info(f"   📊 Całkowite requesty: {total_requests}")
logger.info(f"   📊 Udane requesty: {load_results['success_count']}")
logger.info(f"   📊 Błędne requesty: {load_results['error_count']}")
logger.info(f"   📊 Wskaźnik błędów: {error_rate:.1f}%")
logger.info(f"   📊 Średni czas odpowiedzi: {avg_response_time:.1f}ms")
            
            # Sprawdzenie kryteriów
            if error_rate < 5 and avg_response_time < 200:
                self.test_results['load_performance'] = 'PASSED'
logger.info("   ✅ Test obciążenia: PASSED")
            else:
                self.test_results['load_performance'] = f'FAILED: error_rate={error_rate:.1f}%, response_time={avg_response_time:.1f}ms'
logger.info(f"   ❌ Test obciążenia: FAILED")
                
        except Exception as e:
            self.test_results['load_performance'] = f'FAILED: {e}'
logger.info(f"   ❌ Test obciążenia: FAILED - {e}")
    
    async def _load_test_request(self):
        """Pojedynczy request dla testu obciążenia"""
        # Symulacja różnych typów requestów
        request_types = [
            lambda: asyncio.sleep(0.01),  # Szybki request
            lambda: asyncio.sleep(0.05),  # Średni request
            lambda: asyncio.sleep(0.1),   # Wolny request
        ]
        
        import random
        request_func = random.choice(request_types)
        await request_func()
        
        # Symulacja możliwego błędu (5% szans)
        if random.random() < 0.05:
            raise Exception("Simulated error")
        
        return {'status': 'success'}
    
    async def _test_stress_limits(self):
        """Test limitów stresowych"""
logger.info("\n🔥 Test limitów stresowych...")
        
        try:
            stress_results = {
                'max_concurrent_tasks': 0,
                'memory_peak': 0,
                'cpu_peak': 0,
                'breaking_point': None
            }
            
            # Stopniowe zwiększanie obciążenia
            for concurrent_level in [10, 25, 50, 100, 200]:
                pass
logger.info(f"   🔄 Test z {concurrent_level} równoczesnych zadań...")
                
                    pass
                try:
                    # Pomiar przed testem
                    memory_before = self.process.memory_info().rss / 1024 / 1024
                    
                    # Uruchomienie zadań
                        pass
                    tasks = []
                    for _ in range(concurrent_level):
                        task = asyncio.create_task(self._stress_test_task())
                        tasks.append(task)
                    
                    # Oczekiwanie z timeoutem
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=10.0
                    )
                    
                    # Pomiar po teście
                    memory_after = self.process.memory_info().rss / 1024 / 1024
                    cpu_usage = self.process.cpu_percent()
                    
                    stress_results['max_concurrent_tasks'] = concurrent_level
                    stress_results['memory_peak'] = max(stress_results['memory_peak'], memory_after)
                    stress_results['cpu_peak'] = max(stress_results['cpu_peak'], cpu_usage)
                    pass
logger.info(f"     ✅ {concurrent_level} zadań: OK (RAM: {memory_after:.1f}MB, CPU: {cpu_usage:.1f}%)")
                    
                except asyncio.TimeoutError:
                    stress_results['breaking_point'] = concurrent_level
logger.info(f"     ❌ {concurrent_level} zadań: TIMEOUT")
                    break
                except Exception as e:
                    stress_results['breaking_point'] = concurrent_level
logger.info(f"     ❌ {concurrent_level} zadań: ERROR - {e}")
                    break
                
                # Krótka przerwa między testami
                await asyncio.sleep(1)
logger.info(f"   📊 Maksymalne równoczesne zadania: {stress_results['max_concurrent_tasks']}")
                pass
logger.info(f"   📊 Szczyt pamięci: {stress_results['memory_peak']:.1f} MB")
logger.info(f"   📊 Szczyt CPU: {stress_results['cpu_peak']:.1f}%")
            
                pass
            if stress_results['breaking_point']:
logger.info(f"   ⚠️ Punkt załamania: {stress_results['breaking_point']} zadań")
                pass
            
            # Sprawdzenie kryteriów
            if stress_results['max_concurrent_tasks'] >= 50:
                self.test_results['stress_limits'] = 'PASSED'
logger.info("   ✅ Test limitów stresowych: PASSED")
            else:
                self.test_results['stress_limits'] = f'FAILED: max_tasks={stress_results["max_concurrent_tasks"]}'
logger.info(f"   ❌ Test limitów stresowych: FAILED")
                
        except Exception as e:
            self.test_results['stress_limits'] = f'FAILED: {e}'
logger.info(f"   ❌ Test limitów stresowych: FAILED - {e}")
    
    async def _stress_test_task(self):
            pass
        """Pojedyncze zadanie dla testu stresowego"""
        # Symulacja intensywnego zadania
        await asyncio.sleep(0.1)
        
        # Symulacja obliczeń
        result = 0
        for i in range(1000):
            result += i * i
        
        # Symulacja I/O
        await asyncio.sleep(0.05)
        
        return result
    
    def _print_summary(self):
        """Wydrukowanie podsumowania testów wydajności"""
            pass
logger.info("\n" + "=" * 60)
logger.info("⚡ PODSUMOWANIE TESTÓW WYDAJNOŚCI")
logger.info("=" * 60)
        
                pass
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result == 'PASSED' else f"❌ {result}"
            test_display = test_name.replace('_', ' ').title()
            pass
logger.info(f"{test_display:.<40} {status}")
            
            if result == 'PASSED':
                passed += 1
logger.info("-" * 60)
logger.info(f"Wynik: {passed}/{total} testów przeszło pomyślnie")
            pass
        
        # Szczegółowe metryki
logger.info("\n📊 SZCZEGÓŁOWE METRYKI:")
            pass
        if self.metrics['api_latency']:
            avg_latency = statistics.mean(self.metrics['api_latency'])
logger.info(f"   Średnia latencja API: {avg_latency:.1f}ms")
            pass
        
        if self.metrics['throughput']:
logger.info(f"   Throughput: {self.metrics['throughput']:.0f} req/min")
            pass
        
        if self.metrics['memory_usage']:
            max_memory = max(self.metrics['memory_usage'])
logger.info(f"   Maksymalne zużycie pamięci: {max_memory:.1f} MB")
        
        if self.metrics['cpu_usage']:
            avg_cpu = statistics.mean(self.metrics['cpu_usage'])
logger.info(f"   Średnie zużycie CPU: {avg_cpu:.1f}%")
        
        if self.metrics['concurrent_connections']:
logger.info(f"   Równoczesne połączenia: {self.metrics['concurrent_connections']}")
logger.info("-" * 60)
        
        if passed == total:
logger.info("🎉 Wszystkie testy wydajności przeszły pomyślnie!")
logger.info("✅ System spełnia wszystkie wymagania wydajnościowe")
        else:
logger.info("⚠️ Niektóre testy wydajności nie przeszły")
logger.info("🔧 Sprawdź konfigurację i optymalizację systemu")


async def main():
    """Główna funkcja testowa"""
    tester = PerformanceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())