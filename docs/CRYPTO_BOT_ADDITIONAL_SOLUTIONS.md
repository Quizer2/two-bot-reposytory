# CryptoBot Desktop – dodatkowe rekomendacje techniczne

Dokument rozwija analizę luk produkcyjnych i proponuje konkretne rozwiązania,
które można zaplanować w kolejnych iteracjach, aby domknąć wszystkie kluczowe
obszary funkcjonalne oraz operacyjne.

## Aktualizacja wdrożenia – październik 2025

- Zaimplementowano usługę składania zleceń live w `TradingModeManager`, która
  korzysta z `TradingEngine`, limitów ryzyka oraz rejestruje wykonane transakcje
  w module live. Dzięki temu rekomendacja 1.1 ma działającą implementację.
- Utrwalono stan strategii DCA poprzez nowe repozytoria `strategy_states` i
  `strategy_orders` w warstwie bazy danych. Strategia odtwarza ostatni zapisany
  stan i zapisuje zmiany po każdym cyklu, co zamyka punkt 1.2 planu.
- `DataManager` wykorzystuje teraz bazę aplikacyjną do synchronizacji trybu
  handlowego oraz ustawień ryzyka, a wartości są cache’owane na potrzeby UI –
  pokrywa to zadanie 1.3.
- `NotificationManager` ładuje i zapisuje konfiguracje kanałów, szablony oraz
  historię powiadomień z bazy danych, odświeża statystyki i utrzymuje dane
  domyślne, co odpowiada rekomendacji 1.4.

## 1. Blokery produkcyjne (Priorytet 0)

### 1.1 Implementacja realnego składania zleceń
- **Problem:** Metoda `place_live_order` w `TradingModeManager` kończy się
  ostrzeżeniem i nie wywołuje żadnego adaptera giełdowego, więc handel live jest
  obecnie niemożliwy.【F:app/trading_mode_manager.py†L563-L587】
- **Rozwiązanie:**
  1. Wprowadzić adapter do `ExchangeRegistry`, który mapuje bota na wybraną giełdę
     oraz konto API.
  2. Dodać asynchroniczny „order execution service”, który przyjmuje sygnały,
     waliduje limity ryzyka i wywołuje odpowiednią metodę w `BaseExchange`.
  3. Zaimplementować obsługę błędów (timeout, rate limit, błędne parametry) z
     wykorzystaniem istniejącego `net_guard` (circuit breaker + retry z jitterem).

### 1.2 Utrwalenie stanu strategii
- **Problem:** Kluczowe strategie (`DCA`, `Grid`, `Scalping`) posiadają puste
  metody `load/save/update`, co uniemożliwia wznawianie pracy po restarcie
  aplikacji.【F:app/strategy/dca.py†L439-L451】
- **Rozwiązanie:**
  1. Zdefiniować w `app/database.py` repozytorium `strategy_state_repository` z
     metodami `fetch_state`, `persist_state`, `list_orders`.
  2. Każdej strategii przypisać schemat serializacji (np. `pydantic`/dataclasses)
     i zapisywać stany po każdej zmianie (`order placed`, `order filled`).
  3. Przy starcie bota odtwarzać parametry i aktywne zlecenia, inicjalizując
     planery w oparciu o ostatni timestamp.

### 1.3 Synchronizacja ustawień ryzyka i trybu danych
- **Problem:** `DataManager` zwraca stałe wartości dla trybu handlowego oraz
  ustawień ryzyka – wszystkie metody `get/set` zawierają komentarze `TODO` i nie
  komunikują się z bazą.【F:core/data_manager.py†L1032-L1098】
- **Rozwiązanie:**
  1. Zaimplementować tabele `risk_settings` i `trading_modes` wraz z migracjami.
  2. Dodać warstwę cache z invalidacją po zapisie (korzystając z istniejących
     helperów) oraz walidacją schematów (limity per-user, dzienne straty).
  3. Rozszerzyć API UI, aby reagowało na `asyncio.Event` po zmianie ustawień i
     natychmiast odświeżało widoki.

### 1.4 Powiadomienia produkcyjne
- **Problem:** Każda metoda integracji z bazą w `NotificationManager` jest
  pusta, więc konfiguracje, szablony i historia powiadomień nie są
  utrwalane.【F:app/notifications.py†L895-L964】
