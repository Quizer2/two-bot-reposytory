"""
Moduł zarządzania konfiguracją API dla różnych giełd

Umożliwia bezpieczne przechowywanie i zarządzanie kluczami API
dla różnych giełd kryptowalut.
"""

import json
import os
from typing import Dict, Optional, Any
from pathlib import Path

from utils.encryption import EncryptionManager
from utils.logger import get_logger, LogType
from utils.config_manager import get_config_manager
from utils.event_bus import publish as publish_event


class APIConfigManager:
    """Manager konfiguracji API dla giełd"""
    
    def __init__(self):
        self.logger = get_logger("api_config", LogType.SYSTEM)
        self.config_manager = get_config_manager()
        self.encryption_manager = None
        
        # Ścieżka do pliku z konfiguracją API
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.api_config_file = self.config_dir / "api_keys.encrypted"
        
        # Domyślna konfiguracja
        self.default_config = {
            "binance": {
                "api_key": "",
                "secret": "",
                "sandbox": True,
                "enabled": False
            },
            "bybit": {
                "api_key": "",
                "secret": "",
                "sandbox": True,
                "enabled": False
            },
            "kucoin": {
                "api_key": "",
                "secret": "",
                "passphrase": "",
                "sandbox": True,
                "enabled": False
            },
            "coinbase": {
                "api_key": "",
                "secret": "",
                "passphrase": "",
                "sandbox": True,
                "enabled": False
            },
            "kraken": {
                "api_key": "",
                "secret": "",
                "sandbox": True,
                "enabled": False
            },
            "bitfinex": {
                "api_key": "",
                "secret": "",
                "sandbox": True,
                "enabled": False
            }
        }
        
        self.api_config = self.default_config.copy()

    def _emit_audit(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            publish_event("security." + event, payload)
        except Exception:
            pass
    
    def initialize_encryption(self, master_password: str) -> bool:
        """Inicjalizuje szyfrowanie z hasłem głównym"""
        try:
            self.encryption_manager = EncryptionManager(master_password)
            return True
        except Exception as e:
            self.logger.error(f"Błąd inicjalizacji szyfrowania: {e}")
            return False
    
    def load_api_config(self) -> bool:
        """Ładuje zaszyfrowaną konfigurację API"""
        try:
            if not self.encryption_manager:
                self.logger.warning("Encryption manager nie jest zainicjalizowany")
                return False
            
            if not self.api_config_file.exists():
                self.logger.info("Plik konfiguracji API nie istnieje, używam domyślnej")
                return True
            
            # Odczytaj zaszyfrowane dane
            encrypted_data = self.api_config_file.read_bytes()
            
            # Odszyfruj
            decrypted_data = self.encryption_manager.decrypt_data(encrypted_data)
            
            # Parsuj JSON
            self.api_config = json.loads(decrypted_data)
            
            # Sprawdź czy wszystkie wymagane klucze istnieją
            for exchange in self.default_config:
                if exchange not in self.api_config:
                    self.api_config[exchange] = self.default_config[exchange].copy()
            
            self.logger.info("Konfiguracja API załadowana pomyślnie")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania konfiguracji API: {e}")
            self.api_config = self.default_config.copy()
            return False
    
    def save_api_config(self) -> bool:
        """Zapisuje zaszyfrowaną konfigurację API"""
        try:
            if not self.encryption_manager:
                self.logger.error("Encryption manager nie jest zainicjalizowany")
                return False
            
            # Konwertuj do JSON
            json_data = json.dumps(self.api_config, indent=2)
            
            # Zaszyfruj
            encrypted_data = self.encryption_manager.encrypt_data(json_data)
            
            # Zapisz do pliku
            self.api_config_file.write_bytes(encrypted_data)
            
            self.logger.info("Konfiguracja API zapisana pomyślnie")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd zapisywania konfiguracji API: {e}")
            return False
    
    def get_exchange_config(self, exchange: str) -> Optional[Dict[str, Any]]:
        """Pobiera konfigurację dla konkretnej giełdy"""
        return self.api_config.get(exchange.lower())
    
    def set_exchange_config(self, exchange: str, config: Dict[str, Any]) -> bool:
        """Ustawia konfigurację dla konkretnej giełdy"""
        try:
            exchange = exchange.lower()
            
            if exchange not in self.default_config:
                self.logger.error(f"Nieznana giełda: {exchange}")
                return False
            
            # Waliduj wymagane pola
            required_fields = list(self.default_config[exchange].keys())
            for field in required_fields:
                if field not in config:
                    self.logger.error(f"Brakuje pola {field} dla giełdy {exchange}")
                    return False
            
            prev = self.api_config.get(exchange, {}).copy()
            self.api_config[exchange] = config
            ok = self.save_api_config()
            if ok:
                # Audyt bez sekretów
                self._emit_audit("keys.updated", {
                    "exchange": exchange,
                    "enabled": bool(config.get("enabled")),
                    "sandbox": bool(config.get("sandbox")),
                    "had_prev": bool(prev.get("api_key") or prev.get("secret") or prev.get("passphrase")),
                    "has_new": bool(config.get("api_key") or config.get("secret") or config.get("passphrase")),
                })
            return ok
            
        except Exception as e:
            self.logger.error(f"Błąd ustawiania konfiguracji dla {exchange}: {e}")
            return False
    
    def enable_exchange(self, exchange: str) -> bool:
        """Włącza giełdę"""
        try:
            exchange = exchange.lower()
            if exchange in self.api_config:
                prev = bool(self.api_config[exchange].get("enabled"))
                self.api_config[exchange]["enabled"] = True
                ok = self.save_api_config()
                if ok and not prev:
                    self._emit_audit("exchange.enabled", {"exchange": exchange})
                return ok
            return False
        except Exception as e:
            self.logger.error(f"Błąd włączania giełdy {exchange}: {e}")
            return False
    
    def disable_exchange(self, exchange: str) -> bool:
        """Wyłącza giełdę"""
        try:
            exchange = exchange.lower()
            if exchange in self.api_config:
                prev = bool(self.api_config[exchange].get("enabled"))
                self.api_config[exchange]["enabled"] = False
                ok = self.save_api_config()
                if ok and prev:
                    self._emit_audit("exchange.disabled", {"exchange": exchange})
                return ok
            return False
        except Exception as e:
            self.logger.error(f"Błąd wyłączania giełdy {exchange}: {e}")
            return False
    
    def get_enabled_exchanges(self) -> list:
        """Zwraca listę włączonych giełd"""
        return [
            exchange for exchange, config in self.api_config.items()
            if config.get("enabled", False) and config.get("api_key", "").strip()
        ]
    
    def validate_exchange_config(self, exchange: str) -> bool:
        """Waliduje konfigurację giełdy"""
        try:
            config = self.get_exchange_config(exchange)
            if not config:
                return False
            
            # Sprawdź czy API key i secret są ustawione
            if not config.get("api_key", "").strip():
                return False
            
            if not config.get("secret", "").strip():
                return False
            
            # Dla KuCoin i Coinbase sprawdź passphrase
            if exchange.lower() in ["kucoin", "coinbase"]:
                if not config.get("passphrase", "").strip():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd walidacji konfiguracji {exchange}: {e}")
            return False
    
    def clear_exchange_config(self, exchange: str) -> bool:
        """Czyści konfigurację giełdy (przywraca domyślną)"""
        try:
            exchange = exchange.lower()
            if exchange in self.default_config:
                self.api_config[exchange] = self.default_config[exchange].copy()
                ok = self.save_api_config()
                if ok:
                    self._emit_audit("keys.cleared", {"exchange": exchange})
                return ok
            return False
        except Exception as e:
            self.logger.error(f"Błąd czyszczenia konfiguracji {exchange}: {e}")
            return False
    
    def remove_exchange_config(self, exchange: str) -> bool:
        """Usuwa konfigurację giełdy całkowicie"""
        try:
            exchange = exchange.lower()
            if exchange in self.api_config:
                del self.api_config[exchange]
                ok = self.save_api_config()
                if ok:
                    self._emit_audit("keys.removed", {"exchange": exchange})
                return ok
            return False
        except Exception as e:
            self.logger.error(f"Błąd usuwania konfiguracji {exchange}: {e}")
            return False
    
    def get_all_exchanges(self) -> list:
        """Zwraca listę wszystkich dostępnych giełd"""
        return list(self.default_config.keys())
    
    def get_available_exchanges(self) -> list:
        """Zwraca listę wszystkich dostępnych giełd (alias dla get_all_exchanges)"""
        return self.get_all_exchanges()
    
    def is_production_ready(self) -> bool:
        """Sprawdza czy aplikacja jest gotowa do trybu produkcyjnego"""
        enabled_exchanges = self.get_enabled_exchanges()
        
        if not enabled_exchanges:
            return False
        
        # Sprawdź czy przynajmniej jedna giełda ma poprawną konfigurację
        for exchange in enabled_exchanges:
            if self.validate_exchange_config(exchange):
                return True
        
        return False

    # --- key rotation helper (no secrets in payload) ---
    def rotate_keys(self, exchange: str, *, keep_enabled: Optional[bool] = None, sandbox: Optional[bool] = None) -> bool:
        try:
            exchange = exchange.lower()
            if exchange not in self.api_config:
                self.logger.error(f"Nieznana giełda: {exchange}")
                return False
            cfg = self.api_config[exchange]
            cfg["api_key"] = ""
            cfg["secret"] = ""
            if "passphrase" in cfg:
                cfg["passphrase"] = ""
            if keep_enabled is not None:
                cfg["enabled"] = bool(keep_enabled)
            if sandbox is not None:
                cfg["sandbox"] = bool(sandbox)
            ok = self.save_api_config()
            if ok:
                self._emit_audit("keys.rotated", {"exchange": exchange, "enabled": bool(cfg.get("enabled")), "sandbox": bool(cfg.get("sandbox"))})
            return ok
        except Exception as e:
            self.logger.error(f"Błąd rotacji kluczy {exchange}: {e}")
            return False


# Singleton instance
_api_config_manager = None

def get_api_config_manager() -> APIConfigManager:
    """Zwraca singleton instance API Config Manager"""
    global _api_config_manager
    if _api_config_manager is None:
        _api_config_manager = APIConfigManager()
    return _api_config_manager