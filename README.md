# CryptoBot Desktop — Enterprise Ready

## Szybki start
```bash
pip install -r requirements.txt prometheus_client PyQt6
python main.py check-deps  # opcjonalna kontrola środowiska przed startem
python main.py             # uruchomienie aplikacji z GUI
# Prometheus exporter: http://localhost:8000/metrics
```

Dodaj `--write-report`, aby zapisać wynik kontroli do pliku
(`runtime_dependency_report.json` domyślnie lub ścieżka podana parametrem `--report-path`).

### Test akceptacyjny użytkownika
```bash
python tools/user_acceptance_test.py  # pełna ścieżka: zależności, pytest, compileall, start GUI
```
Raport JSON z wynikami można zapisać flagą `--json-output` i dołączyć do pipeline'u CI/CD.

## Testy
```bash
pytest -q      # szybkie
pytest tests/e2e                      # hermetyczne E2E (mock)
EXCHANGE_TESTNET=1 pytest tests/integration/test_testnet_smoke.py  # opcjonalny testnet
```

## Telemetria (Prometheus + Grafana)
```bash
cd ops
docker compose up -d
# Grafana: http://localhost:3000  (anonimowo, gotowy dashboard)
# Prometheus: http://localhost:9090
```

## Rate limiting i circuit breaker
- Plik: `config/rate_limits.yaml` (domyślne limity + `patterns` per endpoint)
- Auto-mapowanie funkcji -> endpoint: `config/endpoint_map.yaml`
- Dekorator: `@net_guard('binance:place_order')` albo `@net_guard('binance:rest:POST:/api/v3/order')`

## Sekrety
- Hasło główne + sejf (`utils/master_password.py`, `utils/secure_store.py`)

## Backup/Export
- UI: **Plik → Backup/Export…** (`Ctrl+E`)

## Kontrybucja
- Repozytorium oczekuje końcówek linii `LF` w plikach tekstowych; na systemach Windows przed pierwszym commitem ustaw `git config core.autocrlf false`, aby uniknąć ponownej konwersji i konfliktów przy pushu.
- Przed wysłaniem zmian do zdalnego repozytorium uruchom `pytest -q` oraz `python tools/check_runtime_dependencies.py --json`, aby upewnić się, że pipeline CI nie zgłosi regresji.
