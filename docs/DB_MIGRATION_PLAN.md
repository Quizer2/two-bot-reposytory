# Plan migracji bazy danych CryptoBot Desktop

## Cele
- Utrzymać spójność danych portfela i historii zleceń podczas aktualizacji schematu.
- Zapewnić możliwość szybkiego rollbacku w przypadku niepowodzenia migracji.

> **Status:** Migracja `1.1 -> 1.2` ukończona 2025-10-16 (zarejestrowano w `ops/db/migration_log.md`).

## Stosowane narzędzia
- `alembic` – silnik migracji schematu.
- `pg_dump` – eksport danych przed migracją.
- `ops/db/migration_matrix.yaml` – opis kompatybilności wersji.

## Procedura migracji
1. **Przygotowanie**
   - Upewnij się, że katalog `ops/db` zawiera migracje Alembica.
   - Wygeneruj kopię zapasową:
     ```bash
     pg_dump $DATABASE_URL > backups/$(date +%Y%m%d)_before_migration.sql
     ```
2. **Walidacja**
   - Uruchom testy schematu:
     ```bash
     pytest tests/test_exchange_portfolio_db_flow.py -m schema
     ```
3. **Migracja**
   ```bash
   alembic upgrade head
   ```
4. **Weryfikacja po migracji**
   - Uruchom `pytest tests/test_exchange_portfolio_db_flow.py`.
   - Sprawdź integralność danych w `reports/db_integrity.json`.

## Rollback
- W przypadku błędu:
  ```bash
  alembic downgrade -1
  psql $DATABASE_URL < backups/<data>_before_migration.sql
  ```

## Dokumentowanie
- Po zakończonej migracji uzupełnij wpis w `ops/db/migration_log.md` (data, wersja schematu, status).
- Zaktualizuj `README_PRODUCTION_CHECKLIST.md` sekcję „Migracje DB” datą ostatniej weryfikacji.
