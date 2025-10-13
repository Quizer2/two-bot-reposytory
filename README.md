# CryptoBot Desktop — Enterprise Ready

## Szybki start
```bash
pip install -r requirements.txt prometheus_client PyQt6
python app.py  # albo start głównego modułu aplikacji
# Prometheus exporter: http://localhost:8000/metrics
```

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
