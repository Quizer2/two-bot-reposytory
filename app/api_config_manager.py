"""Zarządzanie konfiguracją kluczy API dla giełd."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from utils.config_manager import get_config_manager
from utils.encryption import EncryptionManager
from utils.event_bus import publish as publish_event
from utils.logger import LogType, get_logger
from utils.secure_store import put_secret, delete_secret

CREDENTIALS_FILE = Path("config/exchange_credentials.json")


class APIConfigManager:
    """Manager konfiguracji API – obsługuje tryb szyfrowany i plaintext."""

    def __init__(self) -> None:
        self.logger = get_logger("api_config", LogType.SYSTEM)
        self.config_manager = get_config_manager()
        self.encryption_manager: Optional[EncryptionManager] = None
        self._master_password: Optional[str] = None

        self.config_dir = Path("config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.api_config_file = self.config_dir / "api_keys.encrypted"

        self.default_config: Dict[str, Dict[str, Any]] = {
            "binance": {"api_key": "", "secret": "", "sandbox": True, "enabled": False},
            "bybit": {"api_key": "", "secret": "", "sandbox": True, "enabled": False},
            "kucoin": {
                "api_key": "",
                "secret": "",
                "passphrase": "",
                "sandbox": True,
                "enabled": False,
            },
            "coinbase": {
                "api_key": "",
                "secret": "",
                "passphrase": "",
                "sandbox": True,
                "enabled": False,
            },
            "kraken": {"api_key": "", "secret": "", "sandbox": True, "enabled": False},
            "bitfinex": {"api_key": "", "secret": "", "sandbox": True, "enabled": False},
        }

        self.api_config: Dict[str, Dict[str, Any]] = {
            exchange: cfg.copy() for exchange, cfg in self.default_config.items()
        }

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _emit_audit(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            publish_event(f"security.{event}", payload)
        except Exception:
            pass

    def _plain_payload(self, *, mask_secrets: bool = False) -> Dict[str, Dict[str, Any]]:
        payload: Dict[str, Dict[str, Any]] = {}
        for exchange, cfg in self.api_config.items():
            key_value = cfg.get("api_key", "")
            secret_value = cfg.get("secret", "")
            passphrase_value = cfg.get("passphrase") or cfg.get("password", "")
            if mask_secrets:
                key_value = "***" if key_value else ""
                secret_value = "***" if secret_value else ""
                passphrase_value = "***" if passphrase_value else ""
            payload[exchange] = {
                "api_key": key_value,
                "secret": secret_value,
                "password": passphrase_value,
                "sandbox": bool(cfg.get("sandbox", False)),
                "enabled": bool(cfg.get("enabled", False)),
                "options": cfg.get("options", {}),
            }
        return payload

    def _persist_plaintext_credentials(self, *, mask_secrets: bool = False) -> None:
        try:
            CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with CREDENTIALS_FILE.open("w", encoding="utf-8") as handle:
                json.dump(
                    self._plain_payload(mask_secrets=mask_secrets),
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as exc:
            self.logger.error(f"Błąd zapisu credentials JSON: {exc}")
            raise

    # ------------------------------------------------------------------
    # Secure store helpers
    # ------------------------------------------------------------------
    def _persist_secure_store(self, exchange: str, config: Dict[str, Any]) -> None:
        if not self._master_password:
            return
        suffix = "_testnet" if config.get("sandbox") else ""
        key_name = f"{exchange}_api_key{suffix}"
        secret_name = f"{exchange}_api_secret{suffix}"
        passphrase_name = f"{exchange}_passphrase{suffix}"

        if config.get("api_key"):
            put_secret(key_name, config["api_key"], self._master_password)
        else:
            delete_secret(key_name)

        if config.get("secret"):
            put_secret(secret_name, config["secret"], self._master_password)
        else:
            delete_secret(secret_name)

        if config.get("passphrase"):
            put_secret(passphrase_name, config["passphrase"], self._master_password)
        else:
            delete_secret(passphrase_name)

    def _purge_secure_store(self, exchange: str) -> None:
        if not self._master_password:
            return
        for suffix in ("", "_testnet"):
            delete_secret(f"{exchange}_api_key{suffix}")
            delete_secret(f"{exchange}_api_secret{suffix}")
            delete_secret(f"{exchange}_passphrase{suffix}")

    def _sync_trading_mode(self) -> None:
        enabled = self.get_enabled_exchanges()
        if not enabled:
            self.config_manager.set_setting(
                "app",
                "trading.paper_trading",
                True,
                meta={"source": "api_config", "reason": "no_enabled_exchanges"},
            )
            self.config_manager.set_setting(
                "app",
                "trading.default_mode",
                "paper",
                meta={"source": "api_config", "reason": "no_enabled_exchanges"},
            )
        else:
            current_mode = self.config_manager.get_setting(
                "app", "trading.default_mode", "paper"
            )
            if current_mode not in {"paper", "live"}:
                self.config_manager.set_setting(
                    "app",
                    "trading.default_mode",
                    "paper",
                    meta={"source": "api_config", "reason": "invalid_mode"},
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initialize_encryption(self, master_password: str) -> bool:
        try:
            self.encryption_manager = EncryptionManager(master_password)
            self._master_password = master_password
            return True
        except Exception as exc:
            self.logger.error(f"Błąd inicjalizacji szyfrowania: {exc}")
            return False

    def clear_session_master_password(self) -> None:
        self._master_password = None

    def load_api_config(self) -> bool:
        try:
            if self.encryption_manager is None:
                if CREDENTIALS_FILE.exists():
                    with CREDENTIALS_FILE.open("r", encoding="utf-8") as handle:
                        plaintext = json.load(handle)
                    for exchange, cfg in plaintext.items():
                        if exchange in self.api_config:
                            merged = self.api_config[exchange].copy()
                            merged.update(
                                {
                                    "api_key": cfg.get("api_key", ""),
                                    "secret": cfg.get("secret", ""),
                                    "passphrase": cfg.get("password", ""),
                                    "sandbox": cfg.get("sandbox", merged.get("sandbox", False)),
                                    "enabled": cfg.get("enabled", merged.get("enabled", False)),
                                    "options": cfg.get("options", merged.get("options", {})),
                                }
                            )
                            self.api_config[exchange] = merged
                    self.logger.info("Konfiguracja API załadowana z pliku plaintext")
                    return True
                self.logger.warning(
                    "Encryption manager nie jest zainicjalizowany – używam konfiguracji domyślnej"
                )
                return True

            if not self.api_config_file.exists():
                self.logger.info("Plik konfiguracji API nie istnieje, używam domyślnej")
                return True

            encrypted_data = self.api_config_file.read_bytes()
            decrypted = self.encryption_manager.decrypt_data(encrypted_data)
            payload = json.loads(decrypted)
            if not isinstance(payload, dict):
                raise ValueError("Niepoprawny format zaszyfrowanej konfiguracji API")

            for exchange, default in self.default_config.items():
                merged = default.copy()
                merged.update(payload.get(exchange, {}))
                self.api_config[exchange] = merged

            self._persist_plaintext_credentials(mask_secrets=True)
            self.logger.info("Konfiguracja API załadowana pomyślnie")
            return True

        except Exception as exc:
            self.logger.error(f"Błąd ładowania konfiguracji API: {exc}")
            self.api_config = {exchange: cfg.copy() for exchange, cfg in self.default_config.items()}
            try:
                self._persist_plaintext_credentials(mask_secrets=self.encryption_manager is not None)
            except Exception:
                pass
            return False

    def save_api_config(self) -> bool:
        try:
            if self.encryption_manager is None:
                self.logger.warning(
                    "Encryption manager nie jest zainicjalizowany – zapisuję konfigurację w pliku plaintext"
                )
                self._persist_plaintext_credentials()
                self._sync_trading_mode()
                return True

            payload = json.dumps(self.api_config, indent=2)
            encrypted = self.encryption_manager.encrypt_data(payload)
            self.api_config_file.write_bytes(encrypted)
            self._persist_plaintext_credentials(mask_secrets=True)
            self.logger.info("Konfiguracja API zapisana pomyślnie")
            self._sync_trading_mode()
            return True

        except Exception as exc:
            self.logger.error(f"Błąd zapisywania konfiguracji API: {exc}")
            try:
                self._persist_plaintext_credentials(mask_secrets=self.encryption_manager is not None)
            except Exception:
                pass
            return False

    def get_exchange_config(self, exchange: str) -> Optional[Dict[str, Any]]:
        return self.api_config.get(exchange.lower())

    def set_exchange_config(self, exchange: str, config: Dict[str, Any]) -> bool:
        try:
            exchange = exchange.lower()
            if exchange not in self.default_config:
                self.logger.error(f"Nieznana giełda: {exchange}")
                return False

            required_fields = set(self.default_config[exchange].keys())
            missing = required_fields - set(config.keys())
            if missing:
                self.logger.error(f"Brakuje pól {sorted(missing)} dla giełdy {exchange}")
                return False

            prev = self.api_config.get(exchange, {}).copy()
            self.api_config[exchange] = config
            ok = self.save_api_config()
            if ok:
                self._emit_audit(
                    "keys.updated",
                    {
                        "exchange": exchange,
                        "enabled": bool(config.get("enabled")),
                        "sandbox": bool(config.get("sandbox")),
                        "had_prev": bool(prev.get("api_key") or prev.get("secret") or prev.get("passphrase")),
                        "has_new": bool(config.get("api_key") or config.get("secret") or config.get("passphrase")),
                    },
                )
                self._persist_secure_store(exchange, config)
            return ok
        except Exception as exc:
            self.logger.error(f"Błąd ustawiania konfiguracji dla {exchange}: {exc}")
            return False

    def enable_exchange(self, exchange: str) -> bool:
        try:
            exchange = exchange.lower()
            if exchange in self.api_config:
                previously_enabled = bool(self.api_config[exchange].get("enabled"))
                self.api_config[exchange]["enabled"] = True
                ok = self.save_api_config()
                if ok and not previously_enabled:
                    self._emit_audit("exchange.enabled", {"exchange": exchange})
                return ok
            return False
        except Exception as exc:
            self.logger.error(f"Błąd włączania giełdy {exchange}: {exc}")
            return False

    def disable_exchange(self, exchange: str) -> bool:
        try:
            exchange = exchange.lower()
            if exchange in self.api_config:
                previously_enabled = bool(self.api_config[exchange].get("enabled"))
                self.api_config[exchange]["enabled"] = False
                ok = self.save_api_config()
                if ok and previously_enabled:
                    self._emit_audit("exchange.disabled", {"exchange": exchange})
                return ok
            return False
        except Exception as exc:
            self.logger.error(f"Błąd wyłączania giełdy {exchange}: {exc}")
            return False

    def get_enabled_exchanges(self) -> list[str]:
        return [
            exchange
            for exchange, cfg in self.api_config.items()
            if cfg.get("enabled") and cfg.get("api_key", "").strip()
        ]

    def validate_exchange_config(self, exchange: str) -> bool:
        try:
            cfg = self.get_exchange_config(exchange)
            if not cfg:
                return False
            if not cfg.get("api_key", "").strip():
                return False
            if not cfg.get("secret", "").strip():
                return False
            if exchange.lower() in {"kucoin", "coinbase"} and not cfg.get("passphrase", "").strip():
                return False
            return True
        except Exception as exc:
            self.logger.error(f"Błąd walidacji konfiguracji {exchange}: {exc}")
            return False

    def clear_exchange_config(self, exchange: str) -> bool:
        try:
            exchange = exchange.lower()
            if exchange in self.default_config:
                self.api_config[exchange] = self.default_config[exchange].copy()
                ok = self.save_api_config()
                if ok:
                    self._emit_audit("keys.cleared", {"exchange": exchange})
                    self._purge_secure_store(exchange)
                return ok
            return False
        except Exception as exc:
            self.logger.error(f"Błąd czyszczenia konfiguracji {exchange}: {exc}")
            return False

    def remove_exchange_config(self, exchange: str) -> bool:
        try:
            exchange = exchange.lower()
            if exchange in self.api_config:
                del self.api_config[exchange]
                ok = self.save_api_config()
                if ok:
                    self._emit_audit("keys.removed", {"exchange": exchange})
                    self._purge_secure_store(exchange)
                return ok
            return False
        except Exception as exc:
            self.logger.error(f"Błąd usuwania konfiguracji {exchange}: {exc}")
            return False

    def get_all_exchanges(self) -> list[str]:
        return list(self.default_config.keys())

    def get_available_exchanges(self) -> list[str]:
        return self.get_all_exchanges()

    def is_production_ready(self) -> bool:
        enabled = self.get_enabled_exchanges()
        if not enabled:
            return False
        return any(self.validate_exchange_config(exchange) for exchange in enabled)

    def rotate_keys(
        self,
        exchange: str,
        *,
        keep_enabled: Optional[bool] = None,
        sandbox: Optional[bool] = None,
    ) -> bool:
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
                self._emit_audit(
                    "keys.rotated",
                    {
                        "exchange": exchange,
                        "enabled": bool(cfg.get("enabled")),
                        "sandbox": bool(cfg.get("sandbox")),
                    },
                )
                self._purge_secure_store(exchange)
            return ok
        except Exception as exc:
            self.logger.error(f"Błąd rotacji kluczy {exchange}: {exc}")
            return False


_api_config_manager: Optional[APIConfigManager] = None


def get_api_config_manager() -> APIConfigManager:
    """Zwraca singleton instance API Config Manager."""

    global _api_config_manager
    if _api_config_manager is None:
        _api_config_manager = APIConfigManager()
    return _api_config_manager

