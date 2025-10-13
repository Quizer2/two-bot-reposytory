# AI Trading Strategy - Dokumentacja

## Przegląd

AI Trading Strategy to zaawansowany system handlowy wykorzystujący sztuczną inteligencję do automatycznego podejmowania decyzji handlowych. System łączy w sobie uczenie maszynowe, analizę techniczną i zarządzanie ryzykiem.

## Główne Funkcje

### 🧠 Sztuczna Inteligencja
- **Uczenie ze wzmocnieniem** - Bot uczy się na podstawie wyników swoich transakcji
- **Modele ensemble** - Kombinacja wielu modeli ML dla lepszej dokładności
- **Feature engineering** - Automatyczne tworzenie cech dla modeli
- **Analiza sentymentu** - Opcjonalna analiza nastrojów rynkowych

### 📊 Analiza Rynku
- Analiza techniczna z wykorzystaniem wskaźników
- Predykcja cen za pomocą modeli ML
- Ocena volatilności i trendów
- Analiza wolumenu i momentum

### 🎯 Zarządzanie Strategiami
- **Dynamiczne przełączanie strategii** - Automatyczny wybór najlepszej strategii
- **Optymalizacja budżetu** - Inteligentny podział kapitału
- **Ocena wydajności** - Ciągła ewaluacja strategii
- **Adaptacja do warunków rynkowych**

### ⚡ Dostępne Strategie
- **DCA (Dollar Cost Averaging)** - Systematyczne inwestowanie
- **Grid Trading** - Handel w siatce cenowej
- **Scalping** - Szybkie transakcje krótkoterminowe

## Konfiguracja

### Podstawowe Parametry

```python
parameters = {
    'pair': 'BTC/USD',              # Para handlowa
    'budget': 1000.0,               # Budżet do handlu
    'target_hourly_profit': 2.0,    # Cel zysku na godzinę
    'initial_balance': 1000.0,      # Początkowy balans
    'risk_percentage': 2.0,         # Procent ryzyka na transakcję
    'max_positions': 3,             # Maksymalna liczba pozycji
}
```

### Parametry AI

```python
ai_parameters = {
    'learning_rate': 0.001,                    # Tempo uczenia
    'model_update_frequency': 100,             # Częstotliwość aktualizacji modelu
    'use_reinforcement_learning': True,        # Uczenie ze wzmocnieniem
    'feature_engineering_enabled': True,       # Inżynieria cech
    'sentiment_analysis_enabled': False,       # Analiza sentymentu
    'ensemble_models': True,                   # Modele ensemble
}
```

## Użycie

### Tworzenie Instancji

```python
from app.strategy.ai_trading_bot import AITradingBot
from app.exchange.kraken import KrakenExchange

# Konfiguracja giełdy
exchange = KrakenExchange(
    api_key="your_api_key",
    api_secret="your_api_secret",
    testnet=True
)

# Parametry bota
parameters = {
    'pair': 'BTC/USD',
    'budget': 1000.0,
    'target_hourly_profit': 2.0,
    'learning_rate': 0.001,
    'use_reinforcement_learning': True,
    'feature_engineering_enabled': True,
    'ensemble_models': True
}

# Tworzenie AI Trading Bot
ai_bot = AITradingBot(
    exchange=exchange,
    parameters=parameters
)
```

### Inicjalizacja i Uruchomienie

```python
# Inicjalizacja
await ai_bot.initialize()

# Uruchomienie
await ai_bot.start()

# Sprawdzenie statusu
status = ai_bot.get_status()
print(f"Status: {status}")

# Statystyki
stats = ai_bot.get_statistics()
print(f"Statystyki: {stats}")
```

## Kompatybilne Giełdy

### ✅ Wspierane Giełdy
AI Trading Bot jest w pełni kompatybilny ze wszystkimi giełdami dostępnymi w aplikacji:

- **Binance** - Pełna integracja ✅
- **Bybit** - Pełna integracja ✅
- **KuCoin** - Pełna integracja ✅
- **Coinbase** - Pełna integracja ✅
- **Kraken** - Pełna integracja ✅
- **Bitfinex** - Pełna integracja ✅

### Konfiguracja Giełd

#### Binance
```python
from app.exchange.binance import BinanceExchange

binance = BinanceExchange(
    api_key="your_binance_api_key",
    api_secret="your_binance_api_secret",
    testnet=True  # Dla testów
)
```

#### Bybit
```python
from app.exchange.bybit import BybitExchange

bybit = BybitExchange(
    api_key="your_bybit_api_key",
    api_secret="your_bybit_api_secret",
    testnet=True  # Dla testów
)
```

#### KuCoin
```python
from app.exchange.kucoin import KuCoinExchange

kucoin = KuCoinExchange(
    api_key="your_kucoin_api_key",
    api_secret="your_kucoin_api_secret",
    passphrase="your_kucoin_passphrase",
    testnet=True  # Dla testów
)
```

#### Coinbase
```python
from app.exchange.coinbase import CoinbaseExchange

coinbase = CoinbaseExchange(
    api_key="your_coinbase_api_key",
    api_secret="your_coinbase_api_secret",
    testnet=True  # Dla testów
)
```

#### Kraken
```python
from app.exchange.kraken import KrakenExchange

kraken = KrakenExchange(
    api_key="your_kraken_api_key",
    api_secret="your_kraken_api_secret",
    testnet=True  # Dla testów
)
```

