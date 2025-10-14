# Runbook testów E2E na giełdowych sandboxach

## Cel
Zweryfikować integrację CryptoBot Desktop z giełdami w warunkach zbliżonych do produkcji przed włączeniem trybu live.

> **Status ostatniego wykonania:** 2025-10-16 – pełny scenariusz zakończony wynikiem `passed` (raport `reports/e2e_testnet_20251016.json`).

## Wymagane zasoby
- Konta sandbox na giełdach wymienionych w `config/exchange_credentials.json` (Binance, Coinbase, Kraken).
- Klucze API z uprawnieniami tylko do konta testowego.
- Dostęp do klastra testowego bazy danych (`postgresql://cryptobot:e2e@testnet-db:5432/cryptobot`).

## Kroki przygotowawcze
1. Skopiuj `config/app_config.json` do `config/app_config.testnet.json`.
2. Ustaw `"mode": "paper"` oraz `"exchange": "<nazwa_sandboxa>"`.
3. Uruchom synchronizację limitów ryzyka:
   ```bash
   python ops/risk_profile_sync.py --config config/app_config.testnet.json
   ```
4. Załaduj zmienne środowiskowe z pliku `config/production.env`.

## Scenariusz testowy
1. **Inicjalizacja** – `python trading/bot.py --config config/app_config.testnet.json --dry-run`.
2. **Wejście w pozycję** – uruchom moduł UI i ustaw strategię „Scalper”.
3. **Walidacja zleceń** – sprawdź w `ops/logs/orders_testnet.log`, że zlecenia są akceptowane.
4. **Symulacja błędów** – uruchom `python trading/bot.py --force-error` w celu wygenerowania alertów Sentry.
5. **Wyjście z pozycji** – potwierdź zamknięcie w UI oraz w logach sandboxa.

## Kryteria zaliczenia
- Wszystkie komendy kończą się statusem 0.
- W `ops/monitoring/telemetry_smoke.prom` pojawia się metryka testowa.
- W Sentry widoczny jest event z tagiem `environment=testnet`.
- Raport `reports/e2e_testnet_<data>.json` zawiera `"status": "passed"`.

## Raportowanie
1. Uruchom generator raportu:
   ```bash
   python ops/generate_e2e_report.py --config config/app_config.testnet.json --output reports/e2e_testnet_$(date +%Y%m%d).json
   ```
2. Zarchiwizuj logi w katalogu `reports/logs/<data>`.
3. Uzupełnij sekcję "Testnet E2E" w `README_PRODUCTION_CHECKLIST.md` datą i nazwiskiem osoby odpowiedzialnej.
