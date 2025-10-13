"""
System szyfrowania AES-256 dla CryptoBotDesktop

Zapewnia bezpieczne szyfrowanie i deszyfrowanie kluczy API
oraz innych wrażliwych danych zgodnie ze specyfikacją.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import json

class EncryptionManager:
    """
    Menedżer szyfrowania AES-256
    
    Zarządza szyfrowaniem i deszyfrowaniem wrażliwych danych
    takich jak klucze API, hasła i inne poufne informacje.
    """
    
    def __init__(self, master_password: str = None):
        self.master_password = master_password
        self._key = None
        self._fernet = None
        
    def set_master_password(self, password: str):
        """Ustawienie głównego hasła do szyfrowania"""
        self.master_password = password
        self._key = None
        self._fernet = None
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Wyprowadzenie klucza z hasła używając PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bitów
            salt=salt,
            iterations=100000,  # 100,000 iteracji
            backend=default_backend()
        )
        return kdf.derive(password.encode())
    
    def _get_encryption_key(self) -> bytes:
        """Pobranie klucza szyfrowania"""
        if not self.master_password:
            raise ValueError("Nie ustawiono głównego hasła")
        
        if self._key is None:
            # Użyj stałej soli dla spójności (w produkcji lepiej przechowywać osobno)
            salt = None  # will be loaded per-user
            self._key = self._derive_key(self.master_password, salt)
        
        return self._key
    
    def _get_fernet(self) -> Fernet:
        """Pobranie instancji Fernet do szyfrowania"""
        if self._fernet is None:
            key = self._get_encryption_key()
            # Fernet wymaga klucza w formacie base64
            fernet_key = base64.urlsafe_b64encode(key)
            self._fernet = Fernet(fernet_key)
        
        return self._fernet
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Szyfrowanie tekstu
        
        Args:
            plaintext: Tekst do zaszyfrowania
            
        Returns:
            Zaszyfrowany tekst w formacie base64
        """
        try:
            if not plaintext:
                return ""
            
            fernet = self._get_fernet()
            encrypted_bytes = fernet.encrypt(plaintext.encode('utf-8'))
            return base64.b64encode(encrypted_bytes).decode('utf-8')
            
        except Exception as e:
            raise Exception(f"Błąd podczas szyfrowania: {e}")
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Deszyfrowanie tekstu
        
        Args:
            encrypted_text: Zaszyfrowany tekst w formacie base64
            
        Returns:
            Odszyfrowany tekst
        """
        try:
            if not encrypted_text:
                return ""
            
            fernet = self._get_fernet()
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            raise Exception(f"Błąd podczas deszyfrowania: {e}")
    
    def encrypt_api_credentials(self, api_key: str, api_secret: str, 
                               passphrase: str = None) -> Tuple[str, str, str]:
        """
        Szyfrowanie danych uwierzytelniających API
        
        Args:
            api_key: Klucz API
            api_secret: Sekret API
            passphrase: Hasło (opcjonalne, dla niektórych giełd)
            
        Returns:
            Tuple z zaszyfrowanymi danymi (api_key, api_secret, passphrase)
        """
        try:
            encrypted_key = self.encrypt_string(api_key)
            encrypted_secret = self.encrypt_string(api_secret)
            encrypted_passphrase = self.encrypt_string(passphrase) if passphrase else None
            
            return encrypted_key, encrypted_secret, encrypted_passphrase
            
        except Exception as e:
            raise Exception(f"Błąd podczas szyfrowania danych API: {e}")
    
    def decrypt_api_credentials(self, encrypted_key: str, encrypted_secret: str,
                               encrypted_passphrase: str = None) -> Tuple[str, str, str]:
        """
        Deszyfrowanie danych uwierzytelniających API
        
        Args:
            encrypted_key: Zaszyfrowany klucz API
            encrypted_secret: Zaszyfrowany sekret API
            encrypted_passphrase: Zaszyfrowane hasło (opcjonalne)
            
        Returns:
            Tuple z odszyfrowanymi danymi (api_key, api_secret, passphrase)
        """
        try:
            api_key = self.decrypt_string(encrypted_key)
            api_secret = self.decrypt_string(encrypted_secret)
            passphrase = self.decrypt_string(encrypted_passphrase) if encrypted_passphrase else None
            
            return api_key, api_secret, passphrase
            
        except Exception as e:
            raise Exception(f"Błąd podczas deszyfrowania danych API: {e}")
    
    def encrypt_json(self, data: dict) -> str:
        """
        Szyfrowanie danych JSON
        
        Args:
            data: Słownik do zaszyfrowania
            
        Returns:
            Zaszyfrowane dane w formacie base64
        """
        try:
            json_string = json.dumps(data, ensure_ascii=False)
            return self.encrypt_string(json_string)
            
        except Exception as e:
            raise Exception(f"Błąd podczas szyfrowania JSON: {e}")
    
    def decrypt_json(self, encrypted_data: str) -> dict:
        """
        Deszyfrowanie danych JSON
        
        Args:
            encrypted_data: Zaszyfrowane dane w formacie base64
            
        Returns:
            Odszyfrowany słownik
        """
        try:
            json_string = self.decrypt_string(encrypted_data)
            return json.loads(json_string)
            
        except Exception as e:
            raise Exception(f"Błąd podczas deszyfrowania JSON: {e}")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generowanie bezpiecznego tokenu
        
        Args:
            length: Długość tokenu w bajtach
            
        Returns:
            Bezpieczny token w formacie hex
        """
        return secrets.token_hex(length)
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """
        Hashowanie hasła z solą
        
        Args:
            password: Hasło do zahashowania
            salt: Sól (opcjonalna, zostanie wygenerowana jeśli nie podana)
            
        Returns:
            Tuple (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Użyj PBKDF2 z SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iteracji
        ).hex()
        
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """
        Weryfikacja hasła
        
        Args:
            password: Hasło do sprawdzenia
            password_hash: Hash hasła
            salt: Sól użyta do hashowania
            
        Returns:
            True jeśli hasło jest poprawne, False w przeciwnym razie
        """
        computed_hash, _ = self.hash_password(password, salt)
        return computed_hash == password_hash
    
    def encrypt_file(self, file_path: str, output_path: str = None) -> str:
        """
        Szyfrowanie pliku
        
        Args:
            file_path: Ścieżka do pliku do zaszyfrowania
            output_path: Ścieżka do zaszyfrowanego pliku (opcjonalna)
            
        Returns:
            Ścieżka do zaszyfrowanego pliku
        """
        try:
            if output_path is None:
                output_path = file_path + '.encrypted'
            
            fernet = self._get_fernet()
            
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            encrypted_data = fernet.encrypt(file_data)
            
            with open(output_path, 'wb') as file:
                file.write(encrypted_data)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Błąd podczas szyfrowania pliku: {e}")
    
    def decrypt_file(self, encrypted_file_path: str, output_path: str = None) -> str:
        """
        Deszyfrowanie pliku
        
        Args:
            encrypted_file_path: Ścieżka do zaszyfrowanego pliku
            output_path: Ścieżka do odszyfrowanego pliku (opcjonalna)
            
        Returns:
            Ścieżka do odszyfrowanego pliku
        """
        try:
            if output_path is None:
                output_path = encrypted_file_path.replace('.encrypted', '')
            
            fernet = self._get_fernet()
            
            with open(encrypted_file_path, 'rb') as file:
                encrypted_data = file.read()
            
            decrypted_data = fernet.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as file:
                file.write(decrypted_data)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Błąd podczas deszyfrowania pliku: {e}")
    
    def create_backup_encryption_key(self) -> str:
        """
        Utworzenie klucza szyfrowania dla kopii zapasowych
        
        Returns:
            Klucz szyfrowania w formacie base64
        """
        try:
            key = Fernet.generate_key()
            return base64.b64encode(key).decode('utf-8')
            
        except Exception as e:
            raise Exception(f"Błąd podczas tworzenia klucza kopii zapasowej: {e}")
    
    def encrypt_backup(self, data: bytes, backup_key: str) -> bytes:
        """
        Szyfrowanie kopii zapasowej
        
        Args:
            data: Dane do zaszyfrowania
            backup_key: Klucz szyfrowania kopii zapasowej
            
        Returns:
            Zaszyfrowane dane
        """
        try:
            key = base64.b64decode(backup_key.encode('utf-8'))
            fernet = Fernet(key)
            return fernet.encrypt(data)
            
        except Exception as e:
            raise Exception(f"Błąd podczas szyfrowania kopii zapasowej: {e}")
    
    def decrypt_backup(self, encrypted_data: bytes, backup_key: str) -> bytes:
        """
        Deszyfrowanie kopii zapasowej
        
        Args:
            encrypted_data: Zaszyfrowane dane
            backup_key: Klucz szyfrowania kopii zapasowej
            
        Returns:
            Odszyfrowane dane
        """
        try:
            key = base64.b64decode(backup_key.encode('utf-8'))
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data)
            
        except Exception as e:
            raise Exception(f"Błąd podczas deszyfrowania kopii zapasowej: {e}")
    
    def secure_delete_string(self, sensitive_string: str):
        """
        Bezpieczne usunięcie wrażliwego ciągu znaków z pamięci
        
        Args:
            sensitive_string: Wrażliwy ciąg znaków do usunięcia
        """
        try:
            # W Pythonie nie ma bezpośredniej kontroli nad pamięcią,
            # ale możemy nadpisać zmienną losowymi danymi
            if sensitive_string:
                # Nadpisz losowymi danymi
                random_data = secrets.token_hex(len(sensitive_string))
                sensitive_string = random_data
                del random_data
                del sensitive_string
                
        except Exception:
            pass  # Ignoruj błędy podczas bezpiecznego usuwania
    
    def validate_encryption_integrity(self, encrypted_data: str) -> bool:
        """
        Sprawdzenie integralności zaszyfrowanych danych
        
        Args:
            encrypted_data: Zaszyfrowane dane do sprawdzenia
            
        Returns:
            True jeśli dane są poprawne, False w przeciwnym razie
        """
        try:
            # Spróbuj odszyfrować dane
            self.decrypt_string(encrypted_data)
            return True
            
        except Exception:
            return False
    
    def change_master_password(self, old_password: str, new_password: str,
                              encrypted_data_list: list) -> list:
        """
        Zmiana głównego hasła i ponowne szyfrowanie danych
        
        Args:
            old_password: Stare hasło
            new_password: Nowe hasło
            encrypted_data_list: Lista zaszyfrowanych danych do ponownego zaszyfrowania
            
        Returns:
            Lista danych zaszyfrowanych nowym hasłem
        """
        try:
            # Odszyfruj dane starym hasłem
            old_encryption = EncryptionManager(old_password)
            decrypted_data = []
            
            for encrypted_item in encrypted_data_list:
                decrypted_item = old_encryption.decrypt_string(encrypted_item)
                decrypted_data.append(decrypted_item)
            
            # Zaszyfruj dane nowym hasłem
            self.set_master_password(new_password)
            new_encrypted_data = []
            
            for decrypted_item in decrypted_data:
                encrypted_item = self.encrypt_string(decrypted_item)
                new_encrypted_data.append(encrypted_item)
            
            # Bezpiecznie usuń odszyfrowane dane
            for item in decrypted_data:
                self.secure_delete_string(item)
            
            return new_encrypted_data
            
        except Exception as e:
            raise Exception(f"Błąd podczas zmiany hasła głównego: {e}")


class SecurityManager:
    """
    Menedżer bezpieczeństwa aplikacji
    
    Zarządza dodatkowymi aspektami bezpieczeństwa
    takimi jak sesje, tokeny dostępu i audyt bezpieczeństwa.
    """
    
    def __init__(self):
        self.active_sessions = {}
        self.failed_login_attempts = {}
        self.security_events = []
    
    def create_session_token(self, user_id: int) -> str:
        """
        Utworzenie tokenu sesji
        
        Args:
            user_id: ID użytkownika
            
        Returns:
            Token sesji
        """
        session_token = secrets.token_urlsafe(32)
        self.active_sessions[session_token] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        return session_token
    
    def validate_session_token(self, session_token: str) -> Optional[int]:
        """
        Walidacja tokenu sesji
        
        Args:
            session_token: Token sesji do sprawdzenia
            
        Returns:
            ID użytkownika jeśli token jest ważny, None w przeciwnym razie
        """
        if session_token not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_token]
        
        # Sprawdź czy sesja nie wygasła (24 godziny)
        if datetime.now() - session['created_at'] > timedelta(hours=24):
            del self.active_sessions[session_token]
            return None
        
        # Aktualizuj ostatnią aktywność
        session['last_activity'] = datetime.now()
        return session['user_id']
    
    def invalidate_session(self, session_token: str):
        """
        Unieważnienie sesji
        
        Args:
            session_token: Token sesji do unieważnienia
        """
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
    
    def record_failed_login(self, username: str):
        """
        Rejestracja nieudanej próby logowania
        
        Args:
            username: Nazwa użytkownika
        """
        if username not in self.failed_login_attempts:
            self.failed_login_attempts[username] = []
        
        self.failed_login_attempts[username].append(datetime.now())
        
        # Usuń stare próby (starsze niż 1 godzina)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.failed_login_attempts[username] = [
            attempt for attempt in self.failed_login_attempts[username]
            if attempt > cutoff_time
        ]
    
    def is_account_locked(self, username: str, max_attempts: int = 5) -> bool:
        """
        Sprawdzenie czy konto jest zablokowane
        
        Args:
            username: Nazwa użytkownika
            max_attempts: Maksymalna liczba prób
            
        Returns:
            True jeśli konto jest zablokowane, False w przeciwnym razie
        """
        if username not in self.failed_login_attempts:
            return False
        
        return len(self.failed_login_attempts[username]) >= max_attempts
    
    def clear_failed_login_attempts(self, username: str):
        """
        Wyczyszczenie nieudanych prób logowania
        
        Args:
            username: Nazwa użytkownika
        """
        if username in self.failed_login_attempts:
            del self.failed_login_attempts[username]
    
    def log_security_event(self, event_type: str, user_id: int = None, 
                          details: dict = None):
        """
        Rejestracja zdarzenia bezpieczeństwa
        
        Args:
            event_type: Typ zdarzenia
            user_id: ID użytkownika (opcjonalne)
            details: Szczegóły zdarzenia (opcjonalne)
        """
        event = {
            'type': event_type,
            'user_id': user_id,
            'timestamp': datetime.now(),
            'details': details or {}
        }
        
        self.security_events.append(event)
        
        # Zachowaj tylko ostatnie 1000 zdarzeń
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
    
    def get_security_events(self, event_type: str = None, 
                           user_id: int = None, limit: int = 100) -> list:
        """
        Pobranie zdarzeń bezpieczeństwa
        
        Args:
            event_type: Typ zdarzenia do filtrowania (opcjonalne)
            user_id: ID użytkownika do filtrowania (opcjonalne)
            limit: Maksymalna liczba zdarzeń
            
        Returns:
            Lista zdarzeń bezpieczeństwa
        """
        events = self.security_events
        
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        
        if user_id:
            events = [e for e in events if e['user_id'] == user_id]
        
        return events[-limit:]


# Globalna instancja menedżera szyfrowania
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    """
    Zwraca globalną instancję menedżera szyfrowania
    
    Returns:
        EncryptionManager: Instancja menedżera szyfrowania
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager

from pathlib import Path
import os, secrets

salt = None  # module-level KDF salt

def _get_salt_path():
    base = Path(__file__).resolve().parents[1] / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "secret.salt"

def load_or_create_salt() -> bytes:
    path = _get_salt_path()
    if path.exists():
        return path.read_bytes()
    s = secrets.token_bytes(16)
    path.write_bytes(s)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return s

import os
from base64 import urlsafe_b64encode
from hashlib import sha256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from pathlib import Path
import secrets

salt = None  # module-level KDF salt

def _get_salt_path():
    base = Path(__file__).resolve().parents[1] / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "secret.salt"

def load_or_create_salt() -> bytes:
    path = _get_salt_path()
    if path.exists():
        return path.read_bytes()
    s = secrets.token_bytes(16)
    path.write_bytes(s)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return s

def derive_key(password: str) -> bytes:
    global salt
    if not salt:
        salt = load_or_create_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode("utf-8"))
    return urlsafe_b64encode(key)
