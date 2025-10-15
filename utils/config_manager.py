"""
Menedżer konfiguracji dla CryptoBotDesktop

Zarządza ładowaniem, zapisywaniem i walidacją
plików konfiguracyjnych aplikacji.
"""

import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import copy
import logging
from .event_bus import get_event_bus, EventTypes

logger = logging.getLogger(__name__)

@dataclass
class ConfigValidationError(Exception):
    """Błąd walidacji konfiguracji"""
    message: str
    config_file: str
    field: str = None

class ConfigManager:
    """
    Menedżer konfiguracji aplikacji
    
    Zarządza ładowaniem i zapisywaniem plików konfiguracyjnych,
    walidacją ustawień oraz dostarczaniem domyślnych wartości.
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Ścieżki do plików konfiguracyjnych
        self.app_config_path = self.config_dir / "app_config.json"
        self.ui_config_path = self.config_dir / "ui_config.json"
        
        # Załadowane konfiguracje
        self._app_config = None
        self._ui_config = None
        
        # Domyślne konfiguracje (backup)
        self._default_app_config = self._get_default_app_config()
        self._default_ui_config = self._get_default_ui_config()
        
        # EventBus dla powiadomień o zmianach konfiguracji
        self.event_bus = get_event_bus()

        # Lokalni listenerzy (namespace -> callbacks)
        self._listeners = defaultdict(list)  # type: Dict[str, List[Callable]]
        self._listener_lock = threading.RLock()
    
    def _get_default_app_config(self) -> Dict[str, Any]:
        """Zwraca domyślną konfigurację aplikacji"""
        return {
            "app": {
                "name": "CryptoBotDesktop",
                "version": "1.0.0",
                "debug": False,
                "auto_start_bots": False,
                "auto_restart_bots": True,
                "offline_mode": False,
                "language": "pl",
                "timezone": "Europe/Warsaw"
            },
            "database": {
                "path": "data/database.db",
                "backup_interval_hours": 24,
                "max_backups": 7,
                "auto_backup": True,
                "backup_path": "data/backup"
            },
            "logging": {
                "level": "INFO",
                "max_file_size_mb": 10,
                "max_files": 5,
                "log_to_console": True,
                "log_to_file": True,
                "log_to_database": True,
                "cleanup_days": 30
            },
            "security": {
                "session_timeout_minutes": 60,
                "max_login_attempts": 5,
                "lockout_duration_minutes": 15,
                "require_password_change_days": 90,
                "min_password_length": 8,
                "encryption_algorithm": "AES-256",
                "auto_lock_minutes": 30
            },
            "exchanges": {
                "default": "binance",
                "available": ["binance", "bybit", "kucoin", "coinbase", "kraken", "bitfinex"]
            },
            "trading": {
                "default_quote_currency": "USDT",
                "min_order_amount": 10.0,
                "max_order_amount": 10000.0,
                "default_stop_loss_percent": 5.0,
                "default_take_profit_percent": 10.0,
                "max_open_positions": 10,
                "paper_trading": False,
                "slippage_tolerance_percent": 0.5,
                "supported_pairs": [
                    "BTC/USDT",
                    "ETH/USDT",
                    "BNB/USDT",
                    "SOL/USDT",
                    "ADA/USDT",
                    "XRP/USDT",
                    "DOT/USDT",
                    "MATIC/USDT",
                    "DOGE/USDT",
                    "LTC/USDT",
                    "AVAX/USDT",
                    "LINK/USDT",
                    "BTC/EUR",
                    "ETH/EUR",
                    "BTC/USD",
                    "ETH/USD",
                    "BTC/GBP",
                    "ETH/GBP",
                    "ADA/EUR"
                ]
            }
        }
    
    def _get_default_ui_config(self) -> Dict[str, Any]:
        """Zwraca domyślną konfigurację UI"""
        return {
            "theme": {
                "current": "dark",
                "available": ["light", "dark", "auto"],
                "auto_switch": False
            },
            "window": {
                "default_width": 1200,
                "default_height": 800,
                "min_width": 800,
                "min_height": 600,
                "remember_size": True,
                "remember_position": True,
                "start_maximized": False
            },
            "dashboard": {
                "refresh_interval_seconds": 5,
                "show_portfolio_summary": True,
                "show_active_bots": True,
                "show_recent_trades": True,
                "max_recent_trades": 10
            },
            "notifications": {
                "position": "top-right",
                "duration_seconds": 5,
                "max_notifications": 5,
                "auto_dismiss": True,
                "sound_enabled": True
            }
        }
    
    def load_config(self, config_type: str = "both") -> Dict[str, Any]:
        """
        Ładuje konfigurację z plików
        
        Args:
            config_type: Typ konfiguracji ("app", "ui", "both")
            
        Returns:
            Słownik z konfiguracją
        """
        logger.info(f"Loading configuration: {config_type}")
        try:
            if config_type in ["app", "both"]:
                logger.info(f"Loading app config from {self.app_config_path}")
                self._app_config = self._load_json_file(
                    self.app_config_path, 
                    self._default_app_config
                )
            
            if config_type in ["ui", "both"]:
                logger.info(f"Loading UI config from {self.ui_config_path}")
                self._ui_config = self._load_json_file(
                    self.ui_config_path, 
                    self._default_ui_config
                )
            
            logger.info(f"Configuration {config_type} loaded successfully")
            if config_type == "app":
                return self._app_config
            elif config_type == "ui":
                return self._ui_config
            else:
                return {
                    "app": self._app_config,
                    "ui": self._ui_config
                }
                
        except Exception as e:
            logger.error(f"Error loading configuration {config_type}: {e}")
            raise ConfigValidationError(
                f"Error loading configuration: {str(e)}",
                config_type
            )
    
    def _load_json_file(self, file_path: Path, default_config: Dict) -> Dict[str, Any]:
        """
        Ładuje plik JSON z konfiguracją
        
        Args:
            file_path: Ścieżka do pliku
            default_config: Domyślna konfiguracja
            
        Returns:
            Słownik z konfiguracją
        """
        if not file_path.exists():
            # Utwórz plik z domyślną konfiguracją
            self._save_json_file(file_path, default_config)
            return copy.deepcopy(default_config)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Połącz z domyślną konfiguracją (dodaj brakujące klucze)
            merged_config = self._merge_configs(default_config, config)
            
            # Zapisz zaktualizowaną konfigurację
            if merged_config != config:
                self._save_json_file(file_path, merged_config)
            
            return merged_config
            
        except json.JSONDecodeError as e:
            raise ConfigValidationError(
                f"Invalid JSON in config file: {str(e)}",
                str(file_path)
            )
        except Exception as e:
            raise ConfigValidationError(
                f"Error reading config file: {str(e)}",
                str(file_path)
            )
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """
        Łączy konfigurację użytkownika z domyślną
        
        Args:
            default: Domyślna konfiguracja
            user: Konfiguracja użytkownika
            
        Returns:
            Połączona konfiguracja
        """
        merged = copy.deepcopy(default)
        
        for key, value in user.items():
            if key in merged:
                if isinstance(value, dict) and isinstance(merged[key], dict):
                    merged[key] = self._merge_configs(merged[key], value)
                else:
                    merged[key] = value
            else:
                merged[key] = value
        
        return merged
    
    def _save_json_file(self, file_path: Path, config: Dict):
        """
        Zapisuje konfigurację do pliku JSON
        
        Args:
            file_path: Ścieżka do pliku
            config: Konfiguracja do zapisania
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigValidationError(
                f"Error saving config file: {str(e)}",
                str(file_path)
            )
    
    def save_config(self, config_type: str, config: Dict[str, Any]):
        """
        Zapisuje konfigurację do pliku
        
        Args:
            config_type: Typ konfiguracji ("app" lub "ui")
            config: Konfiguracja do zapisania
        """
        logger.info(f"Saving configuration: {config_type}")
        try:
            old_config = None
            if config_type == "app":
                logger.info(f"Validating and saving app config to {self.app_config_path}")
                old_config = self._app_config.copy() if self._app_config else None
                self._validate_app_config(config)
                self._save_json_file(self.app_config_path, config)
                self._app_config = config
            elif config_type == "ui":
                logger.info(f"Validating and saving UI config to {self.ui_config_path}")
                old_config = self._ui_config.copy() if self._ui_config else None
                self._validate_ui_config(config)
                self._save_json_file(self.ui_config_path, config)
                self._ui_config = config
            else:
                logger.error(f"Invalid config type: {config_type}")
                raise ConfigValidationError(
                    f"Invalid config type: {config_type}",
                    config_type
                )
            
            timestamp = self._get_timestamp()
            logger.info(f"Configuration {config_type} saved successfully")
            # Powiadom o zmianie konfiguracji
            logger.info(f"TRACE: config.updated - type={config_type}, timestamp={timestamp}")
            self.event_bus.publish(
                EventTypes.CONFIG_UPDATED,
                {
                    'config_type': config_type,
                    'old_config': old_config,
                    'new_config': copy.deepcopy(config),
                    'timestamp': timestamp
                }
            )
            
        except Exception as e:
            logger.error(f"Error saving configuration {config_type}: {e}")
            if not isinstance(e, ConfigValidationError):
                raise ConfigValidationError(
                    f"Error saving configuration: {str(e)}",
                    config_type
                )
            raise
    
    def get_app_config(self) -> Dict[str, Any]:
        """
        Pobiera konfigurację aplikacji
        
        Returns:
            Słownik z konfiguracją aplikacji
        """
        if self._app_config is None:
            self.load_config("app")
        return copy.deepcopy(self._app_config)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """
        Pobiera konfigurację UI
        
        Returns:
            Słownik z konfiguracją UI
        """
        if self._ui_config is None:
            self.load_config("ui")
        return copy.deepcopy(self._ui_config)
    
    def get_config(self) -> Dict[str, Any]:
        """
        Pobiera całą konfigurację (app + ui)
        
        Returns:
            Słownik z całą konfiguracją
        """
        app_config = self.get_app_config()
        ui_config = self.get_ui_config()
        
        # Połącz konfiguracje
        combined_config = copy.deepcopy(app_config)
        combined_config['ui'] = ui_config
        
        return combined_config
    
    def get_setting(self, config_type: str, path: str, default: Any = None) -> Any:
        """
        Pobiera konkretne ustawienie z konfiguracji
        
        Args:
            config_type: Typ konfiguracji ("app" lub "ui")
            path: Ścieżka do ustawienia (np. "database.path")
            default: Wartość domyślna
            
        Returns:
            Wartość ustawienia
        """
        try:
            if config_type == "app":
                config = self.get_app_config()
                keys = self._split_path(path)
                if keys and keys[0] == "app":
                    keys = keys[1:]
            elif config_type == "ui":
                config = self.get_ui_config()
                keys = self._split_path(path)
            else:
                # Traktuj config_type jako sekcję w konfiguracji aplikacji
                config = self.get_app_config()
                section_path = f"{config_type}.{path}" if path else config_type
                keys = self._split_path(section_path)

            return self._resolve_path(config, keys, default)

        except Exception:
            return default

    def set_setting(self, config_type: str, path: str, value: Any, meta: Optional[Dict[str, Any]] = None):
        """
        Ustawia konkretne ustawienie w konfiguracji
        
        Args:
            config_type: Typ konfiguracji ("app" lub "ui")
            path: Ścieżka do ustawienia (np. "database.path")
            value: Nowa wartość
        """
        try:
            target_type = config_type if config_type in ("app", "ui") else "app"
            config = self.get_app_config() if target_type == "app" else self.get_ui_config()

            if config_type == "app":
                keys = self._split_path(path)
                if keys and keys[0] == "app":
                    keys = keys[1:]
            elif config_type == "ui":
                keys = self._split_path(path)
            else:
                section_path = f"{config_type}.{path}" if path else config_type
                keys = self._split_path(section_path)

            if not keys:
                raise ConfigValidationError(
                    "Invalid configuration path provided",
                    config_type,
                    path
                )

            old_value = self.get_setting(config_type, path, None)

            current = config
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]

            current[keys[-1]] = value

            # Zapisz konfigurację (to wywoła EventBus notification)
            self.save_config(target_type, config)

            event_path = '.'.join(keys)
            namespace = self._infer_namespace(target_type, event_path)
            meta_payload = dict(meta or {})
            meta_payload.setdefault('by', 'ui')
            meta_payload.setdefault('ts', datetime.now(timezone.utc).isoformat())

            logger.info(
                "TRACE: config.%s.updated - path=%s old=%s new=%s",
                namespace,
                event_path,
                old_value,
                value
            )

            payload = {
                'config_type': target_type,
                'path': event_path,
                'value': value,
                'old_value': old_value,
                'meta': meta_payload,
                'namespace': namespace
            }

            self._notify_listeners(namespace, event_path, value, meta_payload)

            event_name = {
                'risk': EventTypes.CONFIG_RISK_UPDATED,
                'ui': EventTypes.CONFIG_UI_UPDATED
            }.get(namespace, EventTypes.CONFIG_APP_UPDATED)

            self.event_bus.publish(event_name, payload)

        except Exception as e:
            if not isinstance(e, ConfigValidationError):
                raise ConfigValidationError(
                    f"Error setting configuration value: {str(e)}",
                    config_type,
                    path
                )
            raise
    
    def _validate_app_config(self, config: Dict[str, Any]):
        """
        Waliduje konfigurację aplikacji
        
        Args:
            config: Konfiguracja do walidacji
        """
        required_sections = ["app", "database", "logging", "security"]
        
        for section in required_sections:
            if section not in config:
                raise ConfigValidationError(
                    f"Missing required section: {section}",
                    "app_config",
                    section
                )
        
        # Walidacja konkretnych wartości
        if "exchanges" in config:
            if "default" in config["exchanges"]:
                default_exchange = config["exchanges"]["default"]
                available = config["exchanges"].get("available", [])
                if default_exchange not in available:
                    raise ConfigValidationError(
                        f"Default exchange '{default_exchange}' not in available exchanges",
                        "app_config",
                        "exchanges.default"
                    )
        
        # Walidacja limitów
        if "trading" in config:
            trading = config["trading"]
            if "min_order_amount" in trading and "max_order_amount" in trading:
                if trading["min_order_amount"] >= trading["max_order_amount"]:
                    raise ConfigValidationError(
                        "min_order_amount must be less than max_order_amount",
                        "app_config",
                        "trading"
                    )
    
    def _validate_ui_config(self, config: Dict[str, Any]):
        """
        Waliduje konfigurację UI
        
        Args:
            config: Konfiguracja do walidacji
        """
        # Walidacja motywu
        if "theme" in config:
            theme = config["theme"]
            if "current" in theme and "available" in theme:
                if theme["current"] not in theme["available"]:
                    raise ConfigValidationError(
                        f"Current theme '{theme['current']}' not in available themes",
                        "ui_config",
                        "theme.current"
                    )
        
        # Walidacja okna
        if "window" in config:
            window = config["window"]
            if "min_width" in window and "default_width" in window:
                if window["default_width"] < window["min_width"]:
                    raise ConfigValidationError(
                        "default_width must be >= min_width",
                        "ui_config",
                        "window"
                    )
            if "min_height" in window and "default_height" in window:
                if window["default_height"] < window["min_height"]:
                    raise ConfigValidationError(
                        "default_height must be >= min_height",
                        "ui_config",
                        "window"
                    )
    
    def reset_to_defaults(self, config_type: str = "both"):
        """
        Resetuje konfigurację do wartości domyślnych
        
        Args:
            config_type: Typ konfiguracji do zresetowania
        """
        try:
            if config_type in ["app", "both"]:
                self.save_config("app", self._default_app_config)
            
            if config_type in ["ui", "both"]:
                self.save_config("ui", self._default_ui_config)
                
        except Exception as e:
            raise ConfigValidationError(
                f"Error resetting configuration: {str(e)}",
                config_type
            )
    
    def backup_config(self, backup_dir: str = "data/backup/config"):
        """
        Tworzy kopię zapasową konfiguracji
        
        Args:
            backup_dir: Katalog kopii zapasowych
        """
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Kopia konfiguracji aplikacji
            if self.app_config_path.exists():
                backup_app_path = backup_path / f"app_config_{timestamp}.json"
                import shutil
                shutil.copy2(self.app_config_path, backup_app_path)
            
            # Kopia konfiguracji UI
            if self.ui_config_path.exists():
                backup_ui_path = backup_path / f"ui_config_{timestamp}.json"
                shutil.copy2(self.ui_config_path, backup_ui_path)
            
            return True
            
        except Exception as e:
            raise ConfigValidationError(
                f"Error creating config backup: {str(e)}",
                "backup"
            )
    
    def restore_config(self, backup_file: str, config_type: str):
        """
        Przywraca konfigurację z kopii zapasowej
        
        Args:
            backup_file: Ścieżka do pliku kopii zapasowej
            config_type: Typ konfiguracji ("app" lub "ui")
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                raise ConfigValidationError(
                    f"Backup file not found: {backup_file}",
                    config_type
                )
            
            # Wczytaj konfigurację z kopii zapasowej
            with open(backup_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Waliduj i zapisz
            if config_type == "app":
                self._validate_app_config(config)
                target_path = self.app_config_path
            elif config_type == "ui":
                self._validate_ui_config(config)
                target_path = self.ui_config_path
            else:
                raise ConfigValidationError(
                    f"Invalid config type: {config_type}",
                    config_type
                )
            
            # Utwórz kopię zapasową obecnej konfiguracji
            if target_path.exists():
                self.backup_config()
            
            # Przywróć konfigurację
            self._save_json_file(target_path, config)
            
            # Przeładuj konfigurację
            self.load_config(config_type)
            
            return True
            
        except Exception as e:
            if not isinstance(e, ConfigValidationError):
                raise ConfigValidationError(
                    f"Error restoring configuration: {str(e)}",
                    config_type
                )
            raise
    
    def get_available_languages(self) -> list:
        """Zwraca listę dostępnych języków"""
        ui_config = self.get_ui_config()
        return ui_config.get("language", {}).get("available", ["en", "pl"])
    
    def get_available_themes(self) -> list:
        """Zwraca listę dostępnych motywów"""
        ui_config = self.get_ui_config()
        return ui_config.get("theme", {}).get("available", ["light", "dark"])
    
    def get_available_exchanges(self) -> list:
        """Zwraca listę dostępnych giełd"""
        app_config = self.get_app_config()
        return app_config.get("exchanges", {}).get("available", [])

    def get_supported_trading_pairs(self) -> List[str]:
        """Zwraca listę wspieranych par handlowych dla kreatora botów."""

        app_config = self.get_app_config()
        trading_cfg = app_config.get("trading", {}) if isinstance(app_config, dict) else {}
        raw_pairs = trading_cfg.get("supported_pairs")

        if not raw_pairs:
            default_quote = trading_cfg.get("default_quote_currency", "USDT")
            return [f"BTC/{default_quote}", f"ETH/{default_quote}"]

        normalised: List[str] = []
        seen = set()
        for entry in raw_pairs:
            if not entry:
                continue
            candidate = str(entry).strip().upper()
            if not candidate:
                continue
            candidate = candidate.replace("-", "/").replace(" ", "")
            if candidate not in seen:
                normalised.append(candidate)
                seen.add(candidate)

        if not normalised:
            default_quote = trading_cfg.get("default_quote_currency", "USDT")
            return [f"BTC/{default_quote}", f"ETH/{default_quote}"]

        return normalised

    def _get_timestamp(self) -> str:
        """Zwraca aktualny timestamp"""
        return datetime.now(timezone.utc).isoformat()

    def _split_path(self, path: str) -> List[str]:
        return [segment for segment in path.split('.') if segment]

    def _resolve_path(self, config: Dict[str, Any], keys: List[str], default: Any) -> Any:
        value: Any = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def _infer_namespace(self, config_type: str, path: str) -> str:
        lowered = path.lower()
        if "risk" in lowered:
            return "risk"
        if config_type == "ui":
            return "ui"
        return "app"

    def register_listener(self, namespace: str, callback: Callable[[str, Any, Dict[str, Any]], None]) -> None:
        """Rejestruje lokalnego listenera zmian konfiguracji"""
        with self._listener_lock:
            callbacks = self._listeners[namespace]
            if callback not in callbacks:
                callbacks.append(callback)

    def unregister_listener(self, namespace: str, callback: Callable[[str, Any, Dict[str, Any]], None]) -> None:
        """Usuwa listenera ze wskazanego namespace"""
        with self._listener_lock:
            callbacks = self._listeners.get(namespace, [])
            if callback in callbacks:
                callbacks.remove(callback)

    def _notify_listeners(self, namespace: str, path: str, value: Any, meta: Dict[str, Any]) -> None:
        listeners: List[Callable[[str, Any, Dict[str, Any]], None]]
        with self._listener_lock:
            listeners = list(self._listeners.get(namespace, []))

        for callback in listeners:
            try:
                callback(path, value, meta)
            except Exception:
                logger.exception("Notify listener error for %s", namespace)
    
    def subscribe_to_config_changes(self, callback):
        """
        Subskrybuje powiadomienia o zmianach konfiguracji
        
        Args:
            callback: Funkcja callback do wywołania przy zmianie konfiguracji
        """
        self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, callback)
        logger.debug("Dodano listener dla zmian konfiguracji")
    
    def unsubscribe_from_config_changes(self, callback):
        """
        Usuwa subskrypcję powiadomień o zmianach konfiguracji
        
        Args:
            callback: Funkcja callback do usunięcia
        """
        self.event_bus.unsubscribe(EventTypes.CONFIG_UPDATED, callback)
        logger.debug("Usunięto listener dla zmian konfiguracji")

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Zwraca podsumowanie portfela z konfiguracji
        
        Returns:
            Słownik z podsumowaniem portfela
        """
        try:
            # Pobierz konfigurację aplikacji
            app_config = self.get_app_config()
            
            # Zwróć podstawowe informacje o portfelu z konfiguracji
            return {
                "default_quote_currency": app_config.get("trading", {}).get("default_quote_currency", "USDT"),
                "max_open_positions": app_config.get("trading", {}).get("max_open_positions", 10),
                "paper_trading": app_config.get("trading", {}).get("paper_trading", False),
                "min_order_amount": app_config.get("trading", {}).get("min_order_amount", 10.0),
                "max_order_amount": app_config.get("trading", {}).get("max_order_amount", 10000.0),
                "default_stop_loss_percent": app_config.get("trading", {}).get("default_stop_loss_percent", 5.0),
                "default_take_profit_percent": app_config.get("trading", {}).get("default_take_profit_percent", 10.0),
                "slippage_tolerance_percent": app_config.get("trading", {}).get("slippage_tolerance_percent", 0.5)
            }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania podsumowania portfela: {e}")
            return {
                "default_quote_currency": "USDT",
                "max_open_positions": 10,
                "paper_trading": False,
                "min_order_amount": 10.0,
                "max_order_amount": 10000.0,
                "default_stop_loss_percent": 5.0,
                "default_take_profit_percent": 10.0,
                "slippage_tolerance_percent": 0.5
            }

    # -- High level settings helpers -------------------------------------------------

    def get_risk_settings(self) -> Dict[str, Any]:
        """Zwraca aktualne ustawienia zarządzania ryzykiem z konfiguracji."""
        app_config = self.get_app_config()
        defaults = {
            "max_position_size": 10.0,
            "max_daily_trades": 50,
            "max_open_positions": 10,
            "default_stop_loss": 2.0,
            "default_take_profit": 5.0,
            "trailing_stop_enabled": False,
            "max_daily_loss": 5.0,
            "max_drawdown": 10.0,
            "emergency_stop_enabled": True,
            "risk_per_trade": 1.0,
            "kelly_criterion_enabled": False,
            "compound_profits": True,
        }
        stored = app_config.get("risk_management", {}) if isinstance(app_config, dict) else {}
        combined = {**defaults, **stored}
        combined.setdefault("updated_at", self._get_timestamp())
        return combined

    def update_risk_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuje ustawienia zarządzania ryzykiem i emituje zdarzenie."""
        if not isinstance(updates, dict):
            raise ConfigValidationError("Risk settings update must be a dictionary", "app", "risk_management")

        app_config = self.get_app_config()
        risk_section = dict(app_config.get("risk_management", {}))
        risk_section.update(updates)
        risk_section["updated_at"] = self._get_timestamp()
        app_config["risk_management"] = risk_section
        self.save_config("app", app_config)

        meta = {"by": "ui", "ts": risk_section["updated_at"]}
        self._notify_listeners("risk", "risk_management", risk_section, meta)
        self.event_bus.publish(
            EventTypes.CONFIG_RISK_UPDATED,
            {
                "config_type": "app",
                "path": "risk_management",
                "value": copy.deepcopy(risk_section),
                "meta": meta,
            },
        )
        return risk_section

    def get_notification_settings(self) -> Dict[str, Any]:
        """Pobiera ustawienia powiadomień z konfiguracji."""
        app_config = self.get_app_config()
        defaults = self._get_default_app_config().get("notifications", {})
        stored = app_config.get("notifications", {}) if isinstance(app_config, dict) else {}

        merged = copy.deepcopy(defaults)

        for key, value in stored.items():
            if key in {"types", "channels"} and isinstance(value, dict):
                merged.setdefault(key, {})
                merged[key].update(value)
            else:
                merged[key] = value
        return merged

    def update_notification_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuje ustawienia powiadomień i zapisuje je do pliku."""
        if not isinstance(updates, dict):
            raise ConfigValidationError("Notification settings update must be a dictionary", "app", "notifications")

        app_config = self.get_app_config()
        existing = self.get_notification_settings()
        merged = copy.deepcopy(existing)

        for key, value in updates.items():
            if key in {"types", "channels"} and isinstance(value, dict):
                merged.setdefault(key, {})
                merged[key].update(value)
            else:
                merged[key] = value

        merged["updated_at"] = self._get_timestamp()
        app_config["notifications"] = merged
        self.save_config("app", app_config)

        meta = {"by": "ui", "ts": merged["updated_at"]}
        self._notify_listeners("app", "notifications", merged, meta)
        self.event_bus.publish(
            EventTypes.CONFIG_APP_UPDATED,
            {
                "config_type": "app",
                "path": "notifications",
                "value": copy.deepcopy(merged),
                "meta": meta,
            },
        )
        return merged

    def get_general_settings(self) -> Dict[str, Dict[str, Any]]:
        """Zwraca agregat ustawień ogólnych wykorzystywany w UI ustawień."""
        app_config = self.get_app_config()
        ui_config = self.get_ui_config()

        return {
            "ui": {
                "theme": ui_config.get("theme", {}).get("current", "dark"),
                "language": app_config.get("app", {}).get("language", "pl"),
                "minimize_to_tray": ui_config.get("window", {}).get("minimize_to_tray", True),
                "start_minimized": ui_config.get("window", {}).get("start_maximized", False),
            },
            "startup": {
                "start_with_system": app_config.get("app", {}).get("start_with_system", False),
                "auto_start_bots": app_config.get("app", {}).get("auto_start_bots", False),
                "auto_connect_exchanges": app_config.get("trading", {}).get("auto_connect_exchanges", True),
            },
            "security": {
                "encrypt_config": app_config.get("security", {}).get("encryption_algorithm", "AES-256") != "none",
                "require_password": app_config.get("security", {}).get("require_password_change_days", 90) > 0,
                "auto_logout": app_config.get("security", {}).get("auto_lock_minutes", 30) > 0,
                "logout_timeout": app_config.get("security", {}).get("auto_lock_minutes", 30),
            },
            "updates": {
                "auto_check": app_config.get("app", {}).get("auto_check_updates", True),
                "beta_updates": app_config.get("app", {}).get("allow_beta_updates", False),
            },
        }

    def update_general_settings(self, payload: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aktualizuje sekcję ogólną (UI, start, bezpieczeństwo, aktualizacje)."""
        if not isinstance(payload, dict):
            raise ConfigValidationError("General settings payload must be a dictionary", "app", "general")

        app_config = self.get_app_config()
        ui_config = self.get_ui_config()

        ui_section = payload.get("ui", {})
        startup_section = payload.get("startup", {})
        security_section = payload.get("security", {})
        updates_section = payload.get("updates", {})

        if ui_section:
            ui_config.setdefault("theme", {})["current"] = ui_section.get("theme", ui_config.get("theme", {}).get("current", "dark"))
            ui_config.setdefault("window", {})["minimize_to_tray"] = bool(ui_section.get("minimize_to_tray", True))
            ui_config.setdefault("window", {})["start_maximized"] = bool(ui_section.get("start_minimized", False))
            app_config.setdefault("app", {})["language"] = ui_section.get("language", app_config.get("app", {}).get("language", "pl"))

        if startup_section:
            app_config.setdefault("app", {})["start_with_system"] = bool(startup_section.get("start_with_system", False))
            app_config.setdefault("app", {})["auto_start_bots"] = bool(startup_section.get("auto_start_bots", False))
            app_config.setdefault("trading", {})["auto_connect_exchanges"] = bool(startup_section.get("auto_connect_exchanges", True))

        if security_section:
            app_config.setdefault("security", {})["require_password_change_days"] = 90 if security_section.get("require_password", True) else 0
            auto_logout = bool(security_section.get("auto_logout", True))
            timeout_minutes = int(security_section.get("logout_timeout", 30)) if auto_logout else 0
            app_config.setdefault("security", {})["auto_lock_minutes"] = max(0, timeout_minutes)
            if security_section.get("encrypt_config", True):
                app_config.setdefault("security", {})["encryption_algorithm"] = "AES-256"
            else:
                app_config.setdefault("security", {})["encryption_algorithm"] = "none"

        if updates_section:
            app_config.setdefault("app", {})["auto_check_updates"] = bool(updates_section.get("auto_check", True))
            app_config.setdefault("app", {})["allow_beta_updates"] = bool(updates_section.get("beta_updates", False))

        timestamp = self._get_timestamp()
        app_config.setdefault("app", {})["general_updated_at"] = timestamp

        self.save_config("ui", ui_config)
        self.save_config("app", app_config)

        meta = {"by": "ui", "ts": timestamp}
        self._notify_listeners("app", "general", payload, meta)
        self.event_bus.publish(
            EventTypes.CONFIG_APP_UPDATED,
            {
                "config_type": "app",
                "path": "general",
                "value": copy.deepcopy(payload),
                "meta": meta,
            },
        )
        return payload

# Globalna instancja menedżera konfiguracji
_config_manager = None

def get_config_manager() -> ConfigManager:
    """
    Pobiera globalną instancję menedżera konfiguracji
    
    Returns:
        Instancja ConfigManager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_app_setting(path: str, default: Any = None) -> Any:
    """
    Skrót do pobierania ustawień aplikacji
    
    Args:
        path: Ścieżka do ustawienia
        default: Wartość domyślna
        
    Returns:
        Wartość ustawienia
    """
    return get_config_manager().get_setting("app", path, default)

def get_ui_setting(path: str, default: Any = None) -> Any:
    """
    Skrót do pobierania ustawień UI
    
    Args:
        path: Ścieżka do ustawienia
        default: Wartość domyślna
        
    Returns:
        Wartość ustawienia
    """
    return get_config_manager().get_setting("ui", path, default)

def set_app_setting(path: str, value: Any):
    """
    Skrót do ustawiania ustawień aplikacji
    
    Args:
        path: Ścieżka do ustawienia
        value: Nowa wartość
    """
    get_config_manager().set_setting("app", path, value)

def set_ui_setting(path: str, value: Any):
    """
    Skrót do ustawiania ustawień UI
    
    Args:
        path: Ścieżka do ustawienia
        value: Nowa wartość
    """
    get_config_manager().set_setting("ui", path, value)
