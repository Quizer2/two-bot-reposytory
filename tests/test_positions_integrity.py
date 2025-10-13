import sqlite3
import tempfile
import os
import asyncio
from pathlib import Path

from app.database import DatabaseManager


def run(coro):
    return asyncio.run(coro)


def make_temp_db_path():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    return tmp.name


def cleanup(path):
    try:
        os.unlink(path)
    except Exception:
        pass


def get_last_position_id(db_path):
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute('SELECT id FROM positions ORDER BY id DESC LIMIT 1')
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        con.close()


def get_position_row(db_path, position_id):
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute('SELECT id, status, closed_at, size, entry_price FROM positions WHERE id = ?', (position_id,))
        return cur.fetchone()
    finally:
        con.close()


def test_create_position_size_zero_validation_and_db_check():
    db_path = make_temp_db_path()
    try:
        db = DatabaseManager(db_path=db_path)
        run(db.initialize())
        # Utwórz użytkownika i poprawnego bota (wymagane przez FK)
        user_id = run(db.create_user(username='u1', password='p1'))
        assert user_id is not None
        bot_id = run(db.create_bot(user_id=user_id, name='tbot', bot_type='Custom', exchange='BINANCE', pair='BTC/USDT', parameters={'x':1}))
        assert bot_id is not None
        # Walidacja aplikacyjna
        ok = run(db.create_position(bot_id=bot_id, symbol='BTC/USDT', side='buy', size=0.0, entry_price=100.0))
        assert ok is False
        # Walidacja na poziomie bazy (CHECK)
        con = sqlite3.connect(db_path)
        try:
            with con:
                try:
                    con.execute(
                        'INSERT INTO positions (bot_id, symbol, side, size, entry_price, status) VALUES (?,?,?,?,?,?)',
                        (bot_id, 'BTC/USDT', 'buy', 0.0, 100.0, 'open')
                    )
                    assert False, 'Expected IntegrityError for size=0'
                except sqlite3.IntegrityError:
                    pass
        finally:
            con.close()
        run(db.close())
    finally:
        cleanup(db_path)


def test_create_position_negative_entry_price_validation_and_db_check():
    db_path = make_temp_db_path()
    try:
        db = DatabaseManager(db_path=db_path)
        run(db.initialize())
        # Utwórz użytkownika i poprawnego bota (wymagane przez FK)
        user_id = run(db.create_user(username='u2', password='p2'))
        assert user_id is not None
        bot_id = run(db.create_bot(user_id=user_id, name='tbot2', bot_type='Custom', exchange='BINANCE', pair='ETH/USDT', parameters={'x':2}))
        assert bot_id is not None
        # Walidacja aplikacyjna
        ok = run(db.create_position(bot_id=bot_id, symbol='ETH/USDT', side='sell', size=1.0, entry_price=-1.0))
        assert ok is False
        # Walidacja na poziomie bazy (CHECK)
        con = sqlite3.connect(db_path)
        try:
            with con:
                try:
                    con.execute(
                        'INSERT INTO positions (bot_id, symbol, side, size, entry_price, status) VALUES (?,?,?,?,?,?)',
                        (bot_id, 'ETH/USDT', 'sell', 1.0, -1.0, 'open')
                    )
                    assert False, 'Expected IntegrityError for entry_price<0'
                except sqlite3.IntegrityError:
                    pass
        finally:
            con.close()
        run(db.close())
    finally:
        cleanup(db_path)


