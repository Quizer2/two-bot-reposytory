"""
DataManager - Centralny system zarządzania danymi dla CryptoBotDesktop
Obsługuje pobieranie danych, cache, obsługę błędów i integrację z bazą danych i API
"""

import sqlite3
import logging
import asyncio
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import ast

from core.database_manager import DatabaseManager as AppDatabaseManager

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationHelper:
    """Helper do walidacji danych wejściowych"""
    
    @staticmethod
    def validate_limit(limit: Any) -> int:
        """Waliduje i konwertuje limit na int"""
        try:
            limit_int = int(limit)
            return max(1, min(limit_int, 1000))  # Ograniczenie 1-1000
        except (ValueError, TypeError):
            return 100  # Domyślna wartość

    @staticmethod
    def validate_bot_id(bot_id: Any) -> Optional[str]:
        """Waliduje bot_id"""
        if not bot_id:
            return None
        bot_id_str = str(bot_id).strip()
        return bot_id_str if len(bot_id_str) > 0 else None

    @staticmethod
    def validate_log_level(level: Any) -> str:
        """Waliduje poziom logowania"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        level_str = str(level).upper()
        return level_str if level_str in valid_levels else 'INFO'

    @staticmethod
    def validate_date(date_str: Any) -> Optional[datetime]:
        """Waliduje i konwertuje string na datetime"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, datetime):
                return date_str
            return datetime.fromisoformat(str(date_str))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_severity(severity: Any) -> str:
        """Waliduje poziom ważności alertu"""
        valid_severities = ['low', 'medium', 'high', 'critical']
        severity_str = str(severity).lower()
        return severity_str if severity_str in valid_severities else 'medium'

    @staticmethod
    def validate_alert_type(alert_type: Any) -> str:
        """Waliduje typ alertu"""
        valid_types = ['info', 'warning', 'error', 'success']
        type_str = str(alert_type).lower()
        return type_str if type_str in valid_types else 'info'

