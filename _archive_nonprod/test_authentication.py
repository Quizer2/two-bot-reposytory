#!/usr/bin/env python3
"""
Test systemu autentykacji i uprawnień

Ten skrypt testuje wszystkie aspekty bezpieczeństwa aplikacji:
- Rejestrację użytkowników
- Logowanie i wylogowanie
- Zarządzanie sesjami
- Walidację haseł
- Blokowanie kont po nieudanych próbach
- Tokeny sesji i ich wygasanie
- Bezpieczeństwo haseł (hashing, salt)
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import secrets

# Dodaj ścieżkę do modułów
sys.path.append(str(Path(__file__).parent))

from core.database_manager import DatabaseManager
from utils.encryption import SecurityManager
from utils.logger import get_logger, LogType
from utils.config_manager import ConfigManager
import logging
logger = logging.getLogger(__name__)


class AuthenticationTester:
    """Klasa do testowania systemu autentykacji"""
    
    def __init__(self):
        self.logger = get_logger("auth_test", LogType.SECURITY)
        self.db_manager = None
        self.security_manager = SecurityManager()
        self.config_manager = ConfigManager()
        
    async def setup(self):
        """Inicjalizacja testów"""
logger.info("🔧 Inicjalizacja testów autentykacji...")
        
        # Inicjalizuj bazę danych
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        await self.db_manager.create_tables()
        
        # Wyczyść testowych użytkowników z poprzednich uruchomień
        await self.cleanup_test_users()
logger.info("✅ Baza danych zainicjalizowana")
        
    async def cleanup_test_users(self):
        """Usuwa testowych użytkowników z bazy danych"""
        try:
            conn = await self.db_manager.get_connection()
            test_usernames = ['testuser1', 'testuser2', 'admin_user']
            
            for username in test_usernames:
                await conn.execute('DELETE FROM users WHERE username = ?', (username,))
            
            await conn.commit()
logger.info("🧹 Wyczyszczono testowych użytkowników")
        except Exception as e:
            pass
logger.info(f"⚠️ Błąd podczas czyszczenia użytkowników: {e}")
        
    async def get_user_by_username(self, username: str):
        """Pomocnicza funkcja do pobierania użytkownika po nazwie"""
            pass
        try:
            conn = await self.db_manager.get_connection()
            cursor = await conn.execute('''
                SELECT id, username, password_hash, salt, email, created_at, last_login, is_active, settings
                FROM users WHERE username = ?
            ''', (username,))
            
                pass
            user = await cursor.fetchone()
            if user:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'password_hash': user['password_hash'],
                    'salt': user['salt'],
                    'email': user['email'],
                    'created_at': user['created_at'],
                    'last_login': user['last_login'],
                    'is_active': user['is_active'],
                    'settings': user['settings']
                }
            return None
        except Exception as e:
logger.info(f"Błąd podczas pobierania użytkownika {username}: {e}")
            return None
        
            pass
    async def cleanup(self):
        """Czyszczenie po testach"""
        if self.db_manager:
            await self.db_manager.close()
logger.info("🧹 Czyszczenie zakończone")
        
    async def test_user_registration(self):
        """Test rejestracji użytkowników"""
logger.info("\n🧪 Test rejestracji użytkowników")
        
        test_users = [
            ("testuser1", "SecurePass123!", "test1@example.com"),
            ("testuser2", "AnotherPass456@", "test2@example.com"),
            ("admin_user", "AdminPass789#", "admin@example.com")
        ]
            pass
                pass
        
        results = []
        
                    pass
        for username, password, email in test_users:
            try:
                # Test tworzenia użytkownika
                user_id = await self.db_manager.create_user(username, password, email)
                
                        pass
                if user_id:
                        pass
logger.info(f"✅ Utworzono użytkownika: {username} (ID: {user_id})")
                    results.append(True)
                    pass
                    
                    # Sprawdź czy użytkownik istnieje w bazie
                    user = await self.get_user_by_username(username)
                    if user:
logger.info(f"   📋 Dane użytkownika: ID={user['id']}, Email={user['email']}")
                    else:
logger.info(f"❌ Nie można pobrać danych użytkownika {username}")
                        results.append(False)
                else:
logger.info(f"❌ Nie udało się utworzyć użytkownika: {username}")
                    results.append(False)
                    
            except Exception as e:
                pass
logger.info(f"❌ Błąd podczas tworzenia użytkownika {username}: {e}")
                results.append(False)
            pass
        
        # Test duplikatu użytkownika
        try:
            duplicate_id = await self.db_manager.create_user("testuser1", "password", "test@test.com")
            if duplicate_id:
logger.info("❌ Błąd: Pozwolono na utworzenie duplikatu użytkownika")
                results.append(False)
            else:
logger.info("✅ Poprawnie odrzucono duplikat użytkownika")
                results.append(True)
        except Exception as e:
logger.info(f"✅ Poprawnie odrzucono duplikat użytkownika: {e}")
            results.append(True)
            
        return all(results)
    
            pass
    async def test_password_security(self):
        """Test bezpieczeństwa haseł"""
logger.info("\n🔐 Test bezpieczeństwa haseł")
        
        results = []
            pass
        
        # Test hashowania haseł
            pass
        test_password = "TestPassword123!"
        
        # Pobierz użytkownika z bazy
        user = await self.get_user_by_username("testuser1")
        if not user:
            pass
logger.info("❌ Nie można pobrać użytkownika do testu haseł")
            return False
            pass
            
        # Test weryfikacji hasła
        is_valid = self.db_manager.verify_password("SecurePass123!", user['password_hash'], user['salt'])
        if is_valid:
logger.info("✅ Weryfikacja poprawnego hasła działa")
            results.append(True)
        else:
logger.info("❌ Weryfikacja poprawnego hasła nie działa")
            results.append(False)
            
        # Test niepoprawnego hasła
        is_invalid = self.db_manager.verify_password("WrongPassword", user['password_hash'], user['salt'])
        if not is_invalid:
logger.info("✅ Weryfikacja niepoprawnego hasła działa")
            results.append(True)
        else:
logger.info("❌ Weryfikacja niepoprawnego hasła nie działa")
            results.append(False)
            
        # Test unikalności salt
        user2 = await self.get_user_by_username("testuser2")
        if user2 and user['salt'] != user2['salt']:
            pass
logger.info("✅ Salt jest unikalny dla każdego użytkownika")
            results.append(True)
            pass
        else:
logger.info("❌ Salt nie jest unikalny")
            results.append(False)
            
        return all(results)
            pass
    
    async def test_user_authentication(self):
            pass
        """Test autentykacji użytkowników"""
logger.info("\n🔑 Test autentykacji użytkowników")
        
        results = []
        
            pass
        # Test poprawnego logowania
        user_id = await self.db_manager.authenticate_user("testuser1", "SecurePass123!")
            pass
        if user_id:
logger.info(f"✅ Poprawne logowanie użytkownika testuser1 (ID: {user_id})")
            results.append(True)
        else:
logger.info("❌ Nie udało się zalogować użytkownika z poprawnymi danymi")
            results.append(False)
            
        # Test niepoprawnego hasła
        invalid_user = await self.db_manager.authenticate_user("testuser1", "WrongPassword")
        if not invalid_user:
logger.info("✅ Poprawnie odrzucono niepoprawne hasło")
            results.append(True)
        else:
logger.info("❌ Błąd: Zalogowano użytkownika z niepoprawnym hasłem")
            results.append(False)
            pass
            
        # Test nieistniejącego użytkownika
            pass
        nonexistent_user = await self.db_manager.authenticate_user("nonexistent", "password")
        if not nonexistent_user:
logger.info("✅ Poprawnie odrzucono nieistniejącego użytkownika")
            results.append(True)
        else:
            pass
logger.info("❌ Błąd: Zalogowano nieistniejącego użytkownika")
            results.append(False)
            pass
            
        return all(results)
    
    def test_session_management(self):
        """Test zarządzania sesjami"""
            pass
logger.info("\n🎫 Test zarządzania sesjami")
        
            pass
        results = []
        
        # Test tworzenia tokenu sesji
        user_id = 1
        session_token = self.security_manager.create_session_token(user_id)
        
            pass
        if session_token and len(session_token) > 20:
logger.info(f"✅ Utworzono token sesji: {session_token[:10]}...")
            results.append(True)
        else:
logger.info("❌ Nie udało się utworzyć tokenu sesji")
            results.append(False)
            
        # Test walidacji tokenu
        validated_user_id = self.security_manager.validate_session_token(session_token)
        if validated_user_id == user_id:
logger.info("✅ Walidacja tokenu sesji działa")
            results.append(True)
        else:
logger.info("❌ Walidacja tokenu sesji nie działa")
            results.append(False)
            
        # Test niepoprawnego tokenu
        invalid_token_result = self.security_manager.validate_session_token("invalid_token")
        if not invalid_token_result:
            pass
logger.info("✅ Poprawnie odrzucono niepoprawny token")
            results.append(True)
            pass
        else:
logger.info("❌ Błąd: Zaakceptowano niepoprawny token")
            results.append(False)
            
        # Test unieważnienia sesji
        self.security_manager.invalidate_session(session_token)
            pass
        invalidated_result = self.security_manager.validate_session_token(session_token)
        if not invalidated_result:
logger.info("✅ Unieważnienie sesji działa")
            results.append(True)
            pass
        else:
logger.info("❌ Unieważnienie sesji nie działa")
            results.append(False)
            
        return all(results)
    
    def test_failed_login_protection(self):
        """Test ochrony przed wielokrotnymi nieudanymi próbami logowania"""
            pass
logger.info("\n🛡️ Test ochrony przed wielokrotnymi nieudanymi próbami")
        
            pass
        results = []
        username = "testuser1"
        
        # Wyczyść poprzednie próby
        self.security_manager.clear_failed_login_attempts(username)
        
        # Test normalnego stanu (nie zablokowane)
        if not self.security_manager.is_account_locked(username):
logger.info("✅ Konto nie jest zablokowane na początku")
            results.append(True)
        else:
logger.info("❌ Konto jest błędnie zablokowane na początku")
            results.append(False)
            
        # Symuluj nieudane próby logowania
        max_attempts = self.config_manager.get_setting('security', 'max_login_attempts', 5)
        
        for i in range(max_attempts):
            self.security_manager.record_failed_login(username)
logger.info(f"   📝 Zarejestrowano nieudaną próbę {i+1}/{max_attempts}")
            
        # Sprawdź czy konto jest zablokowane
        if self.security_manager.is_account_locked(username):
logger.info(f"✅ Konto zablokowane po {max_attempts} nieudanych próbach")
            results.append(True)
        else:
            pass
logger.info(f"❌ Konto nie zostało zablokowane po {max_attempts} próbach")
            results.append(False)
            pass
            
        # Test czyszczenia prób
        self.security_manager.clear_failed_login_attempts(username)
        if not self.security_manager.is_account_locked(username):
logger.info("✅ Czyszczenie nieudanych prób działa")
            results.append(True)
        else:
logger.info("❌ Czyszczenie nieudanych prób nie działa")
            results.append(False)
            
        return all(results)
    
    def test_security_events_logging(self):
        """Test logowania zdarzeń bezpieczeństwa"""
            pass
logger.info("\n📋 Test logowania zdarzeń bezpieczeństwa")
        
            pass
        results = []
        
        # Test logowania zdarzenia
        self.security_manager.log_security_event(
            "LOGIN_SUCCESS", 
            user_id=1, 
            details={"ip": "127.0.0.1", "user_agent": "Test"}
        )
        
        self.security_manager.log_security_event(
            "LOGIN_FAILED", 
            user_id=None, 
            details={"username": "testuser1", "ip": "127.0.0.1"}
        )
        
        # Pobierz zdarzenia
            pass
        all_events = self.security_manager.get_security_events()
        if len(all_events) >= 2:
            pass
logger.info(f"✅ Zarejestrowano {len(all_events)} zdarzeń bezpieczeństwa")
            results.append(True)
        else:
logger.info("❌ Nie udało się zarejestrować zdarzeń")
            results.append(False)
            
        # Test filtrowania zdarzeń
        login_events = self.security_manager.get_security_events(event_type="LOGIN_SUCCESS")
        if len(login_events) >= 1:
logger.info(f"✅ Filtrowanie zdarzeń działa: {len(login_events)} zdarzeń LOGIN_SUCCESS")
                pass
            results.append(True)
        else:
                pass
logger.info("❌ Filtrowanie zdarzeń nie działa")
            results.append(False)
            pass
            
        # Test filtrowania po użytkowniku
        user_events = self.security_manager.get_security_events(user_id=1)
        if len(user_events) >= 1:
logger.info(f"✅ Filtrowanie po użytkowniku działa: {len(user_events)} zdarzeń")
            results.append(True)
        else:
logger.info("❌ Filtrowanie po użytkowniku nie działa")
            results.append(False)
            
        return all(results)
    
    def test_session_timeout(self):
        """Test wygasania sesji"""
            pass
logger.info("\n⏰ Test wygasania sesji")
        
        results = []
        
        # Utwórz sesję
        user_id = 1
        session_token = self.security_manager.create_session_token(user_id)
        
        # Sprawdź czy sesja jest aktywna
            pass
        if self.security_manager.validate_session_token(session_token):
logger.info("✅ Nowa sesja jest aktywna")
            results.append(True)
        else:
logger.info("❌ Nowa sesja nie jest aktywna")
            results.append(False)
            
        # Symuluj wygaśnięcie sesji (modyfikuj czas utworzenia)
        if session_token in self.security_manager.active_sessions:
            # Ustaw czas utworzenia na 25 godzin temu
            old_time = datetime.now() - timedelta(hours=25)
            self.security_manager.active_sessions[session_token]['created_at'] = old_time
            
            # Sprawdź czy sesja wygasła
            if not self.security_manager.validate_session_token(session_token):
logger.info("✅ Sesja poprawnie wygasła po 24 godzinach")
                results.append(True)
            else:
logger.info("❌ Sesja nie wygasła po 24 godzinach")
                results.append(False)
            pass
        else:
logger.info("❌ Nie można znaleźć sesji do testu wygaśnięcia")
            results.append(False)
            
            pass
        return all(results)
    
            pass
    async def run_all_tests(self):
        """Uruchom wszystkie testy autentykacji"""
logger.info("🚀 Rozpoczynanie testów autentykacji i uprawnień")
logger.info("=" * 60)
        
        await self.setup()
        
        test_results = []
        
        try:
            # Uruchom wszystkie testy
            test_results.append(await self.test_user_registration())
            test_results.append(await self.test_password_security())
            test_results.append(await self.test_user_authentication())
            test_results.append(self.test_session_management())
            test_results.append(self.test_failed_login_protection())
            test_results.append(self.test_security_events_logging())
            test_results.append(self.test_session_timeout())
        pass
            
        finally:
            await self.cleanup()
        
        # Podsumowanie
        pass
logger.info("\n" + "=" * 60)
logger.info("📊 PODSUMOWANIE TESTÓW AUTENTYKACJI")
logger.info("=" * 60)
        
        passed = sum(test_results)
        total = len(test_results)
        
        test_names = [
            "Rejestracja użytkowników",
            "Bezpieczeństwo haseł", 
            "Autentykacja użytkowników",
            "Zarządzanie sesjami",
            "Ochrona przed wielokrotnymi próbami",
            "Logowanie zdarzeń bezpieczeństwa",
            "Wygasanie sesji"
        ]
        
        for i, (name, result) in enumerate(zip(test_names, test_results)):
            status = "✅ PASSED" if result else "❌ FAILED"
logger.info(f"{i+1}. {name}: {status}")
logger.info(f"\nWynik końcowy: {passed}/{total} testów przeszło pomyślnie")
        
        if passed == total:
logger.info("🎉 Wszystkie testy autentykacji przeszły pomyślnie!")
            return True
        else:
logger.info("⚠️ Niektóre testy nie przeszły. Sprawdź logi powyżej.")
            return False


async def main():
    """Główna funkcja testowa"""
    tester = AuthenticationTester()
    success = await tester.run_all_tests()
    
    if success:
logger.info("\n✅ Testy autentykacji zakończone sukcesem")
        return 0
    else:
logger.info("\n❌ Testy autentykacji zakończone niepowodzeniem")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
logger.info("\n⚠️ Testy przerwane przez użytkownika")
        sys.exit(1)
    except Exception as e:
logger.info(f"\n❌ Błąd podczas testów: {e}")
        sys.exit(1)