def test_update_position_open_resets_closed_at_and_db_rejects_open_with_closed_at():
    db_path = make_temp_db_path()
    try:
        db = DatabaseManager(db_path=db_path)
        run(db.initialize())
        # Utwórz użytkownika i poprawnego bota (wymagane przez FK)
        user_id = run(db.create_user(username='u3', password='p3'))
        assert user_id is not None
        bot_id = run(db.create_bot(user_id=user_id, name='tbot3', bot_type='Custom', exchange='BINANCE', pair='XRP/USDT', parameters={'x':3}))
        assert bot_id is not None
        # Utwórz pozycję
        assert run(db.create_position(bot_id=bot_id, symbol='XRP/USDT', side='buy', size=1.0, entry_price=10.0)) is True
        pid = get_last_position_id(db_path)
        assert pid is not None
        # Zamknij pozycję (ustawi status='closed' i closed_at != NULL)
        assert run(db.close_position(pid, close_price=11.0, realized_pnl=1.0)) is True
        row = get_position_row(db_path, pid)
        assert row is not None
        _, status, closed_at, _, _ = row
        assert status == 'closed'
        assert closed_at is not None
        # Próba bezpośredniego otwarcia pozycji w SQL bez czyszczenia closed_at -> powinna się nie udać (CHECK)
        con = sqlite3.connect(db_path)
        try:
            with con:
                try:
                    con.execute('UPDATE positions SET status = ? WHERE id = ?', ('open', pid))
                    assert False, 'Expected IntegrityError when setting status=open while closed_at non-NULL'
                except sqlite3.IntegrityError:
                    pass
        finally:
            con.close()
        # Aplikacyjna operacja otwarcia (powinna wyzerować closed_at)
        assert run(db.update_position(pid, status='open')) is True
        row = get_position_row(db_path, pid)
        assert row is not None
        _, status, closed_at, _, _ = row
        assert status == 'open'
        assert closed_at is None
        run(db.close())
    finally:
        cleanup(db_path)


def test_update_position_rejects_size_zero_and_negative_entry_price():
    db_path = make_temp_db_path()
    try:
        db = DatabaseManager(db_path=db_path)
        run(db.initialize())
        # Utwórz użytkownika i poprawnego bota (wymagane przez FK)
        user_id = run(db.create_user(username='u4', password='p4'))
        assert user_id is not None
        bot_id = run(db.create_bot(user_id=user_id, name='tbot4', bot_type='Custom', exchange='BINANCE', pair='ADA/USDT', parameters={'x':4}))
        assert bot_id is not None
        # Utwórz pozycję
        assert run(db.create_position(bot_id=bot_id, symbol='ADA/USDT', side='sell', size=2.0, entry_price=0.5)) is True
        pid = get_last_position_id(db_path)
        assert pid is not None
        # Próba ustawienia size=0 -> walidacja aplikacyjna
        assert run(db.update_position(pid, size=0.0)) is False
        # Próba ustawienia entry_price<0 -> walidacja aplikacyjna
        assert run(db.update_position(pid, entry_price=-0.1)) is False
        # Bezpośrednio przez SQL -> oba powinny rzucić IntegrityError
        con = sqlite3.connect(db_path)
        try:
            with con:
                for sql, params in [
                    ('UPDATE positions SET size = ? WHERE id = ?', (0.0, pid)),
                    ('UPDATE positions SET entry_price = ? WHERE id = ?', (-0.1, pid)),
                ]:
                    try:
                        con.execute(sql, params)
                        assert False, 'Expected IntegrityError for invalid update'
                    except sqlite3.IntegrityError:
                        pass
        finally:
            con.close()
        run(db.close())
    finally:
        cleanup(db_path)


