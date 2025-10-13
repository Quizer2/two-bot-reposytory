"""
Notification Manager - Zaawansowany system powiadomień
"""

import asyncio
import smtplib
import json
import ssl
import aiohttp
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass, field
from enum import Enum
import os
import hashlib
import base64

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from utils.logger import get_logger
from core.database_manager import DatabaseManager
from utils.encryption import EncryptionManager


class NotificationType(Enum):
    """Typy powiadomień"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    CRITICAL = "critical"
    TRADE = "trade"
    PROFIT = "profit"
    LOSS = "loss"
    SYSTEM = "system"


class NotificationChannel(Enum):
    """Kanały powiadomień"""
    DESKTOP = "desktop"
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationPriority(Enum):
    """Priorytety powiadomień"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationTemplate:
    """Szablon powiadomienia"""
    name: str
    title: str
    message: str
    notification_type: NotificationType
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    variables: Dict[str, str] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Konfiguracja kanału powiadomień"""
    channel: NotificationChannel
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None  # max notifications per minute
    retry_attempts: int = 3
    retry_delay: int = 5  # seconds


@dataclass
class NotificationHistory:
    """Historia powiadomienia"""
    id: str
    timestamp: datetime
    title: str
    message: str
    notification_type: NotificationType
    channels: List[NotificationChannel]
    priority: NotificationPriority
    status: str  # sent, failed, pending
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationStats:
    """Statystyki powiadomień"""
    total_sent: int = 0
    total_failed: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_channel: Dict[str, int] = field(default_factory=dict)
    last_24h: int = 0
    last_hour: int = 0


class NotificationManager:
    """Zaawansowany manager powiadomień"""
    
    def __init__(self, database_manager: DatabaseManager, 
                 encryption_manager: EncryptionManager):
        self.logger = get_logger("NotificationManager")
        self.db = database_manager
        self.encryption = encryption_manager
        
        # Konfiguracje kanałów
        self.channel_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Szablony powiadomień
        self.templates: Dict[str, NotificationTemplate] = {}
        
        # Historia powiadomień
        self.history: List[NotificationHistory] = []
        
        # Statystyki
        self.stats = NotificationStats()
        
        # Rate limiting
        self.rate_limits: Dict[NotificationChannel, List[datetime]] = {}
        
        # Kolejka powiadomień
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        
        # Flagi kontrolne
        self.is_running = False
        self.worker_task: Optional[asyncio.Task] = None
        
        # Session dla HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Inicjalizacja managera"""
        try:
            self.logger.info("Inicjalizacja NotificationManager...")
            
            # Utworzenie session HTTP
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Ładowanie konfiguracji z bazy danych
            await self.load_configurations()
            
            # Ładowanie szablonów
            await self.load_templates()
            
            # Ładowanie historii
            await self.load_history()
            
            # Ładowanie statystyk
            await self.load_statistics()
            
            self.logger.info("NotificationManager zainicjalizowany pomyślnie")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas inicjalizacji NotificationManager: {e}")
            raise
    
    async def start(self):
        """Uruchomienie managera"""
        try:
            if self.is_running:
                return
                
            self.is_running = True
            
            # Uruchomienie worker'a do przetwarzania kolejki
            self.worker_task = asyncio.create_task(self._notification_worker())
            
            self.logger.info("NotificationManager uruchomiony")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas uruchamiania NotificationManager: {e}")
            raise
    
    async def stop(self):
        """Zatrzymanie managera"""
        try:
            self.is_running = False
            
            # Zatrzymanie worker'a
            if self.worker_task:
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
            
            # Zamknięcie session HTTP
            if self.session:
                await self.session.close()
            
            # Zapisanie statystyk
            await self.save_statistics()
            
            self.logger.info("NotificationManager zatrzymany")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania NotificationManager: {e}")
    
    async def send_notification(self, title: str, message: str, 
                              notification_type: NotificationType = NotificationType.INFO,
                              channels: Optional[List[NotificationChannel]] = None,
                              priority: NotificationPriority = NotificationPriority.NORMAL,
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """Wysłanie powiadomienia"""
        try:
            # Generowanie ID powiadomienia
            notification_id = self._generate_notification_id(title, message)
            
            # Domyślne kanały
            if channels is None:
                channels = [NotificationChannel.DESKTOP]
            
            # Filtrowanie aktywnych kanałów
            active_channels = [
                ch for ch in channels 
                if ch in self.channel_configs and self.channel_configs[ch].enabled
            ]
            
            if not active_channels:
                self.logger.warning("Brak aktywnych kanałów powiadomień")
                return notification_id
            
            # Sprawdzenie rate limiting
            allowed_channels = []
            for channel in active_channels:
                if await self._check_rate_limit(channel):
                    allowed_channels.append(channel)
                else:
                    self.logger.warning(f"Rate limit przekroczony dla kanału {channel.value}")
            
            if not allowed_channels:
                self.logger.warning("Wszystkie kanały przekroczyły rate limit")
                return notification_id
            
            # Utworzenie obiektu powiadomienia
            notification = {
                'id': notification_id,
                'title': title,
                'message': message,
                'type': notification_type,
                'channels': allowed_channels,
                'priority': priority,
                'metadata': metadata or {},
                'timestamp': datetime.now()
            }
            
            # Dodanie do kolejki
            await self.notification_queue.put(notification)
            
            self.logger.info(f"Powiadomienie dodane do kolejki: {notification_id}")
            return notification_id
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wysyłania powiadomienia: {e}")
            return ""
    
    async def send_from_template(self, template_name: str, 
                               variables: Optional[Dict[str, str]] = None,
                               override_channels: Optional[List[NotificationChannel]] = None) -> str:
        """Wysłanie powiadomienia z szablonu"""
        try:
            if template_name not in self.templates:
                raise ValueError(f"Szablon '{template_name}' nie istnieje")
            
            template = self.templates[template_name]
            
            # Zastąpienie zmiennych
            title = template.title
            message = template.message
            
            if variables:
                for var, value in variables.items():
                    title = title.replace(f"{{{var}}}", str(value))
                    message = message.replace(f"{{{var}}}", str(value))
            
            # Kanały
            channels = override_channels or template.channels
            
            return await self.send_notification(
                title=title,
                message=message,
                notification_type=template.notification_type,
                channels=channels,
                priority=template.priority
            )
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wysyłania z szablonu: {e}")
            return ""
    
    async def _notification_worker(self):
        """Worker do przetwarzania kolejki powiadomień"""
        while self.is_running:
            try:
                # Pobranie powiadomienia z kolejki
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=1.0
                )
                
                # Przetworzenie powiadomienia
                await self._process_notification(notification)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Błąd w worker'ze powiadomień: {e}")
    
    async def _process_notification(self, notification: Dict[str, Any]):
        """Przetwarzanie pojedynczego powiadomienia"""
        try:
            notification_id = notification['id']
            title = notification['title']
            message = notification['message']
            notification_type = notification['type']
            channels = notification['channels']
            priority = notification['priority']
            metadata = notification['metadata']
            timestamp = notification['timestamp']
            
            # Wysłanie przez wszystkie kanały
            results = {}
            
            for channel in channels:
                try:
                    if channel == NotificationChannel.DESKTOP:
                        await self._send_desktop_notification(title, message, notification_type)
                    elif channel == NotificationChannel.EMAIL:
                        await self._send_email_notification(title, message, notification_type, metadata)
                    elif channel == NotificationChannel.TELEGRAM:
                        await self._send_telegram_notification(title, message, notification_type, metadata)
                    elif channel == NotificationChannel.DISCORD:
                        await self._send_discord_notification(title, message, notification_type, metadata)
                    elif channel == NotificationChannel.WEBHOOK:
                        await self._send_webhook_notification(title, message, notification_type, metadata)
                    
                    results[channel.value] = "success"
                    
                except Exception as e:
                    self.logger.error(f"Błąd wysyłania przez {channel.value}: {e}")
                    results[channel.value] = f"error: {str(e)}"
            
            # Zapisanie do historii
            history_entry = NotificationHistory(
                id=notification_id,
                timestamp=timestamp,
                title=title,
                message=message,
                notification_type=notification_type,
                channels=channels,
                priority=priority,
                status="sent" if any(r == "success" for r in results.values()) else "failed",
                metadata={**metadata, 'results': results}
            )
            
            self.history.append(history_entry)
            
            # Ograniczenie historii
            if len(self.history) > 10000:
                self.history = self.history[-5000:]
            
            # Aktualizacja statystyk
            await self._update_statistics(notification_type, channels, results)
            
            # Zapisanie do bazy danych
            await self._save_notification_to_db(history_entry)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas przetwarzania powiadomienia: {e}")
    
    async def _send_desktop_notification(self, title: str, message: str, 
                                       notification_type: NotificationType):
        """Wysłanie powiadomienia desktop"""
        try:
            if not PLYER_AVAILABLE:
                raise Exception("Plyer nie jest dostępny")
            
            # Ikony dla różnych typów
            icon_map = {
                NotificationType.INFO: None,
                NotificationType.WARNING: None,
                NotificationType.ERROR: None,
                NotificationType.SUCCESS: None,
                NotificationType.CRITICAL: None
            }
            
            # Timeout na podstawie priorytetu
            timeout_map = {
                NotificationPriority.LOW: 5,
                NotificationPriority.NORMAL: 10,
                NotificationPriority.HIGH: 15,
                NotificationPriority.URGENT: 30
            }
            
            notification.notify(
                title=title,
                message=message[:200],  # Ograniczenie długości
                timeout=timeout_map.get(NotificationPriority.NORMAL, 10),
                app_icon=icon_map.get(notification_type)
            )
            
        except Exception as e:
            raise Exception(f"Błąd powiadomienia desktop: {e}")
    
    async def _send_email_notification(self, title: str, message: str, 
                                     notification_type: NotificationType,
                                     metadata: Dict[str, Any]):
        """Wysłanie powiadomienia email"""
        try:
            config = self.channel_configs.get(NotificationChannel.EMAIL)
            if not config or not config.settings:
                raise Exception("Brak konfiguracji email")
            
            settings = config.settings
            
            # Utworzenie wiadomości
            msg = MIMEMultipart('alternative')
            msg['From'] = settings['from_email']
            msg['To'] = ', '.join(settings['to_emails'])
            msg['Subject'] = f"[{notification_type.value.upper()}] {title}"
            
            # Treść HTML
            html_body = f"""
            <html>
            <head></head>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                        <h2 style="color: #333; margin-top: 0;">CryptoBot Notification</h2>
                        <div style="background-color: white; padding: 15px; border-radius: 3px; border-left: 4px solid #007bff;">
                            <p><strong>Type:</strong> {notification_type.value.upper()}</p>
                            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                            <p><strong>Message:</strong></p>
                            <p style="background-color: #f8f9fa; padding: 10px; border-radius: 3px;">{message}</p>
                        </div>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                        <p style="color: #666; font-size: 12px;">CryptoBotDesktop - Automated Trading System</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Treść tekstowa
            text_body = f"""
