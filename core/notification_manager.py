"""
Notification Manager - Wrapper dla kompatybilności

Ten plik zapewnia kompatybilność importów dla NotificationManager
"""

# Import z właściwego modułu
from app.notifications import (
    NotificationManager,
    NotificationType,
    NotificationChannel,
    NotificationPriority,
    NotificationTemplate,
    NotificationConfig,
    NotificationHistory,
    NotificationStats
)

# Re-export wszystkich klas dla kompatybilności
__all__ = [
    'NotificationManager',
    'NotificationType',
    'NotificationChannel', 
    'NotificationPriority',
    'NotificationTemplate',
    'NotificationConfig',
    'NotificationHistory',
    'NotificationStats'
]