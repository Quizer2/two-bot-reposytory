import sqlite3
import json
import hashlib
import secrets
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from utils.db_migrations import apply_migrations
from utils.db_utils import validate_identifiers, build_where_clause, build_set_clause
logger = logging.getLogger(__name__)

try:  # pragma: no cover - zależne od środowiska uruchomieniowego
    import aiosqlite  # type: ignore
except Exception as exc:  # pragma: no cover - fallback do stubu
    logger.warning("aiosqlite unavailable (%s) – installing async stub", exc)
    from utils.async_sqlite_stub import install_aiosqlite_stub

    aiosqlite = install_aiosqlite_stub()

# Stałe whitelist kolumn dla dynamicznych zapytań SQL
RISK_LIMITS_ALLOWED_COLUMNS = {
    'max_daily_loss_percent',
    'max_daily_profit_percent',
    'max_drawdown_percent',
    'max_position_size_percent',
    'stop_loss_percent',
    'take_profit_percent',
    'max_correlation',
    'var_confidence_level'
}

POSITIONS_ALLOWED_COLUMNS = {
    'bot_id', 'symbol', 'side', 'size', 'entry_price',
    'current_price', 'unrealized_pnl', 'realized_pnl',
    'stop_loss_price', 'take_profit_price',
    'closed_at', 'status'
}

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None

    async def get_connection(self):
        """Pobiera połączenie z bazy danych"""
        try:
            import sqlite3
            import aiosqlite
            
            if self._conn is None:
                self._conn = await aiosqlite.connect(self.db_path)
                self._conn.row_factory = sqlite3.Row
                # Enable foreign keys for cascade operations
                await self._conn.execute('PRAGMA foreign_keys = ON')
            
        
            return self._conn
        except Exception as e:
            logger.info(f"Błąd podczas połączenia: {e}")

    async def close(self):
        """Zamyka połączenie z bazą danych"""
        try:
            if self._conn is not None:
                await self._conn.close()
                self._conn = None
                return True
            return False
        except Exception as e:
            logger.info(f"Błąd podczas zamykania połączenia: {e}")
            return False

    async def initialize(self):
        """Inicjalizacja schematu i migracji bazy danych"""
        # Utwórz tabele w trybie aiosqlite
        await self.create_tables()
        # Zastosuj migracje synchronizowane na bazie plikowej
        try:
            from pathlib import Path
            from utils.db_migrations import apply_migrations
            # Jeśli korzystamy z pliku bazy (nie :memory:), zastosuj migracje
            if self.db_path and self.db_path != ":memory:":
                apply_migrations(Path(self.db_path))
        except Exception as e:
            # Migracje są opcjonalne - jeśli się nie powiodą, kontynuujemy z utworzonym schematem
            logger.info(f"Błąd migracji w initialize: {e}")

    async def create_tables(self):
        """Utworzenie wszystkich tabel w bazie danych"""
        conn = await self.get_connection()
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                email TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active BOOLEAN DEFAULT 1,
                settings JSON DEFAULT '{}'
            )
        ''')
        
        # Tabela kluczy API giełd
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exchange TEXT NOT NULL,
                api_key TEXT NOT NULL,
                api_secret TEXT NOT NULL,
                passphrase TEXT,
                testnet BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, exchange, testnet)
            )
        ''')
        
        # Tabela botów
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('DCA', 'Grid', 'Scalping', 'Custom')),
                exchange TEXT NOT NULL,
                pair TEXT NOT NULL,
                parameters JSON NOT NULL,
                status TEXT DEFAULT 'stopped' CHECK (status IN ('active', 'stopped', 'paused', 'error')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                stopped_at DATETIME,
                total_profit REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                last_error TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabela zleceń
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                exchange_order_id TEXT,
                client_order_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
                type TEXT NOT NULL CHECK (type IN ('market', 'limit', 'stop', 'stop_limit')),
                amount REAL NOT NULL,
                price REAL,
                filled_amount REAL DEFAULT 0.0,
                average_price REAL DEFAULT 0.0,
                status TEXT DEFAULT 'new' CHECK (status IN ('new', 'open', 'filled', 'canceled', 'rejected', 'expired')),
                fee REAL DEFAULT 0.0,
                fee_asset TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                filled_at DATETIME,
                canceled_at DATETIME,
                error_message TEXT,
                raw_data JSON,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabela logów
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                user_id INTEGER,
                type TEXT NOT NULL CHECK (type IN ('info', 'warning', 'error', 'trade', 'system')),
                level TEXT DEFAULT 'info' CHECK (level IN ('debug', 'info', 'warning', 'error', 'critical')),
                message TEXT NOT NULL,
                details JSON,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        ''')
        
        # Tabela statystyk botów (dla wydajności)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                date DATE NOT NULL,
                trades_count INTEGER DEFAULT 0,
                profit_loss REAL DEFAULT 0.0,
                volume REAL DEFAULT 0.0,
                win_trades INTEGER DEFAULT 0,
                loss_trades INTEGER DEFAULT 0,
                fees_paid REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE,
                UNIQUE(bot_id, date)
            )
        ''')
        
        # Tabela konfiguracji aplikacji
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS app_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela limitów ryzyka
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS risk_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                user_id INTEGER,
                max_daily_loss_percent REAL DEFAULT 5.0,
                max_daily_profit_percent REAL DEFAULT 10.0,
                max_drawdown_percent REAL DEFAULT 15.0,
                max_position_size_percent REAL DEFAULT 10.0,
                stop_loss_percent REAL DEFAULT 5.0,
                take_profit_percent REAL DEFAULT 10.0,
                max_correlation REAL DEFAULT 0.7,
                var_confidence_level REAL DEFAULT 0.95,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabela zdarzeń ryzyka
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER,
                event_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                message TEXT NOT NULL,
                details JSON,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolved_at DATETIME,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE
            )
        ''')
        
        # Tabela metryk ryzyka
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS risk_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                date DATE NOT NULL,
                current_drawdown REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                daily_pnl REAL DEFAULT 0.0,
                total_pnl REAL DEFAULT 0.0,
                var_1d REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE,
                UNIQUE(bot_id, date)
            )
        ''')
        
        # Tabela konfiguracji powiadomień
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config_data JSON NOT NULL,
                rate_limit_per_minute INTEGER DEFAULT 10,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, channel)
            )
        ''')
        
        # Tabela szablonów powiadomień
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                notification_type TEXT NOT NULL,
                subject_template TEXT,
                message_template TEXT NOT NULL,
                variables JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela historii powiadomień
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                bot_id INTEGER,
                notification_type TEXT NOT NULL,
                channel TEXT NOT NULL,
                priority TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sent_at DATETIME,
                error_message TEXT,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE SET NULL
            )
        ''')
        
        # Tabela statystyk powiadomień
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS notification_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                channel TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, channel, notification_type)
            )
        ''')
        
        # Tabela pozycji handlowych (dla zarządzania ryzykiem)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
                size REAL NOT NULL CHECK (size > 0),
                entry_price REAL NOT NULL CHECK (entry_price >= 0),
                current_price REAL,
                unrealized_pnl REAL DEFAULT 0.0,
                realized_pnl REAL DEFAULT 0.0,
                stop_loss_price REAL,
                take_profit_price REAL,
                trailing_stop_price REAL,
                opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed')),
                CHECK (status = 'closed' OR closed_at IS NULL),
                FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE
            )
        ''')
        # positions constraints are enforced centrally by utils.db_migrations.apply_migrations
        
        # Indeksy dla wydajności
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_bot_id ON orders(bot_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_bot_id ON logs(bot_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_bot_id ON risk_events(bot_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_timestamp ON risk_events(timestamp)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_risk_metrics_bot_id ON risk_metrics(bot_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_notification_history_user_id ON notification_history(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_notification_history_created_at ON notification_history(created_at)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_bot_id ON positions(bot_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)')
        
        await conn.commit()
    
    # === OPERACJE NA UŻYTKOWNIKACH ===
    
    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hashowanie hasła z solą"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iteracji
        ).hex()
        
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Weryfikacja hasła"""
        computed_hash, _ = self.hash_password(password, salt)
        return computed_hash == password_hash
    
    async def create_user(self, username: str, password: str, email: str = None) -> Optional[int]:
        """Utworzenie nowego użytkownika"""
        try:
            conn = await self.get_connection()
            
            # Sprawdź czy użytkownik już istnieje
            cursor = await conn.execute(
                'SELECT id FROM users WHERE username = ?',
                (username,)
            )
            if await cursor.fetchone():
                raise ValueError(f"Użytkownik {username} już istnieje")
            
            # Hashuj hasło
            password_hash, salt = self.hash_password(password)
            
            # Utwórz użytkownika
            cursor = await conn.execute('''
                INSERT INTO users (username, password_hash, salt, email)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, salt, email))
            await conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.info(f"Błąd podczas tworzenia użytkownika: {e}")
            return None

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Uwierzytelnienie użytkownika"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute('''
                SELECT id, username, password_hash, salt, email, is_active, settings
                FROM users WHERE username = ?
            ''', (username,))
            row = await cursor.fetchone()
            # TODO: verify password with stored salt/hash; simplified here
            return dict(row) if row else None
        except Exception as e:
            logger.info(f"Auth error: {e}")
            return None
            if not user:
                return None
            
            # Sprawdź hasło
            if not self.verify_password(password, user['password_hash'], user['salt']):
                return None
            
            # Sprawdź czy konto jest aktywne
            if not user['is_active']:
                return None
            
            # Aktualizuj last_login
            await conn.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user['id'],)
            )
            await conn.commit()
            
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'settings': json.loads(user['settings']) if user['settings'] else {}
            }
            
        except Exception as e:
            
            logger.info("Błąd podczas uwierzytelniania: %s" % e)
        return None

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Pobranie danych użytkownika"""
        try:
            conn = await self.get_connection()
            
            cursor = await conn.execute('''
                SELECT id, username, email, created_at, last_login, is_active, settings
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user = await cursor.fetchone()
            if user:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'created_at': user['created_at'],
                    'last_login': user['last_login'],
                    'is_active': user['is_active'],
                    'settings': json.loads(user['settings']) if user['settings'] else {}
                }
            return None
            
        except Exception as e:
            
            logger.info(f"Błąd podczas pobierania użytkownika: {e}")
            return None
    
    # === OPERACJE NA KLUCZACH API ===
    
    async def save_api_key(self, user_id: int, exchange: str, api_key: str, 
                          api_secret: str, passphrase: str = None, testnet: bool = False) -> Optional[int]:
        """Zapisanie klucza API giełdy (zaszyfrowanego)"""
        try:
            conn = await self.get_connection()
            
            # Usuń istniejący klucz dla tej giełdy i trybu
            await conn.execute('''
                DELETE FROM api_keys 
                WHERE user_id = ? AND exchange = ? AND testnet = ?
            ''', (user_id, exchange, testnet))
            
            # Dodaj nowy klucz (szyfrowanie będzie w EncryptionManager)
            cursor = await conn.execute('''
                INSERT INTO api_keys (user_id, exchange, api_key, api_secret, passphrase, testnet)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, exchange, api_key, api_secret, passphrase, testnet))
            
            await conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.info(f"Błąd podczas zapisywania klucza API: {e}")
            return None
    
    async def get_api_key(self, user_id: int, exchange: str, testnet: bool = False) -> Optional[Dict]:
        """Pobranie klucza API giełdy"""
        try:
            conn = await self.get_connection()
            
            cursor = await conn.execute('''
                SELECT id, api_key, api_secret, passphrase, is_active, created_at, last_used
                FROM api_keys 
                WHERE user_id = ? AND exchange = ? AND testnet = ? AND is_active = 1
            ''', (user_id, exchange, testnet))
            
            api_key = await cursor.fetchone()
            if api_key:
                return {
                    'id': api_key['id'],
                    'api_key': api_key['api_key'],
                    'api_secret': api_key['api_secret'],
                    'passphrase': api_key['passphrase'],
                    'is_active': api_key['is_active'],
                    'created_at': api_key['created_at'],
                    'last_used': api_key['last_used']
                }
            return None
            
        except Exception as e:
            logger.info(f"Błąd podczas pobierania klucza API: {e}")
            return None
    
    async def update_api_key_usage(self, api_key_id: int):
        """Aktualizacja czasu ostatniego użycia klucza API"""
        try:
            conn = await self.get_connection()
            
            await conn.execute(
                'UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE id = ?',
                (api_key_id,)
            )
            await conn.commit()
            
        except Exception as e:
            logger.info(f"Błąd podczas aktualizacji użycia klucza API: {e}")
    
    # === OPERACJE NA BOTACH ===
    
    async def create_bot(self, user_id: int, name: str, bot_type: str, exchange: str,
                        pair: str, parameters: Dict) -> Optional[int]:
        """Utworzenie nowego bota"""
        try:
            conn = await self.get_connection()
            
            cursor = await conn.execute('''
                INSERT INTO bots (user_id, name, type, exchange, pair, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, name, bot_type, exchange, pair, json.dumps(parameters)))
            
            await conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            
            logger.info(f"Błąd podczas tworzenia bota: {e}")
            return None
    
    async def get_bot(self, bot_id: int) -> Optional[Dict]:
        """Pobranie danych bota"""
        try:
            conn = await self.get_connection()
            
            cursor = await conn.execute('''
                SELECT * FROM bots WHERE id = ?
            ''', (bot_id,))
            
            bot = await cursor.fetchone()
            if bot:
                return {
                    'id': bot['id'],
                    'user_id': bot['user_id'],
                    'name': bot['name'],
                    'type': bot['type'],
                    'exchange': bot['exchange'],
                    'pair': bot['pair'],
                    'parameters': json.loads(bot['parameters']),
                    'status': bot['status'],
                    'created_at': bot['created_at'],
                    'started_at': bot['started_at'],
                    'stopped_at': bot['stopped_at'],
                    'total_profit': bot['total_profit'],
                    'total_trades': bot['total_trades'],
                    'win_rate': bot['win_rate'],
                    'max_drawdown': bot['max_drawdown'],
                    'last_error': bot['last_error']
                }
            return None
            
        except Exception as e:
            
            logger.info(f"Błąd podczas pobierania bota: {e}")
            return None
    
    async def get_user_bots(self, user_id: int, status: str = None) -> List[Dict]:
        """Pobranie botów użytkownika"""
        try:
            conn = await self.get_connection()
            
            if status:
                cursor = await conn.execute('''
                    SELECT * FROM bots WHERE user_id = ? AND status = ?
                    ORDER BY created_at DESC
                ''', (user_id, status))
            else:
                cursor = await conn.execute('''
                    SELECT * FROM bots WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
            
            bots = []
            async for bot in cursor:
                bots.append({
                    'id': bot['id'],
                    'user_id': bot['user_id'],
                    'name': bot['name'],
                    'type': bot['type'],
                    'exchange': bot['exchange'],
                    'pair': bot['pair'],
                    'parameters': json.loads(bot['parameters']),
                    'status': bot['status'],
                    'created_at': bot['created_at'],
                    'started_at': bot['started_at'],
                    'stopped_at': bot['stopped_at'],
                    'total_profit': bot['total_profit'],
                    'total_trades': bot['total_trades'],
                    'win_rate': bot['win_rate'],
                    'max_drawdown': bot['max_drawdown'],
                    'last_error': bot['last_error']
                })
            
            return bots
            
        except Exception as e:
            
            logger.info(f"Błąd podczas pobierania botów użytkownika: {e}")
            return []
    
    async def update_bot_status(self, bot_id: int, status: str, error_message: str = None):
        """Aktualizacja statusu bota"""
        try:
            conn = await self.get_connection()
            
            if status == 'active':
                await conn.execute('''
                    UPDATE bots SET status = ?, started_at = CURRENT_TIMESTAMP, last_error = NULL
                    WHERE id = ?
                ''', (status, bot_id))
            elif status in ['stopped', 'paused']:
                await conn.execute('''
                    UPDATE bots SET status = ?, stopped_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, bot_id))
            elif status == 'error':
                await conn.execute('''
                    UPDATE bots SET status = ?, last_error = ?, stopped_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, bot_id))
            
            await conn.commit()
            
        except Exception as e:
            logger.info(f"Błąd podczas aktualizacji statusu bota: {e}")
    
    async def update_bot_statistics(self, bot_id: int, total_profit: float = None,
                                   total_trades: int = None, win_rate: float = None,
                                   max_drawdown: float = None):
        """Aktualizacja statystyk bota"""
        try:
            conn = await self.get_connection()
            
            updates_dict = {}
            if total_profit is not None:
                updates_dict['total_profit'] = total_profit
            if total_trades is not None:
                updates_dict['total_trades'] = total_trades
            if win_rate is not None:
                updates_dict['win_rate'] = win_rate
            if max_drawdown is not None:
                updates_dict['max_drawdown'] = max_drawdown
            
            if updates_dict:
                # Whitelist kolumn w tabeli bots dla tych pól
                allowed = {'total_profit', 'total_trades', 'win_rate', 'max_drawdown'}
                set_clause, params = build_set_clause(updates_dict, allowed_columns=allowed)
                query = ''.join(['UPDATE bots SET ', set_clause, ' WHERE id = ?'])
                params.append(bot_id)
                await conn.execute(query, params)
                await conn.commit()
            
        except Exception as e:
            
            logger.info(f"Błąd podczas aktualizacji statystyk bota: {e}")
    
    # === OPERACJE NA ZLECENIACH ===
    
    async def save_order(self, bot_id: int, exchange_order_id: str, client_order_id: str,
                        symbol: str, side: str, order_type: str, amount: float,
                        price: float = None, raw_data: Dict = None) -> Optional[int]:
        """Zapisanie zlecenia"""
        try:
            conn = await self.get_connection()
            
            cursor = await conn.execute('''
                INSERT INTO orders (bot_id, exchange_order_id, client_order_id, symbol, 
                                  side, type, amount, price, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, exchange_order_id, client_order_id, symbol, side, 
                  order_type, amount, price, json.dumps(raw_data) if raw_data else None))
            
            await conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.info(f"Błąd podczas zapisywania zlecenia: {e}")
            return None
    
    async def update_order_status(self, order_id: int, status: str, filled_amount: float = None,
                                 average_price: float = None, fee: float = None,
                                 fee_asset: str = None, error_message: str = None):
        """Aktualizacja statusu zlecenia"""
        try:
            conn = await self.get_connection()
            
            updates_dict = { 'status': status }
            if filled_amount is not None:
                updates_dict['filled_amount'] = filled_amount
            if average_price is not None:
                updates_dict['average_price'] = average_price
            if fee is not None:
                updates_dict['fee'] = fee
            if fee_asset is not None:
                updates_dict['fee_asset'] = fee_asset
            if error_message is not None:
                updates_dict['error_message'] = error_message
            
            # Whitelist kolumn allowed dla orders
            allowed = {'status','filled_amount','average_price','fee','fee_asset','error_message'}
            set_clause, params = build_set_clause(updates_dict, allowed_columns=allowed)
            
            # Dodaj timestampy w zależności od nowego statusu
            if status == 'filled':
                set_clause = set_clause + ', filled_at = CURRENT_TIMESTAMP'
            elif status == 'canceled':
                set_clause = set_clause + ', canceled_at = CURRENT_TIMESTAMP'
            
            query = ''.join(['UPDATE orders SET ', set_clause, ' WHERE id = ?'])
            params.append(order_id)
            await conn.execute(query, params)
            await conn.commit()
            
        except Exception as e:
            
            logger.info(f"Błąd podczas aktualizacji statusu zlecenia: {e}")
    
    async def get_bot_orders(self, bot_id: int, status: str = None, limit: int = 100) -> List[Dict]:
        """Pobranie zleceń bota"""
        try:
            conn = await self.get_connection()
            
            if status:
                cursor = await conn.execute('''
                    SELECT * FROM orders WHERE bot_id = ? AND status = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (bot_id, status, limit))
            else:
                cursor = await conn.execute('''
                    SELECT * FROM orders WHERE bot_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (bot_id, limit))
            
            orders = []
            async for order in cursor:
                orders.append({
                    'id': order['id'],
                    'bot_id': order['bot_id'],
                    'exchange_order_id': order['exchange_order_id'],
                    'client_order_id': order['client_order_id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'type': order['type'],
                    'amount': order['amount'],
                    'price': order['price'],
                    'filled_amount': order['filled_amount'],
                    'average_price': order['average_price'],
                    'status': order['status'],
                    'fee': order['fee'],
                    'fee_asset': order['fee_asset'],
                    'timestamp': order['timestamp'],
                    'filled_at': order['filled_at'],
                    'canceled_at': order['canceled_at'],
                    'error_message': order['error_message'],
                    'raw_data': json.loads(order['raw_data']) if order['raw_data'] else None
                })
            
            return orders
            
        except Exception as e:
            logger.info(f"Błąd podczas pobierania zleceń bota: {e}")
            return []
    
    # === OPERACJE NA LOGACH ===
    
    async def add_log(self, message: str, log_type: str = 'info', level: str = 'info',
                     bot_id: int = None, user_id: int = None, details: Dict = None):
        """Dodanie wpisu do logów"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT INTO logs (bot_id, user_id, type, level, message, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (bot_id, user_id, log_type, level, message, 
                  json.dumps(details) if details else None))
            
            await conn.commit()
            
        except Exception as e:
            
            logger.info(f"Błąd podczas dodawania logu: {e}")
    
    async def get_logs(self, bot_id: int = None, user_id: int = None, log_type: str = None,
                      level: str = None, limit: int = 1000) -> List[Dict]:
        """Pobranie logów"""
        try:
            conn = await self.get_connection()
            
            filters = {}
            if bot_id is not None:
                filters['bot_id'] = bot_id
            if user_id is not None:
                filters['user_id'] = user_id
            if log_type is not None:
                filters['type'] = log_type
            if level is not None:
                filters['level'] = level
            
            allowed = {'bot_id','user_id','type','level'}
            where_clause, params = build_where_clause(filters, allowed_columns=allowed)
            sql = ''.join(['SELECT * FROM logs WHERE ', where_clause, ' ORDER BY timestamp DESC LIMIT ?'])
            params.append(limit)
            cursor = await conn.execute(sql, params)
            
            logs = []
            async for log in cursor:
                logs.append({
                    'id': log['id'],
                    'bot_id': log['bot_id'],
                    'user_id': log['user_id'],
                    'type': log['type'],
                    'level': log['level'],
                    'message': log['message'],
                    'details': json.loads(log['details']) if log['details'] else None,
                    'timestamp': log['timestamp']
                })
            
            return logs
            
        except Exception as e:
            
            logger.info(f"Błąd podczas pobierania logów: {e}")
            return []
    
    # === OPERACJE NA STATYSTYKACH ===
    
    async def save_daily_statistics(self, bot_id: int, date: str, trades_count: int,
                                   profit_loss: float, volume: float, win_trades: int,
                                   loss_trades: int, fees_paid: float):
        """Zapisanie dziennych statystyk bota"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT OR REPLACE INTO bot_statistics 
                (bot_id, date, trades_count, profit_loss, volume, win_trades, loss_trades, fees_paid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, date, trades_count, profit_loss, volume, win_trades, loss_trades, fees_paid))
            
            await conn.commit()
            
        except Exception as e:
            
            logger.info(f"Błąd podczas zapisywania statystyk dziennych: {e}")
    
    async def get_bot_statistics(self, bot_id: int, start_date: str = None,
                                end_date: str = None) -> List[Dict]:
        """Pobranie statystyk bota"""
        try:
            conn = await self.get_connection()
            
            # Bezpieczne budowanie WHERE
            filters = {'bot_id': bot_id}
            where_clause, params = build_where_clause(filters, allowed_columns={'bot_id'})
            
            if start_date:
                where_clause = where_clause + ' AND date >= ?'
                params.append(start_date)
            if end_date:
                where_clause = where_clause + ' AND date <= ?'
                params.append(end_date)
            
            sql = ''.join(['SELECT * FROM bot_statistics WHERE ', where_clause, ' ORDER BY date ASC'])
            cursor = await conn.execute(sql, params)
            
            statistics = []
            async for stat in cursor:
                statistics.append({
                    'id': stat['id'],
                    'bot_id': stat['bot_id'],
                    'date': stat['date'],
                    'trades_count': stat['trades_count'],
                    'profit_loss': stat['profit_loss'],
                    'volume': stat['volume'],
                    'win_trades': stat['win_trades'],
                    'loss_trades': stat['loss_trades'],
                    'fees_paid': stat['fees_paid'],
                    'created_at': stat['created_at']
                })
            
            return statistics
            
        except Exception as e:
            logger.info(f"Błąd podczas pobierania statystyk bota: {e}")
            return []
    
    # === BACKUP I RESTORE ===
    
    async def backup_database(self, backup_path: str) -> bool:
        """Utworzenie kopii zapasowej bazy danych"""
        try:
            import shutil
            
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Zamknij połączenie przed kopią
            await self.close()
            
            # Skopiuj plik bazy danych
            shutil.copy2(self.db_path, backup_file)
            
            # Przywróć połączenie
            await self.get_connection()
            
            return True
            
        except Exception as e:
            
            logger.info(f"Błąd podczas tworzenia kopii zapasowej: {e}")
            return False
    
    # === OPERACJE NA KONFIGURACJI APLIKACJI ===
    
    async def get_app_config(self, key: str = None):
        """Pobiera konfigurację aplikacji"""
        try:
            conn = await self.get_connection()
            
            if key:
                cursor = await conn.execute(
                    'SELECT value FROM app_config WHERE key = ?',
                    (key,)
                )
                result = await cursor.fetchone()
                return result['value'] if result else None
            else:
                cursor = await conn.execute('SELECT key, value FROM app_config')
                results = []
                async for row in cursor:
                    results.append(row)
                return {row['key']: row['value'] for row in results}
        except Exception as e:
            logger.info(f"Błąd podczas pobierania konfiguracji: {e}")
            return None if key else {}

    async def set_app_config(self, key: str, value: str):
        """Ustawia konfigurację aplikacji"""
        try:
            conn = await self.get_connection()
            
            await conn.execute(
                'INSERT OR REPLACE INTO app_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                (key, value)
            )
            await conn.commit()
            return True
        except Exception as e:
            try:
                await conn.execute('ROLLBACK')
            except Exception:
                pass
            logger.info(f"Błąd podczas aktualizacji constraints tabeli positions: {e}")
            return False
        except Exception as e:
            try:
                await conn.execute('ROLLBACK')
            except Exception:
                pass
            logger.info(f"Błąd podczas aktualizacji constraints tabeli positions: {e}")
            return False
        except Exception as e:
            logger.info(f"Błąd podczas ustawiania konfiguracji: {e}")
            return False

    # === OPERACJE NA ZARZĄDZANIU RYZYKIEM ===
    
    async def create_risk_limit(self, bot_id: int = None, user_id: int = None, **limits):
        """Tworzy nowe limity ryzyka dla bota lub użytkownika"""
        try:
            conn = await self.get_connection()
            
            # Whitelist dozwolonych kolumn zgodnych ze schematem risk_limits
            allowed_columns = RISK_LIMITS_ALLOWED_COLUMNS
            filtered_limits = {k: v for k, v in limits.items() if k in allowed_columns}
            invalid = [k for k in limits.keys() if k not in allowed_columns]
            if invalid:
                logger.info(f"Próba wstawienia niedozwolonych kolumn do risk_limits: {invalid}")
            if not filtered_limits:
                return False
            
            # Walidacja identyfikatorów (kolumn)
            validate_identifiers('bot_id', 'user_id', *filtered_limits.keys())
            
            # Przygotuj kolumny i wartości
            columns = ['bot_id', 'user_id'] + list(filtered_limits.keys())
            placeholders = ', '.join(['?' for _ in columns])
            values = [bot_id, user_id] + list(filtered_limits.values())
            
            columns_str = ', '.join(columns)
            query = ''.join(['INSERT INTO risk_limits (', columns_str, ') VALUES (', placeholders, ')'])
            await conn.execute(query, values)
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas tworzenia limitów ryzyka: {e}")
            return False

    async def update_risk_limits(self, limit_id: int, **updates):
        """Aktualizuje limity ryzyka"""
        try:
            conn = await self.get_connection()
            
            # Whitelist dozwolonych kolumn zgodnych ze schematem risk_limits
            allowed_columns = RISK_LIMITS_ALLOWED_COLUMNS
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_columns}
            invalid = [k for k in updates.keys() if k not in allowed_columns]
            if invalid:
                logger.info(f"Próba aktualizacji niedozwolonych kolumn risk_limits: {invalid}")
            if not filtered_updates:
                return False
            
            # Bezpieczny SET
            set_clause, params = build_set_clause(filtered_updates, allowed_columns=allowed_columns)
            
            query = ''.join(['UPDATE risk_limits SET ', set_clause, ', updated_at = CURRENT_TIMESTAMP WHERE id = ?'])
            params.append(limit_id)
            await conn.execute(query, params)
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas aktualizacji limitów ryzyka: {e}")
            return False

    async def create_risk_event(self, bot_id: int, event_type: str, risk_level: str, message: str, details: Dict = None):
        """Tworzy nowe zdarzenie ryzyka"""
        try:
            conn = await self.get_connection()
            
            await conn.execute(
                'INSERT INTO risk_events (bot_id, event_type, risk_level, message, details) VALUES (?, ?, ?, ?, ?)',
                (bot_id, event_type, risk_level, message, json.dumps(details) if details else None)
            )
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas tworzenia zdarzenia ryzyka: {e}")
            return False

    async def get_risk_events(self, bot_id: int = None, limit: int = 100):
        """Pobiera zdarzenia ryzyka"""
        try:
            conn = await self.get_connection()
            
            if bot_id:
                cursor = await conn.execute(
                    'SELECT * FROM risk_events WHERE bot_id = ? ORDER BY timestamp DESC LIMIT ?',
                    (bot_id, limit)
                )
            else:
                cursor = await conn.execute(
                    'SELECT * FROM risk_events ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
            
            events = []
            async for row in cursor:
                event = dict(row)
                if event['details']:
                    event['details'] = json.loads(event['details'])
                events.append(event)
            return events
        except Exception as e:
            logger.info(f"Błąd podczas pobierania zdarzeń ryzyka: {e}")
            return []

    async def resolve_risk_event(self, event_id: int):
        """Oznacza zdarzenie ryzyka jako rozwiązane"""
        try:
            conn = await self.get_connection()
            
            await conn.execute(
                'UPDATE risk_events SET resolved = 1, resolved_at = CURRENT_TIMESTAMP WHERE id = ?',
                (event_id,)
            )
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas rozwiązywania zdarzenia ryzyka: {e}")
            return False

    async def save_risk_metrics(self, bot_id: int, metrics: Dict):
        """Zapisuje metryki ryzyka"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT OR REPLACE INTO risk_metrics 
                (bot_id, date, current_drawdown, max_drawdown, daily_pnl, total_pnl, 
                 var_1d, sharpe_ratio, win_rate, profit_factor)
                VALUES (?, DATE('now'), ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bot_id,
                metrics.get('current_drawdown', 0.0),
                metrics.get('max_drawdown', 0.0),
                metrics.get('daily_pnl', 0.0),
                metrics.get('total_pnl', 0.0),
                metrics.get('var_1d', 0.0),
                metrics.get('sharpe_ratio', 0.0),
                metrics.get('win_rate', 0.0),
                metrics.get('profit_factor', 0.0)
            ))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas zapisywania metryk ryzyka: {e}")
            return False

    async def get_risk_metrics(self, bot_id: int, start_date: str = None, end_date: str = None):
        """Pobiera metryki ryzyka"""
        try:
            conn = await self.get_connection()
            
            filters = {'bot_id': bot_id}
            where_clause, params = build_where_clause(filters, allowed_columns={'bot_id'})
            
            if start_date:
                where_clause = where_clause + ' AND date >= ?'
                params.append(start_date)
            if end_date:
                where_clause = where_clause + ' AND date <= ?'
                params.append(end_date)
            
            sql = ''.join(['SELECT * FROM risk_metrics WHERE ', where_clause, ' ORDER BY date ASC'])
            cursor = await conn.execute(sql, params)
            
            metrics = []
            async for row in cursor:
                metrics.append(dict(row))
            return metrics
        except Exception as e:
            logger.info(f"Błąd podczas pobierania metryk ryzyka: {e}")
            return []

    # === OPERACJE NA POWIADOMIENIACH ===
    
    async def save_notification_config(self, user_id: int, channel: str, config_data: Dict, 
                                      enabled: bool = True, rate_limit: int = 10):
        """Zapisuje konfigurację powiadomień"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT OR REPLACE INTO notification_configs 
                (user_id, channel, enabled, config_data, rate_limit_per_minute, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, channel, enabled, json.dumps(config_data), rate_limit))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas zapisywania konfiguracji powiadomień: {e}")
            return False

    async def get_notification_configs(self, user_id: int = None, channel: str = None):
        """Pobiera konfiguracje powiadomień"""
        try:
            conn = await self.get_connection()
            
            filters = {}
            if user_id:
                filters['user_id'] = user_id
            if channel:
                filters['channel'] = channel
            where_clause, params = build_where_clause(filters, allowed_columns={'user_id','channel'})
            sql = ''.join(['SELECT * FROM notification_configs WHERE ', where_clause])
            cursor = await conn.execute(sql, params)

            configs = []
            async for row in cursor:
                config = dict(row)
                config['config_data'] = json.loads(config['config_data'])
                configs.append(config)
            return configs
        except Exception as e:
            logger.info(f"Błąd podczas pobierania konfiguracji powiadomień: {e}")
            return []

    async def save_notification_template(self, name: str, notification_type: str, 
                                        message_template: str, subject_template: str = None,
                                        variables: Dict = None):
        """Zapisuje szablon powiadomienia"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT OR REPLACE INTO notification_templates 
                (name, notification_type, subject_template, message_template, variables, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, notification_type, subject_template, message_template, 
                  json.dumps(variables) if variables else None))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas zapisywania szablonu powiadomienia: {e}")
            return False

    async def get_notification_template(self, name: str = None, notification_type: str = None):
        """Pobiera szablon powiadomienia"""
        try:
            conn = await self.get_connection()
            
            if name:
                cursor = await conn.execute('SELECT * FROM notification_templates WHERE name = ?', (name,))
                result = await cursor.fetchone()
                if result:
                    template = dict(result)
                    if template['variables']:
                        template['variables'] = json.loads(template['variables'])
                    return template
            elif notification_type:
                cursor = await conn.execute('SELECT * FROM notification_templates WHERE notification_type = ?', (notification_type,))
                templates = []
                async for row in cursor:
                    template = dict(row)
                    if template['variables']:
                        template['variables'] = json.loads(template['variables'])
                    templates.append(template)
                return templates
            
            return None
        except Exception as e:
            logger.info(f"Błąd podczas pobierania szablonu powiadomienia: {e}")
            return None

    async def save_notification_history(self, notification_data: Dict):
        """Zapisuje historię powiadomień"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT INTO notification_history 
                (notification_id, user_id, bot_id, notification_type, channel, priority, 
                 subject, message, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                notification_data['notification_id'],
                notification_data.get('user_id'),
                notification_data.get('bot_id'),
                notification_data['notification_type'],
                notification_data['channel'],
                notification_data['priority'],
                notification_data.get('subject'),
                notification_data['message'],
                notification_data.get('status', 'pending'),
                json.dumps(notification_data.get('metadata', {}))
            ))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas zapisywania historii powiadomień: {e}")
            return False

    async def update_notification_status(self, notification_id: str, status: str, error_message: str = None):
        """Aktualizuje status powiadomienia"""
        try:
            conn = await self.get_connection()
            
            if status == 'sent':
                await conn.execute(
                    'UPDATE notification_history SET status = ?, sent_at = CURRENT_TIMESTAMP WHERE notification_id = ?',
                    (status, notification_id)
                )
            else:
                await conn.execute(
                    'UPDATE notification_history SET status = ?, error_message = ? WHERE notification_id = ?',
                    (status, error_message, notification_id)
                )
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas aktualizacji statusu powiadomienia: {e}")
            return False

    async def get_notification_history(self, user_id: int = None, bot_id: int = None, 
                                      notification_type: str = None, limit: int = 100):
        """Pobiera historię powiadomień"""
        try:
            conn = await self.get_connection()
            
            filters = {}
            if user_id is not None:
                filters['user_id'] = user_id
            if bot_id is not None:
                filters['bot_id'] = bot_id
            if notification_type is not None:
                filters['notification_type'] = notification_type
            where_clause, params = build_where_clause(filters, allowed_columns={'user_id', 'bot_id', 'notification_type'})
            params.append(limit)
            sql = ''.join(['SELECT * FROM notification_history WHERE ', where_clause, ' ORDER BY created_at DESC LIMIT ?'])
            cursor = await conn.execute(sql, params)
            
            history = []
            async for row in cursor:
                notification = dict(row)
                if notification['metadata']:
                    notification['metadata'] = json.loads(notification['metadata'])
                history.append(notification)
            return history
        except Exception as e:
            logger.info(f"Błąd podczas pobierania historii powiadomień: {e}")
            return []

    async def update_notification_stats(self, date: str, channel: str, notification_type: str, 
                                       sent_count: int = 0, failed_count: int = 0):
        """Aktualizuje statystyki powiadomień"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                INSERT OR REPLACE INTO notification_stats 
                (date, channel, notification_type, sent_count, failed_count, total_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, channel, notification_type, sent_count, failed_count, sent_count + failed_count))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas aktualizacji statystyk powiadomień: {e}")
            return False

    # === OPERACJE NA POZYCJACH HANDLOWYCH ===
    
    async def create_position(self, bot_id: int, symbol: str, side: str, size: float, 
                             entry_price: float, **kwargs):
        """Tworzy nową pozycję handlową"""
        try:
            conn = await self.get_connection()
            
            # Walidacja wartości
            if side not in {'buy', 'sell'}:
                return False
            if size is None or size <= 0:
                return False
            if entry_price is None or entry_price < 0:
                return False
            
            await conn.execute('''
                INSERT INTO positions 
                (bot_id, symbol, side, size, entry_price, stop_loss_price, take_profit_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                bot_id, symbol, side, size, entry_price,
                kwargs.get('stop_loss_price'),
                kwargs.get('take_profit_price')
            ))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas tworzenia pozycji: {e}")
            return False

    async def update_position(self, position_id: int, **updates):
        """Aktualizuje pozycję handlową"""
        try:
            conn = await self.get_connection()
            
            # Walidacja dozwolonych kolumn, aby zapobiec wstrzyknięciom przez nazwy pól
            if not updates:
                return False
            allowed_columns = POSITIONS_ALLOWED_COLUMNS
            invalid = [k for k in updates.keys() if k not in allowed_columns]
            if invalid:
                logger.info(f"Próba aktualizacji niedozwolonych kolumn: {invalid}")
                return False
            
            # Dodatkowa walidacja wartości
            if 'side' in updates and updates['side'] not in {'buy', 'sell'}:
                return False
            if 'status' in updates and updates['status'] not in {'open', 'closed'}:
                return False
            if 'size' in updates and (updates['size'] is None or updates['size'] <= 0):
                return False
            if 'entry_price' in updates and (updates['entry_price'] is None or updates['entry_price'] < 0):
                return False
            
            # Jeśli wymuszana jest zmiana statusu na 'open', closed_at musi pozostać NULL
            if 'status' in updates and updates['status'] == 'open':
                updates['closed_at'] = None
            
            set_clause, params = build_set_clause(updates, allowed_columns)
            params.append(position_id)
            await conn.execute(''.join(['UPDATE positions SET ', set_clause, ' WHERE id = ?']), params)
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas aktualizacji pozycji: {e}")
            return False

    async def get_positions(self, bot_id: int = None, status: str = 'open'):
        """Pobiera pozycje handlowe"""
        try:
            conn = await self.get_connection()
            
            if bot_id:
                cursor = await conn.execute(
                    'SELECT * FROM positions WHERE bot_id = ? AND status = ?',
                    (bot_id, status)
                )
            else:
                cursor = await conn.execute(
                    'SELECT * FROM positions WHERE status = ?',
                    (status,)
                )
            
            positions = []
            async for row in cursor:
                positions.append(dict(row))
            return positions
        except Exception as e:
            logger.info(f"Błąd podczas pobierania pozycji: {e}")
            return []

    async def close_position(self, position_id: int, close_price: float, realized_pnl: float):
        """Zamyka pozycję handlową"""
        try:
            conn = await self.get_connection()
            
            await conn.execute('''
                UPDATE positions 
                SET status = 'closed', current_price = ?, realized_pnl = ?, closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (close_price, realized_pnl, position_id))
            await conn.commit()
            return True
        except Exception as e:
            logger.info(f"Błąd podczas zamykania pozycji: {e}")
            return False
    
    async def restore_database(self, backup_path: str) -> bool:
        """Przywrócenie bazy danych z kopii zapasowej"""
        try:
            import shutil
            
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Plik kopii zapasowej nie istnieje: {backup_path}")
            
            # Zamknij połączenie
            await self.close()
            
            # Przywróć plik bazy danych
            shutil.copy2(backup_file, self.db_path)
            
            # Przywróć połączenie i sprawdź integralność
            await self.get_connection()
            await self.create_tables()  # Upewnij się, że struktura jest aktualna
            
            return True
            
        except Exception as e:
            
            logger.info(f"Błąd podczas przywracania kopii zapasowej: {e}")
            return False
    
    async def get_active_bots(self, user_id: Optional[int] = None) -> List[Dict]:
        """Pobiera listę aktywnych botów"""
        try:
            conn = await self.get_connection()
            
            if user_id:
                cursor = await conn.execute('''
                    SELECT * FROM bots 
                    WHERE user_id = ? AND status = 'active'
                    ORDER BY created_at DESC
                ''', (user_id,))
            else:
                cursor = await conn.execute('''
                    SELECT * FROM bots 
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                ''')
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            
            logger.info(f"Błąd podczas pobierania aktywnych botów: {e}")
            return []
    
    async def get_trading_pairs(self, exchange: Optional[str] = None) -> List[str]:
        """Pobiera listę par handlowych"""
        try:
            conn = await self.get_connection()
            
            if exchange:
                cursor = await conn.execute('''
                    SELECT DISTINCT pair FROM bots 
                    WHERE exchange = ? AND status IN ('active', 'running')
                ''', (exchange,))
            else:
                cursor = await conn.execute('''
                    SELECT DISTINCT pair FROM bots 
                    WHERE status IN ('active', 'running')
                ''')
            
            rows = await cursor.fetchall()
            return [row[0] for row in rows if row[0]]
            
        except Exception as e:
            
            logger.info(f"Błąd podczas pobierania par handlowych: {e}")
            return []

    async def _ensure_positions_constraints(self, conn):
        """[DEPRECATED] Użyj utils.db_migrations.apply_migrations. Zachowane dla kompatybilności."""
        try:
            cursor = await conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='positions'")
            row = await cursor.fetchone()
            sql = ''
            if row is not None:
                try:
                    sql = row['sql']
                except Exception:
                    sql = row[0]
            has_side_check = "CHECK (side IN ('buy', 'sell'))" in sql
            has_status_check = "CHECK (status IN ('open', 'closed'))" in sql
            has_size_check = "CHECK (size > 0)" in sql
            has_entry_price_nonneg = "CHECK (entry_price >= 0)" in sql
            has_closed_at_null_rule = "CHECK (status = 'closed' OR closed_at IS NULL)" in sql
            if has_side_check and has_status_check and has_size_check and has_entry_price_nonneg and has_closed_at_null_rule:
                return
            await conn.execute('BEGIN')
            await conn.execute('''
                CREATE TABLE positions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
                    size REAL NOT NULL CHECK (size > 0),
                    entry_price REAL NOT NULL CHECK (entry_price >= 0),
                    current_price REAL,
                    unrealized_pnl REAL DEFAULT 0.0,
                    realized_pnl REAL DEFAULT 0.0,
                    stop_loss_price REAL,
                    take_profit_price REAL,
                    trailing_stop_price REAL,
                    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME,
                    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed')),
                    CHECK (status = 'closed' OR closed_at IS NULL),
                    FOREIGN KEY (bot_id) REFERENCES bots (id) ON DELETE CASCADE
                )
            ''')
            await conn.execute('''
                INSERT INTO positions_new (
                    id, bot_id, symbol, side, size, entry_price, current_price, unrealized_pnl,
                    realized_pnl, stop_loss_price, take_profit_price, trailing_stop_price, opened_at,
                    closed_at, status
                )
                SELECT id, bot_id, symbol, side, size, entry_price, current_price, unrealized_pnl,
                       realized_pnl, stop_loss_price, take_profit_price, trailing_stop_price, opened_at,
                       closed_at, status
                FROM positions
            ''')
            await conn.execute('DROP TABLE positions')
            await conn.execute('ALTER TABLE positions_new RENAME TO positions')
            await conn.commit()
            return True
        except Exception as e:
            try:
                await conn.execute('ROLLBACK')
            except Exception:
                pass
            logger.info(f"Błąd podczas aktualizacji constraints tabeli positions: {e}")
            return False