CryptoBot Notification

Type: {notification_type.value.upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Message:
{message}

---
CryptoBotDesktop - Automated Trading System
            """
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Wysłanie email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(settings['smtp_server'], settings['smtp_port']) as server:
                server.starttls(context=context)
                server.login(settings['username'], settings['password'])
                server.sendmail(
                    settings['from_email'], 
                    settings['to_emails'], 
                    msg.as_string()
                )
            
        except Exception as e:
            raise Exception(f"Błąd powiadomienia email: {e}")
    
    async def _send_telegram_notification(self, title: str, message: str, 
                                        notification_type: NotificationType,
                                        metadata: Dict[str, Any]):
        """Wysłanie powiadomienia Telegram"""
        try:
            config = self.channel_configs.get(NotificationChannel.TELEGRAM)
            if not config or not config.settings:
                raise Exception("Brak konfiguracji Telegram")
            
            settings = config.settings
            bot_token = settings['bot_token']
            chat_ids = settings['chat_ids']
            
            # Emoji dla różnych typów
            emoji_map = {
                NotificationType.INFO: 'ℹ️',
                NotificationType.WARNING: '⚠️',
                NotificationType.ERROR: '❌',
                NotificationType.SUCCESS: '✅',
                NotificationType.CRITICAL: '🚨',
                NotificationType.TRADE: '💰',
                NotificationType.PROFIT: '📈',
                NotificationType.LOSS: '📉'
            }
            
            emoji = emoji_map.get(notification_type, 'ℹ️')
            
            # Formatowanie wiadomości
            formatted_message = f"""
{emoji} *{title}*

{message}

_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
            """.strip()
            
            # Wysłanie do wszystkich chat_ids
            for chat_id in chat_ids:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                
                payload = {
                    'chat_id': chat_id,
                    'text': formatted_message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                async with self.session.post(url, json=payload) as response:
                    if not response.ok:
                        error_text = await response.text()
                        raise Exception(f"Telegram API error: {error_text}")
            
        except Exception as e:
            raise Exception(f"Błąd powiadomienia Telegram: {e}")
    
    async def _send_discord_notification(self, title: str, message: str, 
                                       notification_type: NotificationType,
                                       metadata: Dict[str, Any]):
        """Wysłanie powiadomienia Discord"""
        try:
            config = self.channel_configs.get(NotificationChannel.DISCORD)
            if not config or not config.settings:
                raise Exception("Brak konfiguracji Discord")
            
            webhook_url = config.settings['webhook_url']
            
            # Kolory dla różnych typów
            color_map = {
                NotificationType.INFO: 0x3498db,
                NotificationType.WARNING: 0xf39c12,
                NotificationType.ERROR: 0xe74c3c,
                NotificationType.SUCCESS: 0x2ecc71,
                NotificationType.CRITICAL: 0x8e44ad,
                NotificationType.TRADE: 0x9b59b6,
                NotificationType.PROFIT: 0x27ae60,
                NotificationType.LOSS: 0xe55039
            }
            
            embed = {
                'title': title,
                'description': message,
                'color': color_map.get(notification_type, 0x3498db),
                'timestamp': datetime.now().isoformat(),
                'footer': {
                    'text': f'CryptoBot • {notification_type.value.upper()}'
                },
                'fields': []
            }
            
            # Dodanie metadanych jako pola
            if metadata:
                for key, value in metadata.items():
                    if key != 'results':
                        embed['fields'].append({
                            'name': key.replace('_', ' ').title(),
                            'value': str(value),
                            'inline': True
                        })
            
            payload = {
                'embeds': [embed],
                'username': 'CryptoBot'
            }
            
            async with self.session.post(webhook_url, json=payload) as response:
                if not response.ok:
                    error_text = await response.text()
                    raise Exception(f"Discord webhook error: {error_text}")
            
        except Exception as e:
            raise Exception(f"Błąd powiadomienia Discord: {e}")
    
    async def _send_webhook_notification(self, title: str, message: str, 
                                       notification_type: NotificationType,
                                       metadata: Dict[str, Any]):
        """Wysłanie powiadomienia webhook"""
        try:
            config = self.channel_configs.get(NotificationChannel.WEBHOOK)
            if not config or not config.settings:
                raise Exception("Brak konfiguracji webhook")
            
            webhook_url = config.settings['url']
            headers = config.settings.get('headers', {})
            
            payload = {
                'title': title,
                'message': message,
                'type': notification_type.value,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            async with self.session.post(
                webhook_url, 
                json=payload, 
                headers=headers
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    raise Exception(f"Webhook error: {error_text}")
            
        except Exception as e:
            raise Exception(f"Błąd powiadomienia webhook: {e}")
    
    async def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """Sprawdzenie rate limiting"""
        try:
            config = self.channel_configs.get(channel)
            if not config or not config.rate_limit:
                return True
            
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            # Inicjalizacja listy jeśli nie istnieje
            if channel not in self.rate_limits:
                self.rate_limits[channel] = []
            
            # Usunięcie starych wpisów
            self.rate_limits[channel] = [
                timestamp for timestamp in self.rate_limits[channel]
                if timestamp > minute_ago
            ]
            
            # Sprawdzenie limitu
            if len(self.rate_limits[channel]) >= config.rate_limit:
                return False
            
            # Dodanie aktualnego timestamp
            self.rate_limits[channel].append(now)
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania rate limit: {e}")
            return True
    
    def _generate_notification_id(self, title: str, message: str) -> str:
        """Generowanie ID powiadomienia"""
        content = f"{title}:{message}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def _update_statistics(self, notification_type: NotificationType, 
                               channels: List[NotificationChannel], 
                               results: Dict[str, str]):
        """Aktualizacja statystyk"""
        try:
            # Ogólne statystyki
            success_count = sum(1 for r in results.values() if r == "success")
            if success_count > 0:
                self.stats.total_sent += 1
            else:
                self.stats.total_failed += 1
            
            # Statystyki według typu
            type_key = notification_type.value
            if type_key not in self.stats.by_type:
                self.stats.by_type[type_key] = 0
            self.stats.by_type[type_key] += 1
            
            # Statystyki według kanału
            for channel in channels:
                channel_key = channel.value
                if channel_key not in self.stats.by_channel:
                    self.stats.by_channel[channel_key] = 0
                if results.get(channel_key) == "success":
                    self.stats.by_channel[channel_key] += 1
            
            # Statystyki czasowe
            self.stats.last_hour += 1
            self.stats.last_24h += 1
            
        except Exception as e:
            self.logger.error(f"Błąd aktualizacji statystyk: {e}")
    
    # Metody konfiguracji
    async def configure_channel(self, channel: NotificationChannel, 
                              settings: Dict[str, Any], enabled: bool = True):
        """Konfiguracja kanału powiadomień"""
        try:
            # Szyfrowanie wrażliwych danych
            encrypted_settings = {}
            sensitive_keys = ['password', 'bot_token', 'webhook_url', 'api_key']
            
            for key, value in settings.items():
                if key in sensitive_keys and isinstance(value, str):
                    encrypted_settings[key] = self.encryption.encrypt(value)
                else:
                    encrypted_settings[key] = value
            
            config = NotificationConfig(
                channel=channel,
                enabled=enabled,
                settings=encrypted_settings
            )
            
            self.channel_configs[channel] = config
            
            # Zapisanie do bazy danych
            await self._save_channel_config(config)
            
            self.logger.info(f"Konfiguracja kanału {channel.value} została zaktualizowana")
            
        except Exception as e:
            self.logger.error(f"Błąd konfiguracji kanału: {e}")
            raise
    
    async def add_template(self, template: NotificationTemplate):
        """Dodanie szablonu powiadomienia"""
        try:
            self.templates[template.name] = template
            await self._save_template(template)
            self.logger.info(f"Szablon '{template.name}' został dodany")
            
        except Exception as e:
            self.logger.error(f"Błąd dodawania szablonu: {e}")
            raise
    
    # Metody pomocnicze dla specjalnych powiadomień
    async def send_trade_notification(self, bot_id: int, trade_data: Dict[str, Any]) -> str:
        """Wysłanie powiadomienia o transakcji"""
        try:
            side = trade_data.get('side', 'unknown')
            pair = trade_data.get('pair', 'unknown')
            amount = trade_data.get('amount', 0)
            price = trade_data.get('price', 0)
            
            title = f"Trade Executed - Bot {bot_id}"
            message = f"{side.upper()} {amount} {pair} @ {price}"
            
            return await self.send_notification(
                title=title,
                message=message,
                notification_type=NotificationType.TRADE,
                metadata={'bot_id': bot_id, 'trade_data': trade_data}
            )
            
        except Exception as e:
            self.logger.error(f"Błąd powiadomienia o transakcji: {e}")
            return ""
    
    async def send_error_notification(self, bot_id: int, error_message: str) -> str:
        """Wysłanie powiadomienia o błędzie"""
        try:
            title = f"Bot Error - Bot {bot_id}"
            
            return await self.send_notification(
                title=title,
                message=error_message,
                notification_type=NotificationType.ERROR,
                priority=NotificationPriority.HIGH,
                metadata={'bot_id': bot_id}
            )
            
        except Exception as e:
            self.logger.error(f"Błąd powiadomienia o błędzie: {e}")
            return ""
    
    async def send_profit_loss_notification(self, bot_id: int, pnl: float, 
                                          percentage: float) -> str:
        """Wysłanie powiadomienia o zysku/stracie"""
        try:
            if pnl > 0:
                title = f"Profit Alert - Bot {bot_id}"
                message = f"PROFIT: +{pnl:.2f} ({percentage:+.2f}%)"
                notification_type = NotificationType.PROFIT
            else:
                title = f"Loss Alert - Bot {bot_id}"
                message = f"LOSS: {pnl:.2f} ({percentage:+.2f}%)"
                notification_type = NotificationType.LOSS
            
            return await self.send_notification(
                title=title,
                message=message,
                notification_type=notification_type,
                metadata={'bot_id': bot_id, 'pnl': pnl, 'percentage': percentage}
            )
            
        except Exception as e:
            self.logger.error(f"Błąd powiadomienia P&L: {e}")
            return ""
    
    # Metody zarządzania danymi
    async def get_notification_history(self, limit: int = 100, 
                                     notification_type: Optional[NotificationType] = None,
                                     channel: Optional[NotificationChannel] = None) -> List[NotificationHistory]:
        """Pobranie historii powiadomień"""
        try:
            filtered_history = self.history
            
            # Filtrowanie według typu
            if notification_type:
                filtered_history = [
                    h for h in filtered_history 
                    if h.notification_type == notification_type
                ]
            
            # Filtrowanie według kanału
            if channel:
                filtered_history = [
                    h for h in filtered_history 
                    if channel in h.channels
                ]
            
            # Sortowanie według czasu (najnowsze pierwsze)
            filtered_history.sort(key=lambda x: x.timestamp, reverse=True)
            
            return filtered_history[:limit]
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania historii: {e}")
            return []
    
    async def get_statistics(self) -> NotificationStats:
        """Pobranie statystyk"""
        return self.stats
    
    async def clear_history(self):
        """Wyczyszczenie historii"""
        try:
            self.history.clear()
            await self.db.execute_query(
                "DELETE FROM notification_history WHERE 1=1"
            )
            self.logger.info("Historia powiadomień została wyczyszczona")
            
        except Exception as e:
            self.logger.error(f"Błąd czyszczenia historii: {e}")
    
    async def test_channel(self, channel: NotificationChannel) -> bool:
        """Test kanału powiadomień"""
        try:
            test_message = f"Test powiadomienia dla kanału {channel.value}"
            
            notification_id = await self.send_notification(
                title="Test Notification",
                message=test_message,
                notification_type=NotificationType.INFO,
                channels=[channel]
            )
            
            # Czekanie na przetworzenie
            await asyncio.sleep(2)
            
            # Sprawdzenie rezultatu
            for entry in reversed(self.history):
                if entry.id == notification_id:
                    return entry.status == "sent"
            
            return False
            
        except Exception as e:
            self.logger.error(f"Błąd testu kanału {channel.value}: {e}")
            return False
    
    # Metody bazy danych
    async def load_configurations(self):
        """Ładowanie konfiguracji z bazy danych"""
        try:
            # TODO: Implementacja ładowania z bazy danych
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania konfiguracji: {e}")
    
    async def load_templates(self):
        """Ładowanie szablonów z bazy danych"""
        try:
            # TODO: Implementacja ładowania szablonów
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania szablonów: {e}")
    
    async def load_history(self):
        """Ładowanie historii z bazy danych"""
        try:
            # TODO: Implementacja ładowania historii
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania historii: {e}")
    
    async def load_statistics(self):
        """Ładowanie statystyk z bazy danych"""
        try:
            # TODO: Implementacja ładowania statystyk
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd ładowania statystyk: {e}")
    
    async def save_statistics(self):
        """Zapisanie statystyk do bazy danych"""
        try:
            # TODO: Implementacja zapisywania statystyk
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd zapisywania statystyk: {e}")
    
    async def _save_channel_config(self, config: NotificationConfig):
        """Zapisanie konfiguracji kanału do bazy danych"""
        try:
            # TODO: Implementacja zapisywania konfiguracji
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd zapisywania konfiguracji kanału: {e}")
    
    async def _save_template(self, template: NotificationTemplate):
        """Zapisanie szablonu do bazy danych"""
        try:
            # TODO: Implementacja zapisywania szablonu
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd zapisywania szablonu: {e}")
    
    async def _save_notification_to_db(self, notification: NotificationHistory):
        """Zapisanie powiadomienia do bazy danych"""
        try:
            # TODO: Implementacja zapisywania powiadomienia
            pass
            
        except Exception as e:
            self.logger.error(f"Błąd zapisywania powiadomienia: {e}")
    
    async def shutdown(self):
        """Alias dla metody stop() - zamyka NotificationManager"""
        await self.stop()
    
    # Synchroniczne wrapper'y dla kompatybilności z UI
    def get_statistics_sync(self) -> NotificationStats:
        """Synchroniczny wrapper dla get_statistics"""
        try:
            return self.stats
        except Exception as e:
            self.logger.error(f"Błąd pobierania statystyk (sync): {e}")
            return NotificationStats()
    
    def get_notification_history_sync(self, limit: int = 100, 
                                    notification_type: Optional[NotificationType] = None,
                                    channel: Optional[NotificationChannel] = None) -> List[NotificationHistory]:
        """Synchroniczny wrapper dla get_notification_history"""
        try:
            filtered_history = self.history
            
            # Filtrowanie według typu
            if notification_type:
                filtered_history = [
                    h for h in filtered_history 
                    if h.notification_type == notification_type
                ]
            
            # Filtrowanie według kanału
            if channel:
                filtered_history = [
                    h for h in filtered_history 
                    if channel in h.channels
                ]
            
            # Sortowanie według czasu (najnowsze pierwsze)
            filtered_history.sort(key=lambda x: x.timestamp, reverse=True)
            
            return filtered_history[:limit]
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania historii (sync): {e}")
            return []