- **Rozwiązanie:**
  1. Wykorzystać istniejące modele (`NotificationConfig`, `NotificationTemplate`)
     i zmapować je na tabele SQLite/PostgreSQL.
  2. Zapewnić migracje inicjalizujące domyślne szablony dla alertów krytycznych.
  3. Uzupełnić panel UI o zarządzanie kanałami (np. e-mail, webhook) – dane będą
     pobierane z repozytorium zamiast z placeholderów.

## 2. Wysoki priorytet (Priorytet 1)

### 2.1 Dashboard i widoki portfela
- **Problem:** Widżety portfela i dashboardu nadal bazują na wartościach
  domyślnych/zerowych, a część metryk ma komentarze `TODO`.【F:ui/portfolio.py†L687-L1302】
- **Rozwiązanie:**
  1. Dostarczyć endpoint w `IntegratedDataManager`, który agreguje metryki P&L
     (1d/7d/30d), wolumen transakcji oraz dzienne limity, korzystając z nowych
     danych persistowanych przez strategie.
  2. W UI wprowadzić mapowanie kolumn na rzeczywiste pola JSON, usuwając
     placeholdery i zapewniając formatowanie walut.
  3. Dodać testy integracyjne UI (np. `pytest-qt`), które symulują przyjęcie
     snapshotu z backendu i weryfikują aktualizację widżetów.

### 2.2 Masowe operacje na botach
- **Problem:** Przyciski „Start/Stop All” oraz import/eksport konfiguracji są w
  starym widoku oznaczone jako `TODO` i nie wykonują realnych akcji.【F:ui/main_window.py†L2918-L2940】
- **Rozwiązanie:**
  1. W `UpdatedBotManagementWidget` dodać operacje wsadowe (async) korzystające z
     `UpdatedBotManager` oraz transakcji DB.
  2. Przy imporcie/eksporcie wykorzystać format JSON ze schematem walidacyjnym
     (np. `jsonschema`) i logować błędy do panelu powiadomień.

### 2.3 Automatyczne zapisywanie stanu UI
- **Problem:** Zarówno nowy, jak i stary główny widok pozostawiają `TODO` przy
  zapisie/odczycie pozycji oraz rozmiaru okna, co obniża UX.【F:ui/main_window.py†L2047-L2048】【F:ui/main_window.py†L3982-L3986】
- **Rozwiązanie:**
  1. Zapisać metadane UI w `config/ui_layout.json` (lub w bazie) i ładować je
     podczas startu.
  2. Dodać przywracanie układu dokowanych paneli oraz preferencji kolumn w
     tabelach.

## 3. Stabilność i wydajność

- Rozbudować `runtime_metrics` o histogramy czasu odpowiedzi dla każdej giełdy,
  a następnie skonfigurować alerty SLO (p95, p99) w Grafanie.
- Wprowadzić „task heartbeat” – watchdog wątku/loopa, który raportuje do
  Prometheusa, dzięki czemu zawieszenia GUI lub pętli eventowej będą wykrywane w
  kilka sekund.
- Skonfigurować profilowanie asynchroniczne (`asyncio slow callback handler`),
  aby rejestrować operacje przekraczające 100 ms i ułatwić dalszą optymalizację.

## 4. Gotowość operacyjna

- Przygotować migrację danych startowych (kontakty alertowe, domyślne limity
  ryzyka), aby świeża instalacja aplikacji była gotowa bez ręcznej ingerencji.
- Rozszerzyć `release_checklist` o walidację integralności bazy (czy wszystkie
  wymagane tabele mają wpisy startowe) oraz o test uruchomienia GUI w trybie
  headless.
- Dodać scenariusze E2E, które obejmują restart aplikacji oraz odzyskanie pracy
  botów po awarii.

## 5. Harmonogram wdrożenia

1. **Sprint 1:** Implementacja order executora + repozytorium strategii.
2. **Sprint 2:** Synchronizacja DataManagera, migracje ryzyka, integracja UI.
3. **Sprint 3:** Persistence powiadomień + masowe akcje w UI + eksport/import.
4. **Sprint 4:** Testy E2E, automatyzacja UX, rozszerzenie monitoringu.

Każdy sprint powinien kończyć się aktualizacją checklisty dystrybucyjnej i
powtórnym uruchomieniem `ops/release_checklist.py`, aby szybko wychwycić nowe
regresje.

