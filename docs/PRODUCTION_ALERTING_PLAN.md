# Plan alertingu produkcyjnego

## Cel
Zapewnić wczesne wykrywanie awarii i regresji wydajnościowych CryptoBot Desktop przy wykorzystaniu istniejącej telemetrii Prometheusa oraz centralnego systemu powiadomień (Sentry + Slack).

> **Status:** Integracja Sentry oraz pipeline Alertmanager → Slack aktywne od 2025-10-16 (alert smoke potwierdzony przez `tools/telemetry_smoke.py`).

## Konfiguracja Sentry
1. Utwórz projekt **CryptoBot Desktop** w Sentry i pobierz DSN.
2. Dodaj zmienne środowiskowe w `config/production.env`:
   ```env
   SENTRY_DSN=https://<token>@sentry.io/<project>
   SENTRY_ENVIRONMENT=production
   SENTRY_RELEASE=$(git rev-parse --short HEAD)
   ```
3. Uruchom narzędzie bootstrapowe:
   ```bash
   python tools/check_runtime_dependencies.py --sync-sentry
   ```
   Polecenie dodaje wpis DSN do pliku `config/runtime_overrides.json`, dzięki czemu backend telemetryczny ładuje konfigurację przy starcie.
4. Zweryfikuj, że raportowanie błędów jest aktywne:
   ```bash
   python tools/telemetry_smoke.py --raise-exception
   ```
   Skrypt powinien wysłać zdarzenie testowe widoczne w konsoli Sentry.

## Konfiguracja Prometheus/Grafana
1. Dodaj job `cryptobot-desktop` do konfiguracji Prometheusa:
   ```yaml
   - job_name: cryptobot-desktop
     metrics_path: /metrics
     static_configs:
       - targets: ['cryptobot-desktop:9100']
   ```
2. W katalogu `ops/grafana/dashboards` umieść dashboard `cryptobot_desktop_overview.json` (dostarczony w repozytorium) i zaimportuj go do Grafany.
3. Włącz alerty:
   - **Order Failure Rate**: warunek `increase(cryptobot_orders_failed_total[5m]) > 3`.
   - **Latency SLO**: warunek `histogram_quantile(0.95, rate(cryptobot_order_latency_bucket[5m])) > 750`.
4. Skonfiguruj integrację `Alertmanager -> Slack` z kanałem `#cryptobot-alerts`.

## PagerDuty/rotacja on-call
1. Utwórz usługę PagerDuty „CryptoBot Trading”.
2. Dodaj webhook Alertmanagera jako integration key.
3. Zdefiniuj rotację on-call (minimum dwie osoby, 24/7, zmiana co 1 tydzień).

## Runbook reagowania
1. Alert **Order Failure Rate**:
   - Sprawdź logi `ops/logs/order_processor.log`.
   - W razie awarii giełdy przełącz bota w tryb `paper` poleceniem `python ops/mode_switch.py --mode=paper`.
2. Alert **Latency SLO**:
   - Weryfikuj obciążenie CPU/RAM (`ops/metrics/system_dashboard.md`).
   - Rozważ restart modułu `trading/exchange_client.py`.
3. Po każdym incydencie zaktualizuj `ops/postmortems/<date>-<incident>.md` w ciągu 24 godzin.

## Testowanie konfiguracji
1. Uruchom lokalnie docker-compose `ops/monitoring/docker-compose.yaml`.
2. W aplikacji wywołaj `python tools/telemetry_smoke.py --alert-demo`.
3. Zweryfikuj alert w Alertmanagerze i powiadomienie w Slacku.

## Harmonogram przeglądów
- Co tydzień: review alertów (30 minut) – właściciel SRE.
- Co miesiąc: przegląd progów i dashboardów.
- Co kwartał: test procedury on-call (symulacja incydentu).
