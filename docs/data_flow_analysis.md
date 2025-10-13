# Analiza Przepływu Danych - CryptoBotDesktop

## Przegląd Architektury

Aplikacja CryptoBotDesktop wykorzystuje wielowarstwową architekturę z centralnym systemem zarządzania danymi:

```
┌─────────────────────────────────────────────────────────────┐
│                    ŹRÓDŁA DANYCH                            │
├─────────────────────────────────────────────────────────────┤
│ • API Giełd (Binance, Bybit, KuCoin, Coinbase)            │
│ • Baza Danych SQLite (crypto_bot.db)                       │
│ • Pliki Konfiguracyjne (JSON)                             │
│ • Dane Demo/Symulacyjne                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 WARSTWA ZARZĄDZANIA DANYMI                  │
├─────────────────────────────────────────────────────────────┤
│ • DataManager (core/data_manager.py)                       │
│ • ProductionDataManager (app/production_data_manager.py)   │
│ • DatabaseManager (app/database.py)                        │
│ • ConfigManager (utils/config_manager.py)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 WARSTWA LOGIKI BIZNESOWEJ                   │
├─────────────────────────────────────────────────────────────┤
│ • BotManager (app/bot_manager.py)                          │
│ • TradingModeManager (app/trading_mode_manager.py)         │
│ • RiskManager (app/risk_manager.py)                        │
│ • NotificationManager (app/notification_manager.py)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WARSTWA PREZENTACJI                      │
├─────────────────────────────────────────────────────────────┤
│ • MainWindow (ui/main_window.py)                           │
│ • Widgety UI (portfolio, bot_management, logs, etc.)      │
└─────────────────────────────────────────────────────────────┘
```

## Szczegółowy Przepływ Danych

### 1. Inicjalizacja Aplikacji

**Plik:** `app/main.py`

```python
# Sekwencja inicjalizacji:
1. DatabaseManager → Inicjalizacja bazy danych
2. EncryptionManager → Szyfrowanie danych wrażliwych
3. NotificationManager → System powiadomień
4. RiskManager → Zarządzanie ryzykiem
5. TradingModeManager → Tryby handlowe
6. ProductionDataManager → Dane produkcyjne (jeśli włączone)
7. MainWindow → Główny interfejs
```

### 2. Źródła Danych

#### A. API Giełd (ProductionDataManager)
- **Lokalizacja:** `app/production_data_manager.py`
- **Obsługiwane giełdy:** Binance, Bybit, KuCoin, Coinbase
- **Dane:** Ceny, OHLCV, salda, transakcje
- **Cache:** 30 sekund TTL

#### B. Baza Danych SQLite
- **Lokalizacja:** `data/crypto_bot.db`
- **Tabele:** portfolio, bots, trades, logs, alerts, risk_metrics
- **Manager:** `app/database.py`

#### C. Dane Demo/Symulacyjne
- **Lokalizacja:** `core/data_manager.py`
- **Użycie:** Gdy tryb produkcyjny wyłączony lub brak API

### 3. Centralny DataManager

**Plik:** `core/data_manager.py`

**Główne funkcje:**
- `get_portfolio_data()` → PortfolioData
- `get_bots_data()` → List[BotData]
- `get_trades_data()` → List[TradeData]
- `get_logs()` → List[LogEntry]
- `get_alerts()` → List[AlertEntry]
- `get_risk_metrics()` → RiskMetrics

**Cache System:**
- Timeout: 5 minut
- Automatyczne odświeżanie
- Fallback na dane demo

## Widgety i Zakładki

### 1. Dashboard (Główny widok)
**Lokalizacja:** `ui/main_window.py` (metoda `setup_dashboard`)

**Komponenty:**
- **PortfolioCard:** Wartość portfela, dzienny P&L
- **ActiveBotsCard:** Liczba aktywnych botów
- **TradesTable:** Ostatnie transakcje
- **BotsLayout:** Karty statusu botów

