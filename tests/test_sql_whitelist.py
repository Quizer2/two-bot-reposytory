#!/usr/bin/env python3
"""
Testy walidacji dozwolonych kolumn (whitelist) w dynamicznych zapytaniach SQL

Sprawdzane funkcje:
- DatabaseManager.create_risk_limit
- DatabaseManager.update_risk_limits
- DatabaseManager.update_position

Weryfikujemy, że:
- Próba użycia niedozwolonych kolumn skutkuje zwróceniem False
- Mieszanka dozwolonych i niedozwolonych kolumn aktualizuje tylko dozwolone
"""

import unittest
import asyncio
import sys
import os

# Dodaj root projektu do sys.path jak w innych testach
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DatabaseManager


class TestSQLWhitelist(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Użyj bazy w pamięci, utwórz schemat i podstawowe encje
        self.db = DatabaseManager(db_path=":memory:")
        await self.db.create_tables()
        self.user_id = await self.db.create_user("test_user_whitelist", "password", "user@example.com")
        # Typ musi być jednym z: 'DCA', 'Grid', 'Scalping', 'Custom'
        self.bot_id = await self.db.create_bot(self.user_id, "bot_whitelist", "Custom", "binance", "BTC/USDT", {})
        self.assertIsNotNone(self.user_id)
        self.assertIsNotNone(self.bot_id)

    async def asyncTearDown(self):
        await self.db.close()

    async def test_create_risk_limit_invalid_only(self):
        # Tylko niedozwolone kolumny -> powinno zwrócić False
        ok = await self.db.create_risk_limit(bot_id=self.bot_id, user_id=self.user_id, evil_field=1, drop_table="x")
        self.assertFalse(ok)

    async def test_create_risk_limit_valid_and_invalid(self):
        # Mieszanka dozwolonej i niedozwolonej kolumny -> powinno zwrócić True i zapisać tylko dozwoloną
        ok = await self.db.create_risk_limit(bot_id=self.bot_id, user_id=self.user_id, 
                                             max_daily_loss_percent=7.5, evil="x")
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT max_daily_loss_percent FROM risk_limits WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['max_daily_loss_percent'], 7.5)

    async def test_update_risk_limits_reject_invalid_only(self):
        # Najpierw dodaj poprawny rekord limitów
        ok = await self.db.create_risk_limit(bot_id=self.bot_id, user_id=self.user_id, max_drawdown_percent=15.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id FROM risk_limits WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        limit_id = row['id']

        # Tylko niedozwolone pola -> False
        ok = await self.db.update_risk_limits(limit_id, invalid_column=99, some_hack='X')
        self.assertFalse(ok)

        # Mieszanka dozwolonych i niedozwolonych -> True, aktualizuje tylko dozwolone
        ok = await self.db.update_risk_limits(limit_id, max_drawdown_percent=20.0, INVALID='Y')
        self.assertTrue(ok)
        cursor = await conn.execute('SELECT max_drawdown_percent FROM risk_limits WHERE id = ?', (limit_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['max_drawdown_percent'], 20.0)

    async def test_update_position_reject_invalid_columns(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'BTC/USDT', 'buy', 0.01, 45000.0, stop_loss_price=44000.0, take_profit_price=46000.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']

        # Próba aktualizacji niedozwoloną kolumną -> False
        ok = await self.db.update_position(position_id, evil_column=123)
        self.assertFalse(ok)

        # Mieszanka dozwolonej (current_price) i niedozwolonej -> powinno zwrócić False zgodnie z implementacją
        ok = await self.db.update_position(position_id, current_price=45555.5, injected='bad')
        self.assertFalse(ok)
        # Sprawdź, że wartość nie została zaktualizowana (ponieważ cała operacja została odrzucona)
        cursor = await conn.execute('SELECT current_price FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # current_price może być None jeśli nie był ustawiony; w każdym razie nie powinien równać się 45555.5 po odrzuceniu
        self.assertNotEqual(row['current_price'], 45555.5)
        # Po odrzuconej aktualizacji mieszanej current_price powinno pozostać niezmienione (tu oczekujemy None)
        self.assertIsNone(row['current_price'])

    async def test_update_bot_statistics_safe_update(self):
        # Początkowe wartości powinny być wartościami domyślnymi (0/0.0)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT total_profit, total_trades, win_rate, max_drawdown FROM bots WHERE id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['total_profit'], 0.0)
        self.assertEqual(row['total_trades'], 0)
        self.assertAlmostEqual(row['win_rate'], 0.0)
        self.assertAlmostEqual(row['max_drawdown'], 0.0)

        # Zaktualizuj tylko wybrane pola i sprawdź, że inne pozostają przy wartościach domyślnych
        await self.db.update_bot_statistics(self.bot_id, total_profit=123.45, win_rate=0.7)
        cursor = await conn.execute('SELECT total_profit, total_trades, win_rate, max_drawdown FROM bots WHERE id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['total_profit'], 123.45)
        self.assertEqual(row['total_trades'], 0)
        self.assertAlmostEqual(row['win_rate'], 0.7)
        self.assertAlmostEqual(row['max_drawdown'], 0.0)

    async def test_update_order_status_parameterization_and_timestamps(self):
        # Utwórz zlecenie
        order_id = await self.db.save_order(self.bot_id, 'ex123', 'cl123', 'BTC/USDT', 'buy', 'limit', 0.01, price=45000.0, raw_data={'x': 1})
        self.assertIsNotNone(order_id)

        # Ustaw status 'filled' i sprawdź timestamps
        await self.db.update_order_status(order_id, status='filled', filled_amount=0.01, average_price=45100.0, fee=0.1, fee_asset='USDT')
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT status, filled_amount, average_price, fee, fee_asset, filled_at, canceled_at FROM orders WHERE id = ?', (order_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'filled')
        self.assertAlmostEqual(row['filled_amount'], 0.01)
        self.assertAlmostEqual(row['average_price'], 45100.0)
        self.assertAlmostEqual(row['fee'], 0.1)
        self.assertEqual(row['fee_asset'], 'USDT')
        self.assertIsNotNone(row['filled_at'])
        self.assertIsNone(row['canceled_at'])

        # Próba wstrzyknięcia przez wartość status (powinna zostać odrzucona przez CHECK, status pozostanie 'new')
        order_id2 = await self.db.save_order(self.bot_id, 'ex124', 'cl124', 'BTC/USDT', 'buy', 'limit', 0.01, price=45000.0, raw_data={'x': 2})
        self.assertIsNotNone(order_id2)
        inj = "filled; DROP TABLE orders;--"
        await self.db.update_order_status(order_id2, status=inj, error_message='hack')
        cursor = await conn.execute('SELECT status, filled_at, canceled_at, error_message FROM orders WHERE id = ?', (order_id2,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'new')
        # Ponieważ status != 'filled' ani 'canceled', znaczniki czasu powinny pozostać None
        self.assertIsNone(row['filled_at'])
        self.assertIsNone(row['canceled_at'])
        # Aktualizacja z nieprawidłowym statusem została odrzucona przez CHECK, więc error_message pozostało bez zmian
        self.assertIsNone(row['error_message'])

    async def test_update_bot_status_valid_transitions(self):
        # Początkowo bot ma status 'stopped' i brak znaczników czasu
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT status, started_at, stopped_at, last_error FROM bots WHERE id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'stopped')
        self.assertIsNone(row['started_at'])
        self.assertIsNone(row['stopped_at'])
        self.assertIsNone(row['last_error'])

        # Ustaw status 'active' -> powinien ustawić started_at i wyczyścić last_error
        await self.db.update_bot_status(self.bot_id, 'active')
        cursor = await conn.execute('SELECT status, started_at, stopped_at, last_error FROM bots WHERE id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'active')
        self.assertIsNotNone(row['started_at'])
        self.assertIsNone(row['stopped_at'])
        self.assertIsNone(row['last_error'])

        # Ustaw status 'error' -> powinien ustawić stopped_at i last_error
        await self.db.update_bot_status(self.bot_id, 'error', error_message='boom')
        cursor = await conn.execute('SELECT status, started_at, stopped_at, last_error FROM bots WHERE id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'error')
        self.assertIsNotNone(row['stopped_at'])
        self.assertEqual(row['last_error'], 'boom')

    async def test_update_bot_status_reject_invalid_status(self):
        # Próba wstrzyknięcia przez wartość status powinna zostać zignorowana (brak dopasowanej gałęzi)
        inj = "active; DROP TABLE bots;--"
        await self.db.update_bot_status(self.bot_id, inj, error_message='hack')
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT status, started_at, stopped_at, last_error FROM bots WHERE id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # Status pozostaje domyślny ('stopped'), brak zmian timestampów i last_error
        self.assertEqual(row['status'], 'stopped')
        self.assertIsNone(row['started_at'])
        self.assertIsNone(row['stopped_at'])
        self.assertIsNone(row['last_error'])

    async def test_update_position_allowed_columns_positive(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'ETH/USDT', 'sell', 0.5, 2500.0, stop_loss_price=2400.0, take_profit_price=2600.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']

        # Aktualizacja tylko dozwolonymi kolumnami -> True
        ok = await self.db.update_position(position_id, current_price=2550.5, realized_pnl=12.34)
        self.assertTrue(ok)

        # Sprawdź, że wartości zostały zaktualizowane
        cursor = await conn.execute('SELECT current_price, realized_pnl FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['current_price'], 2550.5)
        self.assertAlmostEqual(row['realized_pnl'], 12.34)

    async def test_update_position_side_and_size_updates_values(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'SOL/USDT', 'buy', 1.5, 150.0, stop_loss_price=140.0, take_profit_price=160.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, side, size FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertEqual(row['side'], 'buy')
        self.assertAlmostEqual(row['size'], 1.5)

        # Aktualizacja dozwolonymi kolumnami: side i size
        ok = await self.db.update_position(position_id, side='sell', size=2.0)
        self.assertTrue(ok)

        # Sprawdź aktualizacje
        cursor = await conn.execute('SELECT side, size FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['side'], 'sell')
        self.assertAlmostEqual(row['size'], 2.0)

    async def test_update_position_empty_updates_returns_false_and_no_change(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'XRP/USDT', 'sell', 500.0, 0.5, stop_loss_price=0.45, take_profit_price=0.55)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, current_price, realized_pnl, status FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        orig_current_price = row['current_price']
        orig_realized_pnl = row['realized_pnl']
        orig_status = row['status']

        # Wywołanie bez żadnych pól -> powinno zwrócić False i nie zmienić rekordu
        ok = await self.db.update_position(position_id)
        self.assertFalse(ok)

        cursor = await conn.execute('SELECT current_price, realized_pnl, status FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['current_price'], orig_current_price)
        self.assertEqual(row['realized_pnl'], orig_realized_pnl)
        self.assertEqual(row['status'], orig_status)

    async def test_update_risk_limits_updates_timestamp_and_values(self):
        # Utwórz limity ryzyka
        ok = await self.db.create_risk_limit(bot_id=self.bot_id, user_id=self.user_id, max_daily_loss_percent=5.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, updated_at FROM risk_limits WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        limit_id = row['id']
        old_updated_at = row['updated_at']

        # Odczekaj aby zmieniła się sekunda timestampu
        await asyncio.sleep(1)

        # Aktualizacja dozwolonej kolumny -> True, updated_at powinien się zmienić
        ok = await self.db.update_risk_limits(limit_id, max_daily_loss_percent=6.0)
        self.assertTrue(ok)
        cursor = await conn.execute('SELECT max_daily_loss_percent, updated_at FROM risk_limits WHERE id = ?', (limit_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['max_daily_loss_percent'], 6.0)
        self.assertNotEqual(row['updated_at'], old_updated_at)

    async def test_update_order_status_canceled_timestamps_and_error(self):
        # Utwórz zlecenie
        order_id = await self.db.save_order(self.bot_id, 'ex125', 'cl125', 'BTC/USDT', 'sell', 'limit', 0.02, price=45200.0, raw_data={'x': 3})
        self.assertIsNotNone(order_id)

        # Ustaw status 'canceled' i error_message
        await self.db.update_order_status(order_id, status='canceled', error_message='user_cancelled')
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT status, filled_at, canceled_at, error_message FROM orders WHERE id = ?', (order_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'canceled')
        self.assertIsNone(row['filled_at'])
        self.assertIsNotNone(row['canceled_at'])
        self.assertEqual(row['error_message'], 'user_cancelled')

    async def test_close_position_sets_closed_status_and_timestamp(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'LTC/USDT', 'buy', 1.0, 70.0, stop_loss_price=65.0, take_profit_price=80.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
    
        # Zamknij pozycję i sprawdź efekty
        ok = await self.db.close_position(position_id, close_price=75.5, realized_pnl=5.5)
        self.assertTrue(ok)
        cursor = await conn.execute('SELECT status, current_price, realized_pnl, closed_at FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'closed')
        self.assertAlmostEqual(row['current_price'], 75.5)
        self.assertAlmostEqual(row['realized_pnl'], 5.5)
        self.assertIsNotNone(row['closed_at'])

    async def test_update_position_bulk_allowed_updates_and_mixed_rejection(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'ADA/USDT', 'buy', 1000.0, 0.50, stop_loss_price=0.45, take_profit_price=0.60)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, current_price, stop_loss_price, take_profit_price, realized_pnl, status FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']

        # Masowa aktualizacja wyłącznie dozwolonych kolumn -> powinno zakończyć się powodzeniem
        ok = await self.db.update_position(position_id,
                                           current_price=0.52,
                                           stop_loss_price=0.46,
                                           take_profit_price=0.62,
                                           realized_pnl=1.23,
                                           status='open')
        self.assertTrue(ok)

        # Sprawdź, że wartości zostały zaktualizowane
        cursor = await conn.execute('SELECT current_price, stop_loss_price, take_profit_price, realized_pnl, status FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['current_price'], 0.52)
        self.assertAlmostEqual(row['stop_loss_price'], 0.46)
        self.assertAlmostEqual(row['take_profit_price'], 0.62)
        self.assertAlmostEqual(row['realized_pnl'], 1.23)
        self.assertEqual(row['status'], 'open')

        # Mieszanka dozwolonej i niedozwolonej kolumny -> cała aktualizacja powinna zostać odrzucona
        ok = await self.db.update_position(position_id, current_price=0.55, trailing_stop_price=0.50)
        self.assertFalse(ok)

        # Sprawdź, że żadna wartość nie zmieniła się po odrzuconej aktualizacji mieszanej
        cursor = await conn.execute('SELECT current_price FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['current_price'], 0.52)

    async def test_update_position_status_closed_does_not_set_closed_at(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'ADA/USDT', 'buy', 100.0, 0.25, stop_loss_price=0.2, take_profit_price=0.3)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, status, closed_at FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        # Początkowo status 'open' i closed_at = None
        self.assertEqual(row['status'], 'open')
        self.assertIsNone(row['closed_at'])
    
        # Aktualizacja statusu na 'closed' przez update_position nie powinna ustawić closed_at
        ok = await self.db.update_position(position_id, status='closed', current_price=0.27)
        self.assertTrue(ok)
    
        cursor = await conn.execute('SELECT status, current_price, closed_at FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'closed')
        self.assertAlmostEqual(row['current_price'], 0.27)
        # closed_at powinno pozostać None, bo jest ustawiane tylko przez close_position
        self.assertIsNone(row['closed_at'])

    async def test_save_daily_statistics_injection_and_get_bot_statistics_filters(self):
        # Wstaw normalne statystyki
        await self.db.save_daily_statistics(self.bot_id, '2024-01-01', trades_count=5, profit_loss=10.0, volume=1000.0, win_trades=3, loss_trades=2, fees_paid=0.5)
        await self.db.save_daily_statistics(self.bot_id, '2024-01-02', trades_count=7, profit_loss=-2.0, volume=800.0, win_trades=4, loss_trades=3, fees_paid=0.4)
        await self.db.save_daily_statistics(self.bot_id, '2024-01-03', trades_count=9, profit_loss=5.0, volume=1200.0, win_trades=6, loss_trades=3, fees_paid=0.6)

        # Próba wstrzyknięcia przez wartość date (powinna zostać potraktowana jako zwykły string, bez wykonania)
        inj_date = "2024-01-02'); DROP TABLE bot_statistics;--"
        await self.db.save_daily_statistics(self.bot_id, inj_date, trades_count=3, profit_loss=1.0, volume=300.0, win_trades=2, loss_trades=1, fees_paid=0.2)

        # Tabela powinna nadal istnieć, a rekordy powinny być wstawione
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT COUNT(*) as cnt FROM bot_statistics WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # 4 rekordy: 3 normalne + 1 z inj_date
        self.assertEqual(row['cnt'], 4)

        # Dodatkowo wstaw kolejny normalny rekord po inj aby upewnić się, że tabela nie została usunięta
        await self.db.save_daily_statistics(self.bot_id, '2024-01-04', trades_count=2, profit_loss=0.0, volume=200.0, win_trades=1, loss_trades=1, fees_paid=0.1)
        cursor = await conn.execute('SELECT COUNT(*) as cnt FROM bot_statistics WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['cnt'], 5)

        # Filtrowanie po zakresie dat powinno zwrócić rekordy od 2024-01-02 do 2024-01-03 (włącznie)
        stats = await self.db.get_bot_statistics(self.bot_id, start_date='2024-01-02', end_date='2024-01-03')
        self.assertIsInstance(stats, list)
        # Oczekujemy 3 rekordów: '2024-01-02', inj_date, '2024-01-03'
    async def test_update_position_trailing_stop_price_rejected_and_no_partial_update(self):
        # Utwórz pozycję z ustawionym take_profit_price
        ok = await self.db.create_position(self.bot_id, 'ETH/USDT', 'buy', 1.0, 2500.0, stop_loss_price=2400.0, take_profit_price=2600.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, trailing_stop_price, take_profit_price FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        orig_trailing = row['trailing_stop_price']
        orig_tp = row['take_profit_price']
        self.assertIsNone(orig_trailing)
        self.assertAlmostEqual(orig_tp, 2600.0)

        # Próba aktualizacji niedozwolonej kolumny trailing_stop_price razem z dozwoloną take_profit_price -> całość powinna zostać odrzucona
        ok = await self.db.update_position(position_id, trailing_stop_price=2450.0, take_profit_price=2700.0)
        self.assertFalse(ok)

        # Sprawdź, że żadna z wartości nie została zaktualizowana
        cursor = await conn.execute('SELECT trailing_stop_price, take_profit_price FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row['trailing_stop_price'])
        self.assertAlmostEqual(row['take_profit_price'], 2600.0)

    async def test_update_position_entry_price_updates_value(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'SOL/USDT', 'sell', 2.0, 150.0, stop_loss_price=155.0, take_profit_price=140.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, entry_price, size FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertAlmostEqual(row['entry_price'], 150.0)
        self.assertAlmostEqual(row['size'], 2.0)

        # Aktualizuj entry_price (dozwolona kolumna)
        ok = await self.db.update_position(position_id, entry_price=152.5)
        self.assertTrue(ok)

        cursor = await conn.execute('SELECT entry_price, size FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['entry_price'], 152.5)
        # Rozmiar nie powinien się zmienić
        self.assertAlmostEqual(row['size'], 2.0)

    async def test_update_position_side_injection_value_is_stored_and_table_intact(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'BNB/USDT', 'buy', 1.0, 300.0, stop_loss_price=290.0, take_profit_price=320.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, side FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertEqual(row['side'], 'buy')

        # Próba wstrzyknięcia przez wartość side – powinna zostać odrzucona przez walidację
        inj = "sell; DROP TABLE positions;--"
        ok = await self.db.update_position(position_id, side=inj)
        self.assertFalse(ok)

        cursor = await conn.execute('SELECT side FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # Wartość side pozostaje niezmieniona
        self.assertEqual(row['side'], 'buy')

    async def test_update_position_side_and_size_updates_values(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'SOL/USDT', 'buy', 1.5, 150.0, stop_loss_price=140.0, take_profit_price=160.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, side, size FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertEqual(row['side'], 'buy')
        self.assertAlmostEqual(row['size'], 1.5)

        # Aktualizacja dozwolonymi kolumnami: side i size
        ok = await self.db.update_position(position_id, side='sell', size=2.0)
        self.assertTrue(ok)

        # Sprawdź aktualizacje
        cursor = await conn.execute('SELECT side, size FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['side'], 'sell')
        self.assertAlmostEqual(row['size'], 2.0)

    async def test_update_position_empty_updates_returns_false_and_no_change(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'XRP/USDT', 'sell', 500.0, 0.5, stop_loss_price=0.45, take_profit_price=0.55)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, current_price, realized_pnl, status FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        orig_current_price = row['current_price']
        orig_realized_pnl = row['realized_pnl']
        orig_status = row['status']

        # Wywołanie bez żadnych pól -> powinno zwrócić False i nie zmienić rekordu
        ok = await self.db.update_position(position_id)
        self.assertFalse(ok)

        cursor = await conn.execute('SELECT current_price, realized_pnl, status FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['current_price'], orig_current_price)
        self.assertEqual(row['realized_pnl'], orig_realized_pnl)
        self.assertEqual(row['status'], orig_status)

    async def test_update_risk_limits_updates_timestamp_and_values(self):
        # Utwórz limity ryzyka
        ok = await self.db.create_risk_limit(bot_id=self.bot_id, user_id=self.user_id, max_daily_loss_percent=5.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, updated_at FROM risk_limits WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        limit_id = row['id']
        old_updated_at = row['updated_at']

        # Odczekaj aby zmieniła się sekunda timestampu
        await asyncio.sleep(1)

        # Aktualizacja dozwolonej kolumny -> True, updated_at powinien się zmienić
        ok = await self.db.update_risk_limits(limit_id, max_daily_loss_percent=6.0)
        self.assertTrue(ok)

        cursor = await conn.execute('SELECT max_daily_loss_percent, updated_at FROM risk_limits WHERE id = ?', (limit_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['max_daily_loss_percent'], 6.0)
        self.assertNotEqual(row['updated_at'], old_updated_at)

    async def test_update_order_status_canceled_timestamps_and_error(self):
        # Utwórz zlecenie
        order_id = await self.db.save_order(self.bot_id, 'ex125', 'cl125', 'BTC/USDT', 'sell', 'limit', 0.02, price=45200.0, raw_data={'x': 3})
        self.assertIsNotNone(order_id)

        # Ustaw status 'canceled' i error_message
        await self.db.update_order_status(order_id, status='canceled', error_message='user_cancelled')
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT status, filled_at, canceled_at, error_message FROM orders WHERE id = ?', (order_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'canceled')
        self.assertIsNone(row['filled_at'])
        self.assertIsNotNone(row['canceled_at'])
        self.assertEqual(row['error_message'], 'user_cancelled')

    async def test_close_position_sets_closed_status_and_timestamp(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'LTC/USDT', 'buy', 1.0, 70.0, stop_loss_price=65.0, take_profit_price=80.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
    
        # Zamknij pozycję i sprawdź efekty
        ok = await self.db.close_position(position_id, close_price=75.5, realized_pnl=5.5)
        self.assertTrue(ok)
        cursor = await conn.execute('SELECT status, current_price, realized_pnl, closed_at FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'closed')
        self.assertAlmostEqual(row['current_price'], 75.5)
        self.assertAlmostEqual(row['realized_pnl'], 5.5)
        self.assertIsNotNone(row['closed_at'])

    async def test_update_position_status_closed_does_not_set_closed_at(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'ADA/USDT', 'buy', 100.0, 0.25, stop_loss_price=0.2, take_profit_price=0.3)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, status, closed_at FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        # Początkowo status 'open' i closed_at = None
        self.assertEqual(row['status'], 'open')
        self.assertIsNone(row['closed_at'])
    
        # Aktualizacja statusu na 'closed' przez update_position nie powinna ustawić closed_at
        ok = await self.db.update_position(position_id, status='closed', current_price=0.27)
        self.assertTrue(ok)
    
        cursor = await conn.execute('SELECT status, current_price, closed_at FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'closed')
        self.assertAlmostEqual(row['current_price'], 0.27)
        # closed_at powinno pozostać None, bo jest ustawiane tylko przez close_position
        self.assertIsNone(row['closed_at'])

    async def test_save_daily_statistics_injection_and_get_bot_statistics_filters(self):
        # Wstaw normalne statystyki
        await self.db.save_daily_statistics(self.bot_id, '2024-01-01', trades_count=5, profit_loss=10.0, volume=1000.0, win_trades=3, loss_trades=2, fees_paid=0.5)
        await self.db.save_daily_statistics(self.bot_id, '2024-01-02', trades_count=7, profit_loss=-2.0, volume=800.0, win_trades=4, loss_trades=3, fees_paid=0.4)
        await self.db.save_daily_statistics(self.bot_id, '2024-01-03', trades_count=9, profit_loss=5.0, volume=1200.0, win_trades=6, loss_trades=3, fees_paid=0.6)

        # Próba wstrzyknięcia przez wartość date (powinna zostać potraktowana jako zwykły string, bez wykonania)
        inj_date = "2024-01-02'); DROP TABLE bot_statistics;--"
        await self.db.save_daily_statistics(self.bot_id, inj_date, trades_count=3, profit_loss=1.0, volume=300.0, win_trades=2, loss_trades=1, fees_paid=0.2)

        # Tabela powinna nadal istnieć, a rekordy powinny być wstawione
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT COUNT(*) as cnt FROM bot_statistics WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # 4 rekordy: 3 normalne + 1 z inj_date
        self.assertEqual(row['cnt'], 4)

        # Dodatkowo wstaw kolejny normalny rekord po inj aby upewnić się, że tabela nie została usunięta
        await self.db.save_daily_statistics(self.bot_id, '2024-01-04', trades_count=2, profit_loss=0.0, volume=200.0, win_trades=1, loss_trades=1, fees_paid=0.1)
        cursor = await conn.execute('SELECT COUNT(*) as cnt FROM bot_statistics WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['cnt'], 5)

        # Filtrowanie po zakresie dat powinno zwrócić rekordy od 2024-01-02 do 2024-01-03 (włącznie)
        stats = await self.db.get_bot_statistics(self.bot_id, start_date='2024-01-02', end_date='2024-01-03')
        self.assertIsInstance(stats, list)
        # Oczekujemy 3 rekordów: '2024-01-02', inj_date, '2024-01-03'
    async def test_update_position_trailing_stop_price_rejected_and_no_partial_update(self):
        # Utwórz pozycję z ustawionym take_profit_price
        ok = await self.db.create_position(self.bot_id, 'ETH/USDT', 'buy', 1.0, 2500.0, stop_loss_price=2400.0, take_profit_price=2600.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, trailing_stop_price, take_profit_price FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        orig_trailing = row['trailing_stop_price']
        orig_tp = row['take_profit_price']
        self.assertIsNone(orig_trailing)
        self.assertAlmostEqual(orig_tp, 2600.0)

        # Próba aktualizacji niedozwolonej kolumny trailing_stop_price razem z dozwoloną take_profit_price -> całość powinna zostać odrzucona
        ok = await self.db.update_position(position_id, trailing_stop_price=2450.0, take_profit_price=2700.0)
        self.assertFalse(ok)

        # Sprawdź, że żadna z wartości nie została zaktualizowana
        cursor = await conn.execute('SELECT trailing_stop_price, take_profit_price FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row['trailing_stop_price'])
        self.assertAlmostEqual(row['take_profit_price'], 2600.0)


    async def test_update_position_side_injection_value_is_stored_and_table_intact(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'BNB/USDT', 'buy', 1.0, 300.0, stop_loss_price=290.0, take_profit_price=320.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, side FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertEqual(row['side'], 'buy')

        # Próba wstrzyknięcia przez wartość side – powinna zostać odrzucona przez walidację
        inj = "sell; DROP TABLE positions;--"
        ok = await self.db.update_position(position_id, side=inj)
        self.assertFalse(ok)

        cursor = await conn.execute('SELECT side FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # Wartość side pozostaje niezmieniona
        self.assertEqual(row['side'], 'buy')

    async def test_update_position_side_and_size_updates_values(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'SOL/USDT', 'buy', 1.5, 150.0, stop_loss_price=140.0, take_profit_price=160.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, side, size FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertEqual(row['side'], 'buy')
        self.assertAlmostEqual(row['size'], 1.5)

        # Aktualizacja dozwolonymi kolumnami: side i size
        ok = await self.db.update_position(position_id, side='sell', size=2.0)
        self.assertTrue(ok)

        # Sprawdź aktualizacje
        cursor = await conn.execute('SELECT side, size FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['side'], 'sell')
        self.assertAlmostEqual(row['size'], 2.0)

    async def test_update_position_empty_updates_returns_false_and_no_change(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'XRP/USDT', 'sell', 500.0, 0.5, stop_loss_price=0.45, take_profit_price=0.55)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, current_price, realized_pnl, status FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        orig_current_price = row['current_price']
        orig_realized_pnl = row['realized_pnl']
        orig_status = row['status']

        # Wywołanie bez żadnych pól -> powinno zwrócić False i nie zmienić rekordu
        ok = await self.db.update_position(position_id)
        self.assertFalse(ok)

        cursor = await conn.execute('SELECT current_price, realized_pnl, status FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['current_price'], orig_current_price)
        self.assertEqual(row['realized_pnl'], orig_realized_pnl)
        self.assertEqual(row['status'], orig_status)

    async def test_update_risk_limits_updates_timestamp_and_values(self):
        # Utwórz limity ryzyka
        ok = await self.db.create_risk_limit(bot_id=self.bot_id, user_id=self.user_id, max_daily_loss_percent=5.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, updated_at FROM risk_limits WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        limit_id = row['id']
        old_updated_at = row['updated_at']

        # Odczekaj aby zmieniła się sekunda timestampu
        await asyncio.sleep(1)

        # Aktualizacja dozwolonej kolumny -> True, updated_at powinien się zmienić
        ok = await self.db.update_risk_limits(limit_id, max_daily_loss_percent=6.0)
        self.assertTrue(ok)

        cursor = await conn.execute('SELECT max_daily_loss_percent, updated_at FROM risk_limits WHERE id = ?', (limit_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row['max_daily_loss_percent'], 6.0)
        self.assertNotEqual(row['updated_at'], old_updated_at)

    async def test_update_order_status_canceled_timestamps_and_error(self):
        # Utwórz zlecenie
        order_id = await self.db.save_order(self.bot_id, 'ex125', 'cl125', 'BTC/USDT', 'sell', 'limit', 0.02, price=45200.0, raw_data={'x': 3})
        self.assertIsNotNone(order_id)

        # Ustaw status 'canceled' i error_message
        await self.db.update_order_status(order_id, status='canceled', error_message='user_cancelled')
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT status, filled_at, canceled_at, error_message FROM orders WHERE id = ?', (order_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'canceled')
        self.assertIsNone(row['filled_at'])
        self.assertIsNotNone(row['canceled_at'])
        self.assertEqual(row['error_message'], 'user_cancelled')

    async def test_close_position_sets_closed_status_and_timestamp(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'LTC/USDT', 'buy', 1.0, 70.0, stop_loss_price=65.0, take_profit_price=80.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
    
        # Zamknij pozycję i sprawdź efekty
        ok = await self.db.close_position(position_id, close_price=75.5, realized_pnl=5.5)
        self.assertTrue(ok)
        cursor = await conn.execute('SELECT status, current_price, realized_pnl, closed_at FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'closed')
        self.assertAlmostEqual(row['current_price'], 75.5)
        self.assertAlmostEqual(row['realized_pnl'], 5.5)
        self.assertIsNotNone(row['closed_at'])

    async def test_update_position_status_closed_does_not_set_closed_at(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'ADA/USDT', 'buy', 100.0, 0.25, stop_loss_price=0.2, take_profit_price=0.3)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, status, closed_at FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        # Początkowo status 'open' i closed_at = None
        self.assertEqual(row['status'], 'open')
        self.assertIsNone(row['closed_at'])
    
        # Aktualizacja statusu na 'closed' przez update_position nie powinna ustawić closed_at
        ok = await self.db.update_position(position_id, status='closed', current_price=0.27)
        self.assertTrue(ok)
    
        cursor = await conn.execute('SELECT status, current_price, closed_at FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['status'], 'closed')
        self.assertAlmostEqual(row['current_price'], 0.27)
        # closed_at powinno pozostać None, bo jest ustawiane tylko przez close_position
        self.assertIsNone(row['closed_at'])

    async def test_save_daily_statistics_injection_and_get_bot_statistics_filters(self):
        # Wstaw normalne statystyki
        await self.db.save_daily_statistics(self.bot_id, '2024-01-01', trades_count=5, profit_loss=10.0, volume=1000.0, win_trades=3, loss_trades=2, fees_paid=0.5)
        await self.db.save_daily_statistics(self.bot_id, '2024-01-02', trades_count=7, profit_loss=-2.0, volume=800.0, win_trades=4, loss_trades=3, fees_paid=0.4)
        await self.db.save_daily_statistics(self.bot_id, '2024-01-03', trades_count=9, profit_loss=5.0, volume=1200.0, win_trades=6, loss_trades=3, fees_paid=0.6)

        # Próba wstrzyknięcia przez wartość date (powinna zostać potraktowana jako zwykły string, bez wykonania)
        inj_date = "2024-01-02'); DROP TABLE bot_statistics;--"
        await self.db.save_daily_statistics(self.bot_id, inj_date, trades_count=3, profit_loss=1.0, volume=300.0, win_trades=2, loss_trades=1, fees_paid=0.2)

        # Tabela powinna nadal istnieć, a rekordy powinny być wstawione
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT COUNT(*) as cnt FROM bot_statistics WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # 4 rekordy: 3 normalne + 1 z inj_date
        self.assertEqual(row['cnt'], 4)

        # Dodatkowo wstaw kolejny normalny rekord po inj aby upewnić się, że tabela nie została usunięta
        await self.db.save_daily_statistics(self.bot_id, '2024-01-04', trades_count=2, profit_loss=0.0, volume=200.0, win_trades=1, loss_trades=1, fees_paid=0.1)
        cursor = await conn.execute('SELECT COUNT(*) as cnt FROM bot_statistics WHERE bot_id = ?', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['cnt'], 5)

        # Filtrowanie po zakresie dat powinno zwrócić rekordy od 2024-01-02 do 2024-01-03 (włącznie)
        stats = await self.db.get_bot_statistics(self.bot_id, start_date='2024-01-02', end_date='2024-01-03')
        self.assertIsInstance(stats, list)
        # Oczekujemy 3 rekordów: '2024-01-02', inj_date, '2024-01-03'
    async def test_update_position_trailing_stop_price_rejected_and_no_partial_update(self):
        # Utwórz pozycję z ustawionym take_profit_price
        ok = await self.db.create_position(self.bot_id, 'ETH/USDT', 'buy', 1.0, 2500.0, stop_loss_price=2400.0, take_profit_price=2600.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, trailing_stop_price, take_profit_price FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        orig_trailing = row['trailing_stop_price']
        orig_tp = row['take_profit_price']
        self.assertIsNone(orig_trailing)
        self.assertAlmostEqual(orig_tp, 2600.0)

        # Próba aktualizacji niedozwolonej kolumny trailing_stop_price razem z dozwoloną take_profit_price -> całość powinna zostać odrzucona
        ok = await self.db.update_position(position_id, trailing_stop_price=2450.0, take_profit_price=2700.0)
        self.assertFalse(ok)

        # Sprawdź, że żadna z wartości nie została zaktualizowana
        cursor = await conn.execute('SELECT trailing_stop_price, take_profit_price FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row['trailing_stop_price'])
        self.assertAlmostEqual(row['take_profit_price'], 2600.0)


    async def test_update_position_side_injection_value_is_stored_and_table_intact(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'BNB/USDT', 'buy', 1.0, 300.0, stop_loss_price=290.0, take_profit_price=320.0)
        self.assertTrue(ok)
        conn = await self.db.get_connection()
        cursor = await conn.execute('SELECT id, side FROM positions WHERE bot_id = ? ORDER BY id DESC LIMIT 1', (self.bot_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        position_id = row['id']
        self.assertEqual(row['side'], 'buy')

        # Próba wstrzyknięcia przez wartość side – powinna zostać odrzucona przez walidację
        inj = "sell; DROP TABLE positions;--"
        ok = await self.db.update_position(position_id, side=inj)
        self.assertFalse(ok)

        cursor = await conn.execute('SELECT side FROM positions WHERE id = ?', (position_id,))
        row = await cursor.fetchone()
        self.assertIsNotNone(row)
        # Wartość side pozostaje niezmieniona
        self.assertEqual(row['side'], 'buy')

    async def test_update_position_side_and_size_updates_values(self):
        # Utwórz pozycję
        ok = await self.db.create_position(self.bot_id, 'SOL/USDT', 'buy', 1.5, 150.0, stop_loss_price=140.0, take_profit_price=160.0)
        self.assertTrue(ok)