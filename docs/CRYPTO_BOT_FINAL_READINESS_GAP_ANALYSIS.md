# CryptoBot Desktop – analiza luk przed produkcyjnym wydaniem

## Podsumowanie wykonanej inspekcji
- Wykonano pełny zestaw testów jednostkowych/integracyjnych (`pytest`).
- Przeanalizowano kluczowe moduły (warstwa tradingowa, strategie, UI, powiadomienia, dane i operacje) pod kątem pozostawionych `TODO`, braków wdrożeniowych oraz funkcji krytycznych dla produkcji.
- Zweryfikowano automatyczne checklisty wydaniowe (zaktualizowano checker zależności, aby współpracował z pipeline).

| Obszar | Status | Kluczowe obserwacje |
| --- | --- | --- |
| Składanie zleceń na żywo | **Blokada** | Brak implementacji faktycznego złożenia zlecenia przez API w `TradingModeManager` – aktualnie kończy się ostrzeżeniem i `None`. |
| Utrwalenie stanu strategii | **Blokada** | Kluczowe strategie (DCA, Grid, Scalping) mają niezaimplementowane operacje `load/save/update` do bazy danych. |
| Warstwa danych/risk | **Blokada** | `DataManager` wciąż operuje na domyślnych wartościach i nie zapisuje/nie pobiera realnych ustawień trybu/risku z bazy. |
| Powiadomienia | **Blokada** | `NotificationManager` ma kompletny brak implementacji operacji bazodanowych. |
| UI/Dashboard | **Wysoki priorytet** | Wiele widoków UI bazuje na placeholderach (dane dashboardu, statystyki portfela, masowe akcje botów, import/eksport). |
| Monitorowanie | **Średni priorytet** | Brak dynamicznej aktualizacji wskaźników (np. dzienne transakcje, zmiany 24h) oraz brak zapisu ustawień UI. |
| Bezpieczeństwo | **Rozwiązane** | W tej iteracji przywrócono weryfikację haseł użytkowników. |

## Krytyczne blokery produkcyjne
1. **Brak realnego składania zleceń live.** Metoda `place_live_order` kończy się ostrzeżeniem i brakiem zlecenia, co uniemożliwia handel na realnym rynku.【F:app/trading_mode_manager.py†L563-L587】
2. **Strategie nie utrwalają stanu.** Strategia DCA, Grid oraz Scalping mają puste implementacje odpowiedzialne za ładowanie i zapisywanie historii/zleceń, więc restart aplikacji skutkowałby utratą kontekstu.【F:app/strategy/dca.py†L439-L451】【F:app/strategy/grid.py†L564-L584】【F:app/strategy/scalping.py†L803-L828】
3. **NotificationManager bez integracji z bazą.** Cały moduł obsługi powiadomień nie zapisuje ani nie odczytuje danych z bazy; obecnie wszystkie operacje są `pass`, więc funkcja jest niefunkcjonalna w środowisku produkcyjnym.【F:app/notifications.py†L895-L964】
4. **DataManager trzyma tylko wartości domyślne.** Krytyczne ustawienia (tryb tradingu, limity ryzyka) nie są pobierane ani zapisywane do bazy – aplikacja działałaby na stałych wartościach niezależnie od konfiguracji operatora.【F:core/data_manager.py†L1032-L1094】

## Wysokie priorytety (do wykonania przed wydaniem)
- **Dashboard i widoki UI muszą używać realnych danych.** Aktualizacje metryk korzystają z placeholderów (`TODO` przy pobieraniu danych z backendu, liczeniu dziennego P&L czy liczby botów).【F:ui/main_window.py†L2315-L2676】
- **Masowe operacje na botach oraz import/eksport konfiguracji są niezaimplementowane.** Przyciski w UI wyświetlają jedynie komunikaty, nie wykonują faktycznych działań.【F:ui/main_window.py†L2915-L2941】
- **Portfel ma wyłącznie wartości domyślne.** Widok portfela nie aktualizuje statystyk i nie oblicza metryk 24h/PnL – zarówno dla danych sandbox, jak i realnych.【F:ui/portfolio.py†L685-L1302】
- **Strategia engine nie weryfikuje istniejących zleceń.** Brak implementacji `_has_order_at_level` uniemożliwia zapobieganie duplikatom w Grid Tradingu.【F:core/strategy_engine.py†L173-L176】

## Średni i niski priorytet
- Zapisywanie i przywracanie ustawień okna (rozmiar/pozycja) nie jest zaimplementowane, co obniża UX.【F:ui/main_window.py†L2038-L2048】【F:ui/main_window.py†L3980-L3987】
- Moduł logów nie aktualizuje poziomów i limitów na żywo (pozostawione `TODO`).【F:ui/logs.py†L1448-L1460】

## Zrealizowane w tej iteracji
- **Weryfikacja haseł.** `Database.authenticate_user` ponownie korzysta z `verify_password`, aktualizuje `last_login` i zwraca wyłącznie bezpieczne dane użytkownika.【F:app/database.py†L486-L520】
- **Zgodność narzędzi wydaniowych.** Skrypt `check_runtime_dependencies.py` akceptuje parametr `--json`, dzięki czemu pipeline wydaniowy nie kończy się błędem, zachowując dotychczasowy format raportu.【F:tools/check_runtime_dependencies.py†L109-L134】
- **Failsafe i awaryjne zamknięcia.** Menedżer `FailSafeManager` wykrywa niepoprawne zamknięcia, oznacza boty jako wstrzymane, zapisuje migawki w tabelach `system_failover_state`/`system_failover_events`, a przy wyłączaniu aplikacji oznacza czyste zakończenie pracy.【F:core/failsafe_manager.py†L1-L195】【F:app/database.py†L120-L215】【F:app/main.py†L20-L118】

## Rekomendowane kolejne kroki
1. Zaplanować sprint na implementację realnego składania zleceń oraz synchronizacji strategii z bazą (back-end + testy end-to-end).
2. Dostarczyć warstwę persistence/odczytu danych dla NotificationManagera oraz DataManagera, wraz z migracjami DB.
3. Uzupełnić UI o realne dane (portfel, dashboard, masowe akcje) po ukończeniu prac backendowych.
4. Wdrożyć testy integracyjne obejmujące flow „utwórz bota → uruchom → restart aplikacji → wznowienie strategii”.
5. Dopiero po wykonaniu powyższych kroków powtórzyć pełną checklistę dystrybucyjną i ocenić ponownie gotowość produkcyjną.

## Rozszerzone rozwiązania

Szczegółowe propozycje działań technicznych – podzielone na sprinty i priorytety –
zebrano w dokumencie [CRYPTO_BOT_ADDITIONAL_SOLUTIONS.md](CRYPTO_BOT_ADDITIONAL_SOLUTIONS.md).
Rekomendacje obejmują m.in. budowę serwisu egzekucji zleceń, persystencję
strategii, migracje ustawień ryzyka, domknięcie masowych akcji w UI oraz
rozszerzenia monitoringu i procedur operacyjnych.