#### Bitfinex
```python
from app.exchange.bitfinex import BitfinexExchange

bitfinex = BitfinexExchange(
    api_key="your_bitfinex_api_key",
    api_secret="your_bitfinex_api_secret",
    testnet=True  # Dla testów
)
```

## Architektura

### Komponenty Systemu

```
AITradingBot
├── MarketAnalyzer          # Analiza rynku
├── StrategyManager         # Zarządzanie strategiami
├── RiskManager            # Zarządzanie ryzykiem
├── NotificationManager    # Powiadomienia
├── MLPredictor           # Predykcje ML
└── PerformanceTracker    # Śledzenie wydajności
```

### Przepływ Działania

1. **Analiza Rynku** - Zbieranie i analiza danych rynkowych
2. **Predykcja ML** - Generowanie predykcji cenowych
3. **Wybór Strategii** - Automatyczny wybór najlepszej strategii
4. **Zarządzanie Ryzykiem** - Ocena i kontrola ryzyka
5. **Wykonanie Transakcji** - Realizacja zleceń
6. **Uczenie** - Aktualizacja modeli na podstawie wyników
7. **Raportowanie** - Generowanie raportów i powiadomień

## Monitorowanie i Statystyki

### Dostępne Metryki

```python
statistics = ai_bot.get_statistics()

# Przykładowe statystyki:
{
    'total_pnl': 150.50,           # Całkowity P&L
    'total_trades': 45,            # Liczba transakcji
    'successful_trades': 32,       # Udane transakcje
    'win_rate': 71.11,            # Wskaźnik wygranych (%)
    'current_profit': 25.30,      # Aktualny zysk
    'active_strategies': 2,        # Aktywne strategie
    'model_accuracy': 0.78,       # Dokładność modelu
    'last_update': '2024-01-15 14:30:00'
}
```

### Status Bota

```python
status = ai_bot.get_status()

# Przykładowy status:
{
    'running': True,
    'current_strategy': 'dca',
    'market_condition': 'bullish',
    'risk_level': 'medium',
    'last_trade': '2024-01-15 14:25:00',
    'next_analysis': '2024-01-15 14:35:00'
}
```

## Bezpieczeństwo

### Zarządzanie Ryzykiem
- **Stop Loss** - Automatyczne zatrzymywanie strat
- **Take Profit** - Realizacja zysków
- **Position Sizing** - Kontrola wielkości pozycji
- **Daily Loss Limit** - Dzienny limit strat

### Zabezpieczenia
- **API Key Encryption** - Szyfrowanie kluczy API
- **Secure Storage** - Bezpieczne przechowywanie danych
- **Rate Limiting** - Ograniczenie częstotliwości zapytań
- **Error Handling** - Obsługa błędów i wyjątków

## Rozwiązywanie Problemów

### Częste Problemy

#### 1. Błąd inicjalizacji
```
TypeError: AITradingBot.__init__() missing required arguments
```
**Rozwiązanie**: Upewnij się, że przekazujesz parametry w słowniku `parameters`

#### 2. Błąd API
```
APIError: Invalid API credentials
```
**Rozwiązanie**: Sprawdź poprawność kluczy API i czy są aktywne

#### 3. Błąd modelu ML
```
ModelError: Insufficient training data
```
**Rozwiązanie**: Poczekaj na zebranie większej ilości danych historycznych

### Logi i Debugowanie

```python
# Włączenie szczegółowych logów
import logging
logging.getLogger('AITradingBot').setLevel(logging.DEBUG)

# Sprawdzenie logów
ai_bot.logger.info("Sprawdzanie statusu bota")
```

## Przykłady Użycia

### Przykład 1: Podstawowa Konfiguracja

```python
# Prosta konfiguracja dla początkujących
parameters = {
    'pair': 'BTC/USD',
    'budget': 500.0,
    'target_hourly_profit': 1.0,
    'risk_percentage': 1.0,
    'max_positions': 2,
    'learning_rate': 0.001,
    'use_reinforcement_learning': False,
    'ensemble_models': False
}
```

### Przykład 2: Zaawansowana Konfiguracja

```python
# Zaawansowana konfiguracja dla doświadczonych użytkowników
parameters = {
    'pair': 'ETH/USD',
    'budget': 5000.0,
    'target_hourly_profit': 10.0,
    'risk_percentage': 3.0,
    'max_positions': 5,
    'learning_rate': 0.0005,
    'model_update_frequency': 50,
    'use_reinforcement_learning': True,
    'feature_engineering_enabled': True,
    'sentiment_analysis_enabled': True,
    'ensemble_models': True
}
```

## Aktualizacje i Rozwój

### Planowane Funkcje
- [ ] Integracja z więcej giełdami
- [ ] Zaawansowana analiza sentymentu
- [ ] Backtesting historyczny
- [ ] API dla zewnętrznych aplikacji
- [ ] Mobile app integration

### Historia Wersji
- **v1.0.0** - Podstawowa funkcjonalność AI Trading
- **v1.1.0** - Integracja z Kraken i Bitfinex
- **v1.2.0** - Uczenie ze wzmocnieniem
- **v1.3.0** - Modele ensemble

## Wsparcie

Jeśli masz pytania lub problemy z AI Trading Strategy:

1. Sprawdź sekcję "Rozwiązywanie Problemów"
2. Przejrzyj logi aplikacji
3. Skontaktuj się z zespołem wsparcia

---

*Dokumentacja AI Trading Strategy - Ostatnia aktualizacja: 2024-01-15*