def test_delete_bot_cascades_positions_orders_risk_limits():
    db_path = make_temp_db_path()
    try:
        db = DatabaseManager(db_path=db_path)
        run(db.initialize())
        # Utwórz użytkownika i bota
        user_id = run(db.create_user(username='u_cascade_bot', password='p'))
        assert user_id is not None
        bot_id = run(db.create_bot(user_id=user_id, name='bot_cascade', bot_type='Custom', exchange='BINANCE', pair='BTC/USDT', parameters={'x':1}))
        assert bot_id is not None
        # Utwórz pozycję, zlecenie i limit ryzyka
        assert run(db.create_position(bot_id=bot_id, symbol='BTC/USDT', side='buy', size=0.1, entry_price=100.0)) is True
        order_id = run(db.save_order(bot_id, 'ex_c1', 'cl_c1', 'BTC/USDT', 'buy', 'limit', 0.1, price=100.0, raw_data={'a':1}))
        assert order_id is not None
        assert run(db.create_risk_limit(bot_id=bot_id, user_id=user_id, max_drawdown_percent=10.0)) is True
        # Sprawdź, że rekordy istnieją
        con = sqlite3.connect(db_path)
        try:
            cur = con.execute('SELECT COUNT(*) FROM positions WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] >= 1
            cur = con.execute('SELECT COUNT(*) FROM orders WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] >= 1
            cur = con.execute('SELECT COUNT(*) FROM risk_limits WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] >= 1
        finally:
            con.close()
        # Usuń bota, używając połączenia aiosqlite (FK ON)
        async def _delete_bot_async(dbm, bid):
            conn = await dbm.get_connection()
            await conn.execute('DELETE FROM bots WHERE id = ?', (bid,))
            await conn.commit()
        run(_delete_bot_async(db, bot_id))
        # Zweryfikuj kaskadowe usunięcie
        con = sqlite3.connect(db_path)
        try:
            cur = con.execute('SELECT COUNT(*) FROM bots WHERE id = ?', (bot_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM positions WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM orders WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM risk_limits WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] == 0
        finally:
            con.close()
        run(db.close())
    finally:
        cleanup(db_path)


def test_delete_user_cascades_bots_and_children():
    db_path = make_temp_db_path()
    try:
        db = DatabaseManager(db_path=db_path)
        run(db.initialize())
        # Utwórz użytkownika i bota
        user_id = run(db.create_user(username='u_cascade_user', password='p'))
        assert user_id is not None
        bot_id = run(db.create_bot(user_id=user_id, name='bot_cascade_user', bot_type='Custom', exchange='BINANCE', pair='ETH/USDT', parameters={'y':2}))
        assert bot_id is not None
        # Utwórz pozycję, zlecenie i limit ryzyka
        assert run(db.create_position(bot_id=bot_id, symbol='ETH/USDT', side='sell', size=0.2, entry_price=50.0)) is True
        order_id = run(db.save_order(bot_id, 'ex_c2', 'cl_c2', 'ETH/USDT', 'sell', 'market', 0.2, raw_data={'b':2}))
        assert order_id is not None
        assert run(db.create_risk_limit(bot_id=bot_id, user_id=user_id, max_daily_loss_percent=7.5)) is True
        # Sprawdź, że rekordy istnieją
        con = sqlite3.connect(db_path)
        try:
            cur = con.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,))
            assert cur.fetchone()[0] >= 1
            cur = con.execute('SELECT COUNT(*) FROM positions WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] >= 1
            cur = con.execute('SELECT COUNT(*) FROM orders WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] >= 1
            cur = con.execute('SELECT COUNT(*) FROM risk_limits WHERE user_id = ?', (user_id,))
            assert cur.fetchone()[0] >= 1
        finally:
            con.close()
        # Usuń użytkownika (powinno usunąć bota i jego dzieci)
        async def _delete_user_async(dbm, uid):
            conn = await dbm.get_connection()
            await conn.execute('DELETE FROM users WHERE id = ?', (uid,))
            await conn.commit()
        run(_delete_user_async(db, user_id))
        # Zweryfikuj kaskadowe usunięcie
        con = sqlite3.connect(db_path)
        try:
            cur = con.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM positions WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM orders WHERE bot_id = ?', (bot_id,))
            assert cur.fetchone()[0] == 0
            cur = con.execute('SELECT COUNT(*) FROM risk_limits WHERE user_id = ?', (user_id,))
            assert cur.fetchone()[0] == 0
        finally:
            con.close()
        run(db.close())
    finally:
        cleanup(db_path)