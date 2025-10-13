# Architektura systemu

## Warstwy
- **UI (PyQt6)** — okna, statusy (API/WS/DB), toasty, themes
- **EventBus + Audit** — `utils/event_bus.py` → `logs/events.jsonl`
- **Strategie / Backtester** — `backtesting/*`, sygnały SMA, metryki, auto-domknięcie
- **Adaptery giełd** — `utils/adapters/exchange_adapter.py` (+ `utils/orders.py`)
- **Sieć** — `utils/net_wrappers.py` (**rate-limit + circuit-breaker + metrics**) + klienci `api/*`, `app/exchange/*`
- **Bezpieczeństwo** — `utils/encryption.py`, `utils/secure_store.py`, `utils/logging_config.py`
- **DB** — `utils/db_migrations.py`, parametryzowane SQL, guard w CI
- **Telemetria** — `utils/metrics_exporter.py` + `ops/*` (Prometheus/Grafana)

## Limity i mapowanie endpointów
- `config/rate_limits.yaml` — limity domyślne + `patterns` (method+path)
- `config/endpoint_map.yaml` — mapowanie nazwy funkcji na method+path dla każdej giełdy
- Dekorator `@net_guard('<exchange>:<function>')` automatycznie dobiera właściwy ogranicznik na podstawie mapy

## Start aplikacji
- `bootstrap/startup_checks.py` — setup logging, walidacja configów, migracje DB, start eksportera metryk, subskrypcja EventBus do metryk, preload limiterów

## CI
- ruff, mypy, pytest (+ PyQt6 offscreen), **SQL guard**, **E2E hermetyczne**
