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
- [ ] End-to-end tests on exchange testnets (market data → order → fill → audit)
- [ ] Metrics & alerting (Sentry/Prometheus/Grafana)
- [ ] DB migrations/versioning strategy
- [ ] Circuit breaker & rate limiter applied around exchange client methods