**Źródła danych:**
```python
# Portfolio Card
portfolio_data = data_manager.get_portfolio_data()
# → total_value, daily_change, daily_change_percent

# Active Bots Card  
bots_data = data_manager.get_bots_data()
# → count, running_count

# Trades Table
trades_data = data_manager.get_trades_data(limit=10)
# → time, bot, pair, side, amount, price

# Bots Layout
bots_data = data_manager.get_bots_data()
# → BotStatusWidget dla każdego bota
```

### 2. Portfolio Widget
**Lokalizacja:** `ui/portfolio.py`

**Komponenty:**
- **PortfolioStatsWidget:** Statystyki portfela
- **TransactionHistoryWidget:** Historia transakcji
- **Balance Cards:** Karty sald dla różnych walut

**Źródła danych:**
```python
# Portfolio Stats
portfolio_data = data_manager.get_portfolio_data()
# → total_value, profit_loss, available_balance, invested_balance

# Transaction History
transactions = data_manager.get_trades_data()
# → Lista wszystkich transakcji

# Balance Cards
balances = production_manager.get_real_balances() if production_mode
# → Salda z API giełd lub dane demo
```

### 3. Bot Management Widget
**Lokalizacja:** `ui/bot_management.py`

**Komponenty:**
- **BotCard:** Karty poszczególnych botów
- **BotConfigWidget:** Konfiguracja nowych botów
- **FlowLayout:** Responsywny układ kart

**Źródła danych:**
```python
# Bot Cards
bots_data = data_manager.get_bots_data()
# → id, name, status, strategy, profit, trades_count

# Real-time updates
bot_manager.get_bot_statistics(bot_id)
# → Aktualne statystyki z BotManager
```

### 4. Logs Widget
**Lokalizacja:** `ui/logs.py`

**Komponenty:**
- **LogTableWidget:** Tabela logów
- **LogFilterWidget:** Filtry logów
- **AlertsWidget:** Alerty i powiadomienia

**Źródła danych:**
```python
# Logs Table
logs = data_manager.get_logs(limit=1000, level=filter_level)
# → timestamp, level, type, bot_id, message

# Alerts
alerts = data_manager.get_alerts(limit=100, unread_only=False)
# → timestamp, title, message, severity, is_read
```

### 5. Analysis Widget
**Lokalizacja:** `ui/analysis.py`

**Komponenty:**
- **BotAnalysisWidget:** Analiza wydajności botów
- **Charts:** Wykresy P&L, drawdown

**Źródła danych:**
```python
# Bot Analysis
bot_stats = data_manager.get_bot_statistics(bot_id)
# → profit_history, trade_history, performance_metrics

# Trading Manager
trading_data = trading_manager.get_analysis_data()
# → Dane z TradingModeManager
```

### 6. Settings Widget
**Lokalizacja:** `ui/settings.py`

**Komponenty:**
- **ExchangeConfigWidget:** Konfiguracja giełd
- **NotificationConfigWidget:** Ustawienia powiadomień
- **RiskManagementWidget:** Parametry ryzyka
- **GeneralSettingsWidget:** Ogólne ustawienia

**Źródła danych:**
```python
# Config Manager
config = config_manager.get_all_settings()
# → Wszystkie ustawienia aplikacji

# API Config
api_config = api_config_manager.get_exchange_config(exchange)
# → Klucze API, ustawienia giełd
```

### 7. Risk Management View
**Lokalizacja:** `ui/main_window.py` (metoda `setup_risk_management_view`)

**Komponenty:**
- **Risk Metrics Cards:** VaR, Sharpe Ratio, Max Drawdown
- **Risk Settings Forms:** Limity ryzyka
- **Emergency Controls:** Przyciski awaryjne

**Źródła danych:**
```python
# Risk Metrics
risk_data = data_manager.get_risk_metrics()
# → current_drawdown, max_drawdown, var_1day, sharpe_ratio

# Risk Manager
risk_settings = risk_manager.get_current_settings()
# → Aktualne limity i ustawienia ryzyka
```

### 8. Notifications View
**Lokalizacja:** `ui/main_window.py` (metoda `setup_notifications_view`)

