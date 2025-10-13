# Raport stanu systemu – 13 października 2025

## Podsumowanie wykonawcze
- **Konfiguracja i propagacja zdarzeń**: przepływ UI → ConfigManager → EventBus działa, zmiany są zapisywane i wyzwalają powiadomienia, a RiskManager reaguje na aktualizacje konfiguracji ryzyka.
- **Luki krytyczne**: środowisko nie ma aktywnych adapterów giełdowych ani zależności WebSocket, UnifiedDataManager nie przechodzi inicjalizacji, a smoke-testy UI i silnika strategii zatrzymują się na brakujących bibliotekach.

## Testy uruchomione 13.10.2025
- `pytest -rxXs` – **86 passed / 1 skipped / 3 xfailed** (brak regresji w pakiecie jednostkowym).
- `python test_ui_config_eventbus_flow.py` – przepływ UI → ConfigManager → EventBus zaliczony w całości.
- `python test_bot_trading_api_flow.py` – 1/6 testów zaliczonych, brak adapterów giełdowych oraz błąd API place_order.
- `python tests/full_system_test.py` – smoke-test całego stosu zakończył się 5/9 kroków.

Szczegółowe logi z trzech ostatnich uruchomień są dołączone w repozytorium (`ui_config_eventbus_flow_results.json`, `bot_trading_api_flow_results.json`, `tests/full_system_report.json`).

## Synchronizacja i propagacja konfiguracji
- ConfigManager zapisuje konfiguracje (app/UI), waliduje dane i publikuje zdarzenia `config.updated`, które mogą przetwarzać inne komponenty.【F:utils/config_manager.py†L271-L358】
- EventBus zapewnia mechanizm pub/sub wykorzystywany przez ConfigManager, RiskManager i inne moduły do reagowania na zmiany.【F:utils/event_bus.py†L10-L151】
- W najnowszym przebiegu testów UI → Config → EventBus każdy scenariusz (zmiana limitów ryzyka, konfiguracji bota i motywu) zakończył się publikacją zdarzenia oraz trwałym zapisem na dysku.【F:ui_config_eventbus_flow_results.json†L1-L128】

## Zarządzanie ryzykiem
- RiskManager reaguje na zdarzenia konfiguracji, planuje ponowne wczytanie limitów dla konkretnych botów lub całego systemu i publikuje zdarzenia `risk.reloaded`.【F:app/risk_management.py†L901-L976】
- Bieżąca konfiguracja aplikacji zawiera dodatnie, realistyczne limity ryzyka zarówno na poziomie globalnym, jak i w sekcji `trading.risk_management` (zaktualizowane podczas testu UI).【F:config/app_config.json†L48-L91】
- Walidacja w ConfigManager nie odrzuca jednak ekstremalnych wartości ryzyka; w razie potrzeby należy dodać twarde ograniczenia biznesowe (obecnie testy nie wykrywają zbyt liberalnych parametrów).

## Boty, strategie i przepływy danych
- Strategy Engine udostępnia zestaw strategii (DCA, Grid, Scalping, a także integrację z adapterem AI i strategiami swing/arbitrage), korzystając z MarketDataManager i TradingEngine do generowania sygnałów.【F:core/strategy_engine.py†L1-L200】
- BotManager (nie cytowany w testach) pozostaje zależny od dostępności MarketDataManager i modułu `websocket`; brak tej biblioteki powoduje, że smoke-testy botów oraz UnifiedDataManager kończą się niepowodzeniem (`No module named 'websocket'`).【F:tests/full_system_report.json†L3-L47】【380c51†L1-L36】
- W konsekwencji przepływ Bot → TradingEngine → API → Exchange nie przechodzi (brak adapterów giełdowych, błąd sygnatury `place_order`, brak MarketDataManager).【F:bot_trading_api_flow_results.json†L1-L35】【380c51†L1-L36】

## UI i widgety statystyk
- Dashboard korzysta z widgetów StatTile i LineChart, które cyklicznie odświeżają dane z modułu `runtime_metrics` (liczby zdarzeń, zamówień, krzywe kapitału). Mechanizmy mają fallbacki dla środowisk headless, więc UI nie blokuje się przy braku bibliotek GUI.【F:ui/metrics_widgets.py†L1-L176】【F:utils/runtime_metrics.py†L1-L87】
- Brak biblioteki `libGL.so.1` w środowisku uniemożliwia import głównego okna UI (`updated_main_window`), co potwierdza smoke-test pełnego systemu.【F:tests/full_system_report.json†L33-L52】【d8bf17†L1-L37】

## Tryby handlu (live/paper) i TradingEngine
- TradingEngine działa w trybie demo (paper trading) i poprawnie generuje odpowiedzi dla zleceń rynkowych w testach smoke, jednak brak aktywnych adapterów giełdowych uniemożliwia handel live.【F:core/trading_engine.py†L70-L137】【d8bf17†L1-L37】
- Aby obsłużyć handel rzeczywisty, należy dostarczyć moduły adapterów giełdowych (`app.exchange.*`) oraz zależności `websocket`/`websockets`.

## Persistencja ustawień i restart
- Zmiany konfiguracji są zapisywane do plików JSON (`config/app_config.json`, `config/ui_config.json`) wraz ze znacznikami czasu, co weryfikuje test trwałości w scenariuszu UI → Config → EventBus.【F:config/app_config.json†L48-L91】【F:config/ui_config.json†L1-L30】【F:ui_config_eventbus_flow_results.json†L1-L29】

## Rekomendowane działania przed produkcją
1. Zainstalować brakujące zależności (`websocket`/`websockets`, biblioteki OpenGL dla PyQt) i dostarczyć adaptery giełdowe `app.exchange.*`.
2. Naprawić signaturę wywołania `TradingEngine.place_order` w testach integracyjnych (przekazywać `OrderSide` zamiast surowego stringa lub dodać wrapper).
3. Rozszerzyć walidację konfiguracji o twarde limity wartości ryzyka i spójność danych botów.
4. Uruchomić UnifiedDataManager po dostarczeniu brakujących modułów oraz powtórzyć smoke-testy pełnego systemu (`python tests/full_system_test.py`).
