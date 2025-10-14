# Production Checklist (final mile)

- [x] Network timeouts on all HTTP/WS calls
- [x] Backoff/reconnect with status wiring
- [x] No `eval`/`exec` in production paths
- [x] No `bare except:`; proper logging of errors
- [x] SQL is parameterized (no f-strings/format)
- [x] Logging masks secrets (API keys/tokens)
- [x] UI tested headless in CI (PyQt6 offscreen)
- [x] Adapters enforce precision & idempotent CIDs
- [x] Backup/Export ZIP
- [x] Risk profiles and Go LIVE guard in UI
- [x] Live/simulated exchange adapters with ccxt integration
- [x] Risk alerts/escalations publikowane na EventBus
- [x] Release checklist automation (`ops/release_checklist.py`)
- [x] Distribution readiness verifier (`tools/check_distribution_readiness.py` z kontrolą znaczników konfliktów)
- [x] UI bundle builder (`tools/build_ui_bundle.py`)

Recommended before flipping full LIVE:
- [x] End-to-end tests on exchange testnets (market data → order → fill → audit) — patrz `docs/TESTNET_E2E_RUNBOOK.md`
- [x] Metrics & alerting (Sentry/Prometheus/Grafana) — patrz `docs/PRODUCTION_ALERTING_PLAN.md`
- [x] DB migrations/versioning strategy — patrz `docs/DB_MIGRATION_PLAN.md`
- [x] Circuit breaker & rate limiter applied around exchange client methods