**Komponenty:**
- **Notifications List:** Lista powiadomień
- **Filter Controls:** Filtry powiadomień

**Źródła danych:**
```python
# Notifications
alerts = data_manager.get_alerts()
# → Lista wszystkich alertów i powiadomień

# Notification Manager
notification_stats = notification_manager.get_statistics()
# → Statystyki powiadomień
```

## System Odświeżania Danych

### Timery Odświeżania

**MainWindow:**
```python
# Główny timer odświeżania (co 5 sekund)
self.refresh_timer.timeout.connect(self.refresh_data)

# Metody odświeżania:
- update_portfolio_data()    # Portfolio Card
- update_bots_data()         # Bots Layout  
- update_recent_trades()     # Trades Table
- update_pnl_cards()         # P&L Cards
```

**PortfolioWidget:**
```python
# Timer portfela (co 10 sekund)
self.refresh_timer.timeout.connect(self.refresh_data)
```

**BotManagementWidget:**
```python
# Timer statusu botów (co 5 sekund)
self.status_timer.timeout.connect(self.update_bots_status)

# Timer statystyk (co 3 sekundy)  
self.stats_timer.timeout.connect(self.update_bot_statistics)
```

## Zarządzanie Stanem Widgetów

### Problem Duplikacji Instancji (NAPRAWIONY)

**Przed naprawą:**
```python
# Każde wywołanie tworzyło nową instancję
def setup_portfolio_view(self):
    self.portfolio_widget = PortfolioWidget()  # BŁĄD!
```

**Po naprawie:**
```python
# Jedna instancja na cały cykl życia aplikacji
def setup_portfolio_view(self):
    if self.portfolio_widget is None:
        self.portfolio_widget = PortfolioWidget()
    self.content_layout.addWidget(self.portfolio_widget)
```

### Zachowanie Stanu przy Zmianie Zakładek

**clear_content_layout():**
```python
# Zachowuje referencje do głównych widgetów
preserved_widgets = [
    self.bot_management_widget,
    self.portfolio_widget, 
    self.logs_widget,
    self.notifications_widget,
    self.risk_management_widget,
    self.analysis_widget,
    self.settings_widget
]

# Usuwa tylko z layoutu, nie niszczy obiektów
for widget in preserved_widgets:
    if widget:
        widget.setParent(None)
```

## Tryby Danych

### 1. Tryb Demo (Domyślny)
- Dane symulacyjne z `DataManager`
- Brak połączeń z API giełd
- Bezpieczne testowanie

### 2. Tryb Produkcyjny
- Włączany przez `production_mode = True`
- Dane z `ProductionDataManager`
- Rzeczywiste API giełd
- Cache 30 sekund

### 3. Tryb Mieszany
- Fallback na dane demo przy błędach API
- Automatyczne przełączanie
- Logowanie błędów

## Bezpieczeństwo Danych

### Szyfrowanie
- **EncryptionManager:** Szyfrowanie kluczy API
- **Secure Storage:** Bezpieczne przechowywanie wrażliwych danych

### Walidacja
- **ValidationHelper:** Walidacja wszystkich danych wejściowych
- **Type Checking:** Sprawdzanie typów danych
- **Sanitization:** Oczyszczanie danych

## Wydajność

### Cache System
- **DataManager:** Cache 5 minut
- **ProductionDataManager:** Cache 30 sekund
- **Automatic Cleanup:** Automatyczne czyszczenie

### Asynchroniczne Operacje
- **Async/Await:** Nieblokujące operacje API
- **Threading:** Operacje w tle
- **Queue System:** Kolejkowanie żądań

## Monitoring i Diagnostyka

### Logging
- **Structured Logging:** Ustrukturyzowane logi
- **Log Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation:** Rotacja plików logów

### Metryki
- **Performance Metrics:** Metryki wydajności
- **Error Tracking:** Śledzenie błędów
- **Usage Statistics:** Statystyki użycia

---

**Ostatnia aktualizacja:** 2024-01-25
**Wersja dokumentu:** 1.0
**Status:** Kompletna analiza przepływu danych