class DatabaseTransactionHelper:
    """Helper do wykonywania transakcji bazodanowych z retry i rollback"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        
    def execute_with_retry(self, operation_func, max_retries: int = 3) -> bool:
        """Wykonuje operację z retry i obsługą błędów"""
        with self.lock:
            for attempt in range(max_retries):
                try:
                    with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                        conn.execute("PRAGMA foreign_keys = ON")
                        cursor = conn.cursor()
                        
                        # Wykonaj operację
                        operation_func(cursor, conn)
                        conn.commit()
                        return True
                        
                except sqlite3.Error as e:
                    logger.error(f"Database error (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        time.sleep(2 ** attempt)
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts")
                        return False
                except Exception as e:
                    logger.error(f"Unexpected error in database operation: {e}")
                    return False
            
            return False

@dataclass
class PortfolioData:
    """Struktura danych portfolio"""
    total_value: float
    available_balance: float
    invested_amount: float
    profit_loss: float
    profit_loss_percent: float
    assets: List[Dict[str, Any]]
    last_updated: datetime

@dataclass
class BotData:
    """Struktura danych bota"""
    id: str
    name: str
    status: str
    active: bool
    profit: float
    profit_percent: float
    trades_count: int
    last_trade: Optional[datetime]
    risk_level: str
    created_at: datetime

@dataclass
class RiskMetrics:
    """Struktura metryk ryzyka"""
    var_1d: float
    var_7d: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    beta: float
    last_calculated: datetime

@dataclass
class LogEntry:
    """Struktura wpisu loga"""
    id: int
    timestamp: datetime
    level: str
    message: str
    source: str
    bot_id: Optional[str] = None

@dataclass
class AlertEntry:
    """Struktura alertu"""
    id: int
    timestamp: datetime
    type: str
    severity: str
    title: str
    message: str
    read: bool
    bot_id: Optional[str] = None

class DataManager:
    """Główny manager danych aplikacji"""
    
    def __init__(self, db_path: str = "crypto_bot.db"):
        self.db_path = db_path
        self.cache: Dict[str, Any] = {}
        self.last_cache_update: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=5)
        self.db_helper = DatabaseTransactionHelper(db_path)
        self._initialized = False
        self._init_lock = threading.Lock()

        # Konfiguracja z zmiennych środowiskowych
        self.use_real_data = os.getenv('USE_REAL_DATA', 'false').lower() == 'true'
        self.cache_enabled = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'

        # Mostek do asynchronicznego DatabaseManagera (app.database)
        self._app_db_manager: Optional[AppDatabaseManager] = None
        self._app_db_lock = asyncio.Lock()
        
    async def ensure_initialized(self):
        """Zapewnia, że DataManager jest zainicjalizowany"""
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:
                    await self.init_database()
                    self._initialized = True

    async def init_database(self):
        """Inicjalizuje bazę danych z tabelami"""
        def create_tables_operation(cursor, conn):
            # Tabela portfolio
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_value REAL NOT NULL,
                    available_balance REAL NOT NULL,
                    invested_amount REAL NOT NULL,
                    profit_loss REAL NOT NULL,
                    profit_loss_percent REAL NOT NULL,
                    assets TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela botów
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT 0,
                    profit REAL NOT NULL DEFAULT 0,
                    profit_percent REAL NOT NULL DEFAULT 0,
                    trades_count INTEGER NOT NULL DEFAULT 0,
                    last_trade TIMESTAMP,
                    risk_level TEXT NOT NULL DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela metryk ryzyka
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    var_1d REAL NOT NULL,
                    var_7d REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    volatility REAL NOT NULL,
                    beta REAL NOT NULL,
                    last_calculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela logów
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    source TEXT NOT NULL,
                    bot_id TEXT,
                    FOREIGN KEY (bot_id) REFERENCES bots (id)
                )
            ''')
            
            # Tabela alertów
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    read BOOLEAN NOT NULL DEFAULT 0,
                    bot_id TEXT,
                    FOREIGN KEY (bot_id) REFERENCES bots (id)
                )
            ''')
            
            # Indeksy dla lepszej wydajności
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_read ON alerts(read)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bots_active ON bots(active)')
            
        success = self.db_helper.execute_with_retry(create_tables_operation)
        if success:
            logger.info("Database initialized successfully")
        else:
            logger.error("Failed to initialize database")

    def _get_config_setting(self, key: str, default: Any = None) -> Any:
        """Pobiera ustawienie konfiguracyjne"""
        return os.getenv(key, default)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Sprawdza czy cache jest aktualny"""
        if not self.cache_enabled:
            return False
        if cache_key not in self.last_cache_update:
            return False
        return datetime.now() - self.last_cache_update[cache_key] < self.cache_duration

    def _update_cache(self, cache_key: str, data: Any):
        """Aktualizuje cache"""
        if self.cache_enabled:
            self.cache[cache_key] = data
            self.last_cache_update[cache_key] = datetime.now()

    async def _get_app_database(self) -> Optional[AppDatabaseManager]:
        """Lazy inicjalizacja DatabaseManagera z warstwy aplikacyjnej."""
        if self._app_db_manager is not None:
            return self._app_db_manager
        async with self._app_db_lock:
            if self._app_db_manager is None:
                try:
                    manager = AppDatabaseManager()
                    await manager.initialize()
                    self._app_db_manager = manager
                except Exception as exc:
                    logger.error(f"Nie można zainicjalizować DatabaseManager: {exc}")
                    return None
        return self._app_db_manager

    async def _resolve_default_user_id(self) -> Optional[int]:
        """Próbuje ustalić identyfikator użytkownika dla ustawień globalnych."""
        app_db = await self._get_app_database()
        if app_db is None:
            return None
        try:
            user = await app_db.get_first_user()
            if user and user.get('id') is not None:
                return int(user['id'])
        except Exception as exc:
            logger.debug(f"Nie udało się ustalić domyślnego użytkownika: {exc}")
        return None

    async def get_portfolio_data(self) -> PortfolioData:
        """Pobiera dane portfolio"""
        try:
            await self.ensure_initialized()
            
            cache_key = "portfolio_data"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            if self.use_real_data:
                data = await self._get_real_portfolio_data()
            else:
                data = await self._get_sample_portfolio_data()
            
            self._update_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Error getting portfolio data: {e}")
            return await self._get_sample_portfolio_data()

    async def _get_real_portfolio_data(self) -> PortfolioData:
        """Pobiera rzeczywiste dane portfolio z bazy"""
        def get_portfolio_operation(cursor, conn):
            cursor.execute('''
                SELECT total_value, available_balance, invested_amount, 
                       profit_loss, profit_loss_percent, assets, last_updated
                FROM portfolio 
                ORDER BY last_updated DESC 
                LIMIT 1
            ''')
            return cursor.fetchone()
        
        try:
            result = None
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                result = get_portfolio_operation(cursor, conn)
            
            if result:
                return PortfolioData(
                    total_value=result[0],
                    available_balance=result[1],
                    invested_amount=result[2],
                    profit_loss=result[3],
                    profit_loss_percent=result[4],
                    assets=ast.literal_eval(result[5]) if result[5] else [],
                    last_updated=datetime.fromisoformat(result[6])
                )
            else:
                # Brak danych - wstaw przykładowe
                sample_data = await self._get_sample_portfolio_data()
                await self._insert_sample_portfolio_data(sample_data)
                return sample_data
                
        except Exception as e:
            logger.error(f"Error getting real portfolio data: {e}")
            return await self._get_sample_portfolio_data()

    async def _get_sample_portfolio_data(self) -> PortfolioData:
        """Zwraca przykładowe dane portfolio"""
        return PortfolioData(
            total_value=15750.50,
            available_balance=2500.00,
            invested_amount=13250.50,
            profit_loss=1250.50,
            profit_loss_percent=8.6,
            assets=[
                {"symbol": "BTC", "amount": 0.5, "value": 8500.00, "change_24h": 2.5},
                {"symbol": "ETH", "amount": 3.2, "value": 4200.00, "change_24h": -1.2},
                {"symbol": "ADA", "amount": 1500, "value": 750.00, "change_24h": 5.8},
                {"symbol": "DOT", "amount": 200, "value": 1300.50, "change_24h": 3.1}
            ],
            last_updated=datetime.now()
        )

    async def _insert_sample_portfolio_data(self, data: PortfolioData):
        """Wstawia przykładowe dane portfolio do bazy"""
        def insert_operation(cursor, conn):
            cursor.execute('''
                INSERT INTO portfolio (total_value, available_balance, invested_amount,
                                     profit_loss, profit_loss_percent, assets, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.total_value, data.available_balance, data.invested_amount,
                data.profit_loss, data.profit_loss_percent, str(data.assets),
                data.last_updated.isoformat()
            ))
        
        self.db_helper.execute_with_retry(insert_operation)

    async def get_bots_data(self, limit: int = 100) -> List[BotData]:
        """Pobiera dane botów"""
        try:
            await self.ensure_initialized()
            limit = ValidationHelper.validate_limit(limit)
            
            cache_key = f"bots_data_{limit}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            if self.use_real_data:
                data = await self._get_real_bots_data(limit)
            else:
                # W środowisku aplikacji nie generujemy danych przykładowych
                data = []
            
            self._update_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Error getting bots data: {e}")
            # Nie generuj danych przykładowych – zwróć pustą listę
            return []

    async def _get_real_bots_data(self, limit: int) -> List[BotData]:
        """Pobiera rzeczywiste dane botów z bazy"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, status, active, profit, profit_percent,
                           trades_count, last_trade, risk_level, created_at
                    FROM bots 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                
                if not results:
                    # Brak danych – zwróć pustą listę (nie wstawiaj przykładowych danych)
                    return []
                
                bots = []
                for row in results:
                    bots.append(BotData(
                        id=row[0],
                        name=row[1],
                        status=row[2],
                        active=bool(row[3]),
                        profit=row[4],
                        profit_percent=row[5],
                        trades_count=row[6],
                        last_trade=datetime.fromisoformat(row[7]) if row[7] else None,
                        risk_level=row[8],
                        created_at=datetime.fromisoformat(row[9])
                    ))
                
                return bots
                
        except Exception as e:
            logger.error(f"Error getting real bots data: {e}")
            # Nie zwracaj przykładowych danych – zwróć pustą listę
            return []

    async def _get_sample_bots_data(self, limit: int) -> List[BotData]:
        """Zwraca przykładowe dane botów"""
        sample_bots = [
            BotData(
                id="bot_001",
                name="Bitcoin Scalper",
                status="running",
                active=True,
                profit=450.75,
                profit_percent=12.5,
                trades_count=156,
                last_trade=datetime.now() - timedelta(minutes=15),
                risk_level="medium",
                created_at=datetime.now() - timedelta(days=30)
            ),
            BotData(
                id="bot_002", 
                name="ETH Grid Bot",
                status="paused",
                active=False,
                profit=-25.30,
                profit_percent=-1.8,
                trades_count=89,
                last_trade=datetime.now() - timedelta(hours=2),
                risk_level="low",
                created_at=datetime.now() - timedelta(days=15)
            ),
            BotData(
                id="bot_003",
                name="Altcoin Hunter",
                status="running",
                active=True,
                profit=825.60,
                profit_percent=28.9,
                trades_count=234,
                last_trade=datetime.now() - timedelta(minutes=5),
                risk_level="high",
                created_at=datetime.now() - timedelta(days=45)
            )
        ]
        
        return sample_bots[:limit]

    async def _insert_sample_bots_data(self, bots: List[BotData]):
        """Wstawia przykładowe dane botów do bazy"""
        def insert_operation(cursor, conn):
            for bot in bots:
                cursor.execute('''
                    INSERT OR REPLACE INTO bots 
                    (id, name, status, active, profit, profit_percent, trades_count,
                     last_trade, risk_level, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    bot.id, bot.name, bot.status, bot.active, bot.profit,
                    bot.profit_percent, bot.trades_count,
                    bot.last_trade.isoformat() if bot.last_trade else None,
                    bot.risk_level, bot.created_at.isoformat(), datetime.now().isoformat()
                ))
        
        self.db_helper.execute_with_retry(insert_operation)

    async def get_risk_metrics(self) -> RiskMetrics:
        """Pobiera metryki ryzyka bez używania przykładowych danych.
        Zwraca rzeczywiste metryki, a gdy ich brak lub wystąpi błąd – metryki zerowe.
        """
        try:
            await self.ensure_initialized()

            cache_key = "risk_metrics"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]

            # Zawsze próbuj pobrać rzeczywiste metryki; _get_real_risk_metrics zwraca zera gdy brak danych
            data = await self._get_real_risk_metrics()

            self._update_cache(cache_key, data)
            return data

        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            # Zwróć metryki zerowe zamiast przykładów
            return RiskMetrics(
                var_1d=0.0,
                var_7d=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                beta=0.0,
                last_calculated=datetime.now()
            )

    async def _get_real_risk_metrics(self) -> RiskMetrics:
        """Pobiera rzeczywiste metryki ryzyka z bazy; zwraca zera gdy brak danych"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT var_1d, var_7d, sharpe_ratio, max_drawdown,
                           volatility, beta, last_calculated
                    FROM risk_metrics 
                    ORDER BY last_calculated DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                if result:
                    return RiskMetrics(
                        var_1d=result[0] or 0.0,
                        var_7d=result[1] or 0.0,
                        sharpe_ratio=result[2] or 0.0,
                        max_drawdown=result[3] or 0.0,
                        volatility=result[4] or 0.0,
                        beta=result[5] or 0.0,
                        last_calculated=datetime.fromisoformat(result[6])
                    )
                else:
                    # Brak danych - zwróć metryki zerowe zamiast przykładowych
                    return RiskMetrics(
                        var_1d=0.0,
                        var_7d=0.0,
                        sharpe_ratio=0.0,
                        max_drawdown=0.0,
                        volatility=0.0,
                        beta=0.0,
                        last_calculated=datetime.now()
                    )
        except Exception as e:
            logger.error(f"Error getting real risk metrics: {e}")
            return RiskMetrics(
                var_1d=0.0,
                var_7d=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                beta=0.0,
                last_calculated=datetime.now()
            )


    async def get_logs(self, limit: int = 100, level: str = None) -> List[LogEntry]:
        """Pobiera logi"""
        try:
            await self.ensure_initialized()
            limit = ValidationHelper.validate_limit(limit)
            if level:
                level = ValidationHelper.validate_log_level(level)
            
            cache_key = f"logs_{limit}_{level or 'all'}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            if self.use_real_data:
                data = await self._get_real_logs(limit, level)
            else:
                data = await self._get_sample_logs(limit, level)
            
            self._update_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return await self._get_sample_logs(limit, level)

    async def _get_real_logs(self, limit: int, level: str = None) -> List[LogEntry]:
        """Pobiera rzeczywiste logi z bazy"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                if level:
                    cursor.execute('''
                        SELECT id, timestamp, level, message, source, bot_id
                        FROM logs 
                        WHERE level = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (level, limit))
                else:
                    cursor.execute('''
                        SELECT id, timestamp, level, message, source, bot_id
                        FROM logs 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                results = cursor.fetchall()
                
                if not results:
                    # Brak danych - wstaw przykładowe
                    sample_data = await self._get_sample_logs(limit, level)
                    await self._insert_sample_logs(sample_data)
                    return sample_data
                
                logs = []
                for row in results:
                    logs.append(LogEntry(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        level=row[2],
                        message=row[3],
                        source=row[4],
                        bot_id=row[5]
                    ))
                
                return logs
                
        except Exception as e:
            logger.error(f"Error getting real logs: {e}")
            return await self._get_sample_logs(limit, level)

    async def _get_sample_logs(self, limit: int, level: str = None) -> List[LogEntry]:
        """Zwraca przykładowe logi"""
        sample_logs = [
            LogEntry(
                id=1,
                timestamp=datetime.now() - timedelta(minutes=5),
                level="INFO",
                message="Bot started successfully",
                source="bot_manager",
                bot_id="bot_001"
            ),
            LogEntry(
                id=2,
                timestamp=datetime.now() - timedelta(minutes=10),
                level="WARNING",
                message="High volatility detected",
                source="risk_manager",
                bot_id=None
            ),
            LogEntry(
                id=3,
                timestamp=datetime.now() - timedelta(minutes=15),
                level="ERROR",
                message="Failed to connect to exchange API",
                source="exchange_connector",
                bot_id="bot_002"
            ),
            LogEntry(
                id=4,
                timestamp=datetime.now() - timedelta(minutes=20),
                level="INFO",
                message="Trade executed: BUY 0.1 BTC",
                source="trading_engine",
                bot_id="bot_001"
            )
        ]
        
        if level:
            sample_logs = [log for log in sample_logs if log.level == level]
        
        return sample_logs[:limit]

    async def _insert_sample_logs(self, logs: List[LogEntry]):
        """Wstawia przykładowe logi do bazy"""
        def insert_operation(cursor, conn):
            for log in logs:
                cursor.execute('''
                    INSERT INTO logs (timestamp, level, message, source, bot_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    log.timestamp.isoformat(), log.level, log.message,
                    log.source, log.bot_id
                ))
        
        self.db_helper.execute_with_retry(insert_operation)

    async def add_log(self, level: str, message: str, source: str, bot_id: str = None):
        """Dodaje nowy wpis do logów"""
        try:
            level = ValidationHelper.validate_log_level(level)
            bot_id = ValidationHelper.validate_bot_id(bot_id)
            
            def insert_operation(cursor, conn):
                cursor.execute('''
                    INSERT INTO logs (level, message, source, bot_id)
                    VALUES (?, ?, ?, ?)
                ''', (level, message, source, bot_id))
            
            success = self.db_helper.execute_with_retry(insert_operation)
            
            if success:
                # Wyczyść cache logów
                keys_to_remove = [k for k in self.cache.keys() if k.startswith('logs_')]
                for key in keys_to_remove:
                    del self.cache[key]
                    if key in self.last_cache_update:
                        del self.last_cache_update[key]
                
                logger.info(f"Log added: {level} - {message}")
            else:
                logger.error("Failed to add log entry")
                
        except Exception as e:
            logger.error(f"Error adding log: {e}")

    def clear_cache(self):
        """Czyści cache"""
        self.cache.clear()
        self.last_cache_update.clear()
        logger.info("Cache cleared")

    async def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Pobiera ostatnie transakcje"""
        try:
            await self.ensure_initialized()
            limit = ValidationHelper.validate_limit(limit)
            
            cache_key = f"recent_trades_{limit}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            if getattr(self, 'use_real_data', False):
                data = await self._get_real_recent_trades(limit)
            else:
                data = await self._get_sample_trades(limit)
            
            self._update_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return await self._get_sample_trades(limit)

    async def _get_real_recent_trades(self, limit: int) -> List[Dict[str, Any]]:
        """Pobiera rzeczywiste ostatnie transakcje z Binance i konwertuje do formatu dla UI"""
        try:
            from api.binance_api import get_binance_api
            binance = get_binance_api()
            symbol = "BTCUSDT"  # domyślny symbol dla widoku transakcji
            raw_trades = binance.get_recent_trades(symbol=symbol, limit=limit) or []
            
            def _fmt_pair(sym: str) -> str:
                sym = sym.upper()
                if sym.endswith("USDT"):
                    return f"{sym[:-4]}/USDT"
                if sym.endswith("USD"):
                    return f"{sym[:-3]}/USD"
                return sym
            
            trades: List[Dict[str, Any]] = []
            for t in raw_trades:
                ts_ms = t.get('time')
                try:
                    dt = datetime.fromtimestamp(ts_ms / 1000.0) if isinstance(ts_ms, (int, float)) else datetime.now()
                    time_str = dt.strftime('%H:%M:%S')
                except Exception:
                    time_str = str(ts_ms)
                price = float(t.get('price', 0) or 0)
                qty = float(t.get('qty', 0) or 0)
                is_buyer_maker = bool(t.get('isBuyerMaker', False))
                side = 'SELL' if is_buyer_maker else 'BUY'
                trades.append({
                    'time': time_str,
                    'bot': 'Binance',
                    'pair': _fmt_pair(symbol),
                    'side': side,
                    'amount': qty,
                    'price': price
                })
            return trades
        except Exception as e:
            logger.error(f"Error getting real recent trades: {e}")
            return await self._get_sample_trades(limit)

    async def _get_sample_trades(self, limit: int) -> List[Dict[str, Any]]:
        """Zwraca przykładowe transakcje w formacie zgodnym z UI"""
        try:
            now = datetime.now()
            trades = [
                {
                    'time': (now - timedelta(minutes=5)).strftime('%H:%M:%S'),
                    'bot': 'Scalper',
                    'pair': 'BTC/USDT',
                    'side': 'BUY',
                    'amount': 0.10,
                    'price': 42500.0
                },
                {
                    'time': (now - timedelta(minutes=15)).strftime('%H:%M:%S'),
                    'bot': 'DCA',
                    'pair': 'ETH/USDT',
                    'side': 'SELL',
                    'amount': 2.0,
                    'price': 2800.0
                }
            ]
            return trades[:limit]
        except Exception:
            return []

    async def get_alerts(self, limit: int = 50, unread_only: bool = False) -> List[AlertEntry]:
        """Pobiera alerty"""
        try:
            await self.ensure_initialized()
            limit = ValidationHelper.validate_limit(limit)
            
            cache_key = f"alerts_{limit}_{unread_only}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            if self.use_real_data:
                data = await self._get_real_alerts(limit, unread_only)
            else:
                data = await self._get_sample_alerts(limit, unread_only)
            
            self._update_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return await self._get_sample_alerts(limit, unread_only)

    async def _get_real_alerts(self, limit: int, unread_only: bool) -> List[AlertEntry]:
        """Pobiera rzeczywiste alerty z bazy"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                if unread_only:
                    cursor.execute('''
                        SELECT id, timestamp, type, severity, title, message, read, bot_id
                        FROM alerts 
                        WHERE read = 0
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                else:
                    cursor.execute('''
                        SELECT id, timestamp, type, severity, title, message, read, bot_id
                        FROM alerts 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                results = cursor.fetchall()
                
                if not results:
                    # Brak danych - wstaw przykładowe
                    sample_data = await self._get_sample_alerts(limit, unread_only)
                    await self._insert_sample_alerts(sample_data)
                    return sample_data
                
                alerts = []
                for row in results:
                    alerts.append(AlertEntry(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        type=row[2],
                        severity=row[3],
                        title=row[4],
                        message=row[5],
                        read=bool(row[6]),
                        bot_id=row[7]
                    ))
                
                return alerts
                
        except Exception as e:
            logger.error(f"Error getting real alerts: {e}")
            return await self._get_sample_alerts(limit, unread_only)

    async def _get_sample_alerts(self, limit: int, unread_only: bool) -> List[AlertEntry]:
        """Zwraca przykładowe alerty"""
        sample_alerts = [
            AlertEntry(
                id=1,
                timestamp=datetime.now() - timedelta(minutes=10),
                type="warning",
                severity="medium",
                title="High Volatility Alert",
                message="BTC volatility increased by 15% in the last hour",
                read=False,
                bot_id=None
            ),
            AlertEntry(
                id=2,
                timestamp=datetime.now() - timedelta(hours=1),
                type="info",
                severity="low",
                title="Bot Started",
                message="Bitcoin Scalper bot has been started successfully",
                read=True,
                bot_id="bot_001"
            ),
            AlertEntry(
                id=3,
                timestamp=datetime.now() - timedelta(hours=2),
                type="error",
                severity="high",
                title="Connection Error",
                message="Failed to connect to Binance API",
                read=False,
                bot_id="bot_002"
            )
        ]
        
        if unread_only:
            sample_alerts = [alert for alert in sample_alerts if not alert.read]
        
        return sample_alerts[:limit]

    async def _insert_sample_alerts(self, alerts: List[AlertEntry]):
        """Wstawia przykładowe alerty do bazy"""
        def insert_operation(cursor, conn):
            for alert in alerts:
                cursor.execute('''
                    INSERT INTO alerts (timestamp, type, severity, title, message, read, bot_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert.timestamp.isoformat(), alert.type, alert.severity,
                    alert.title, alert.message, alert.read, alert.bot_id
                ))
        
        self.db_helper.execute_with_retry(insert_operation)

    async def add_alert(self, alert_type: str, severity: str, title: str, 
                       message: str, bot_id: str = None):
        """Dodaje nowy alert"""
        try:
            alert_type = ValidationHelper.validate_alert_type(alert_type)
            severity = ValidationHelper.validate_severity(severity)
            bot_id = ValidationHelper.validate_bot_id(bot_id)
            
            def insert_operation(cursor, conn):
                cursor.execute('''
                    INSERT INTO alerts (type, severity, title, message, bot_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (alert_type, severity, title, message, bot_id))
            
            success = self.db_helper.execute_with_retry(insert_operation)
            
            if success:
                # Wyczyść cache alertów
                keys_to_remove = [k for k in self.cache.keys() if k.startswith('alerts_')]
                for key in keys_to_remove:
                    del self.cache[key]
                    if key in self.last_cache_update:
                        del self.last_cache_update[key]
                
                logger.info(f"Alert added: {title}")
            else:
                logger.error("Failed to add alert")
                
        except Exception as e:
            logger.error(f"Error adding alert: {e}")

    async def mark_alert_read(self, alert_id: int):
        """Oznacza alert jako przeczytany"""
        try:
            def update_operation(cursor, conn):
                cursor.execute('''
                    UPDATE alerts SET read = 1 WHERE id = ?
                ''', (alert_id,))
            
            success = self.db_helper.execute_with_retry(update_operation)
            
            if success:
                # Wyczyść cache alertów
                keys_to_remove = [k for k in self.cache.keys() if k.startswith('alerts_')]
                for key in keys_to_remove:
                    del self.cache[key]
                    if key in self.last_cache_update:
                        del self.last_cache_update[key]
                
                logger.info(f"Alert {alert_id} marked as read")
            else:
                logger.error(f"Failed to mark alert {alert_id} as read")
                
        except Exception as e:
            logger.error(f"Error marking alert as read: {e}")

    def set_real_data_mode(self, enabled: bool):
        """Ustawia tryb rzeczywistych danych"""
        self.use_real_data = enabled
        self.clear_cache()  # Wyczyść cache przy zmianie trybu
        logger.info(f"Real data mode {'enabled' if enabled else 'disabled'}")

    async def get_trading_mode(self) -> str:
        """Pobiera aktualny tryb handlowy"""
        try:
            cache_key = "trading_mode"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]

            app_db = await self._get_app_database()
            user_id = await self._resolve_default_user_id()
            mode = None
            if app_db is not None:
                mode = await app_db.get_trading_mode(user_id=user_id)
            if not mode:
                mode = "manual"
            self._update_cache(cache_key, mode)
            return mode

        except Exception as e:
            logger.error(f"Error getting trading mode: {e}")
            return "manual"

    async def set_trading_mode(self, mode: str):
        """Ustawia tryb handlowy"""
        try:
            valid_modes = ["manual", "auto", "semi-auto"]
            if mode not in valid_modes:
                raise ValueError(f"Invalid trading mode: {mode}")

            app_db = await self._get_app_database()
            user_id = await self._resolve_default_user_id()
            if app_db is not None:
                await app_db.set_trading_mode(mode, user_id=user_id)

            # Aktualizuj cache
            self._update_cache("trading_mode", mode)
            logger.info(f"Trading mode set to: {mode}")

        except Exception as e:
            logger.error(f"Error setting trading mode: {e}")

    async def get_risk_settings(self) -> Dict[str, Any]:
        """Pobiera ustawienia ryzyka"""
        try:
            cache_key = "risk_settings"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]

            app_db = await self._get_app_database()
            user_id = await self._resolve_default_user_id()
            settings: Dict[str, Any] = {}
            if app_db is not None:
                settings = await app_db.get_risk_settings_config(user_id=user_id)
            if not settings:
                settings = {
                    "max_risk_per_trade": 2.0,
                    "max_daily_loss": 5.0,
                    "stop_loss_percent": 3.0,
                    "take_profit_percent": 6.0,
                    "max_open_positions": 5
                }

            self._update_cache(cache_key, settings)
            return settings

        except Exception as e:
            logger.error(f"Error getting risk settings: {e}")
            return {}

    async def update_risk_settings(self, settings: Dict[str, Any]):
        """Aktualizuje ustawienia ryzyka"""
        try:
            app_db = await self._get_app_database()
            user_id = await self._resolve_default_user_id()
            if app_db is not None:
                await app_db.save_risk_settings_config(settings, user_id=user_id)

            # Aktualizuj cache
            self._update_cache("risk_settings", settings)
            logger.info("Risk settings updated")

        except Exception as e:
            logger.error(f"Error updating risk settings: {e}")

    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """Pobiera status konkretnego bota"""
        try:
            bot_id = ValidationHelper.validate_bot_id(bot_id)
            if not bot_id:
                raise ValueError("Invalid bot_id")
            
            # Pobierz dane bota
            bots = await self.get_bots_data()
            for bot in bots:
                if bot.id == bot_id:
                    return {
                        "id": bot.id,
                        "name": bot.name,
                        "status": bot.status,
                        "active": bot.active,
                        "profit": bot.profit,
                        "profit_percent": bot.profit_percent,
                        "trades_count": bot.trades_count,
                        "last_trade": bot.last_trade,
                        "risk_level": bot.risk_level
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting bot status for {bot_id}: {e}")
            return {}

    async def update_bot_status(self, bot_id: str, status: str, active: bool = None):
        """Aktualizuje status bota"""
        try:
            bot_id = ValidationHelper.validate_bot_id(bot_id)
            if not bot_id:
                raise ValueError("Invalid bot_id")
            
            def update_bot_operation(cursor, conn):
                if active is not None:
                    cursor.execute('''
                        UPDATE bots SET status = ?, active = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (status, active, bot_id))
                else:
                    cursor.execute('''
                        UPDATE bots SET status = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (status, bot_id))
            
            success = self.db_helper.execute_with_retry(update_bot_operation)
            
            if success:
                # Wyczyść cache botów
                keys_to_remove = [k for k in self.cache.keys() if k.startswith('bots_')]
                for key in keys_to_remove:
                    del self.cache[key]
                    if key in self.last_cache_update:
                        del self.last_cache_update[key]
                
                logger.info(f"Bot {bot_id} status updated to {status}")
            else:
                logger.error(f"Failed to update bot {bot_id} status")
                
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """Pobiera status całego systemu"""
        try:
            await self.ensure_initialized()
            
            # Pobierz dane z różnych źródeł
            portfolio = await self.get_portfolio_data()
            bots = await self.get_bots_data()
            trading_mode = await self.get_trading_mode()
            risk_settings = await self.get_risk_settings()
            
            # Oblicz statystyki
            active_bots = len([bot for bot in bots if bot.active])
            total_profit = sum(bot.profit for bot in bots)
            
            return {
                "initialized": self._initialized,
                "trading_mode": trading_mode,
                "total_bots": len(bots),
                "active_bots": active_bots,
                "total_profit": total_profit,
                "portfolio_value": portfolio.total_value,
                "risk_settings_loaded": bool(risk_settings),
                "database_connected": True,
                "last_updated": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "initialized": False,
                "error": str(e),
                "last_updated": datetime.now()
            }

# Singleton instance
_data_manager_instance = None

def get_data_manager() -> DataManager:
    """Zwraca singleton instance DataManager"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance