#!/usr/bin/env python3
"""
Skrypt do sprawdzenia struktury bazy danych i dodania przykładowych danych portfela
"""

import sqlite3
import json
from datetime import datetime, timedelta
import random
import logging
logger = logging.getLogger(__name__)

def check_database_structure():
    """Sprawdza strukturę bazy danych"""
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
logger.info("=== STRUKTURA BAZY DANYCH ===")
    
    # Pobierz wszystkie tabele
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
logger.info(f"Znalezione tabele: {len(tables)}")
    for table in tables:
        table_name = table[0]
logger.info(f"\n--- Tabela: {table_name} ---")
        
        # Pobierz strukturę tabeli
        cursor.execute("PRAGMA table_info(?);", (table_name,))
        columns = cursor.fetchall()
        
        for col in columns:
            pass
logger.info(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
        # Sprawdź ile rekordów jest w tabeli
        cursor.execute("SELECT COUNT(*) FROM ?;", (table_name,))
        count = cursor.fetchone()[0]
logger.info(f"  Liczba rekordów: {count}")
    
    conn.close()

def add_sample_portfolio_data():
    """Dodaje przykładowe dane portfela do bazy danych"""
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
logger.info("\n=== DODAWANIE PRZYKŁADOWYCH DANYCH ===")
    
    # Sprawdź czy tabela orders istnieje i dodaj przykładowe transakcje
        pass
    try:
        # Dodaj przykładowe zlecenia/transakcje
        sample_orders = [
            {
                'bot_id': 'test_bot_1',
                'exchange': 'binance',
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'amount': 0.001,
                'price': 45000.0,
                'status': 'filled',
                'timestamp': datetime.now() - timedelta(hours=2),
                'fee': 0.45
            },
            {
                'bot_id': 'test_bot_2',
                'exchange': 'binance',
                'symbol': 'ETHUSDT',
                'side': 'buy',
                'amount': 0.1,
                'price': 3200.0,
                'status': 'filled',
                'timestamp': datetime.now() - timedelta(hours=1),
                'fee': 0.32
            },
            {
                'bot_id': 'test_bot_1',
                'exchange': 'binance',
                'symbol': 'ADAUSDT',
                'side': 'sell',
                'amount': 100.0,
                'price': 0.85,
                'status': 'filled',
                'timestamp': datetime.now() - timedelta(minutes=30),
                'fee': 0.085
            }
        ]
            pass
        
        for order in sample_orders:
            cursor.execute("""
                INSERT OR REPLACE INTO orders 
                (bot_id, exchange, symbol, side, amount, price, status, timestamp, fee)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order['bot_id'], order['exchange'], order['symbol'], 
                order['side'], order['amount'], order['price'], 
                order['status'], order['timestamp'].isoformat(), order['fee']
            ))
        pass
logger.info(f"Dodano {len(sample_orders)} przykładowych zleceń")
        
    except sqlite3.Error as e:
        pass
logger.info(f"Błąd przy dodawaniu zleceń: {e}")
    
    # Sprawdź czy tabela positions istnieje i dodaj przykładowe pozycje
    try:
        sample_positions = [
            {
                'bot_id': 'test_bot_1',
                'symbol': 'BTCUSDT',
                'amount': 0.001,
                'entry_price': 45000.0,
                'current_price': 46500.0,
                'pnl': 1.5,
                'timestamp': datetime.now()
            },
            {
                'bot_id': 'test_bot_2',
                'symbol': 'ETHUSDT',
                'amount': 0.1,
                'entry_price': 3200.0,
                'current_price': 3350.0,
                'pnl': 15.0,
                'timestamp': datetime.now()
            }
        ]
        
        for pos in sample_positions:
            cursor.execute("""
                INSERT OR REPLACE INTO positions 
                (bot_id, symbol, amount, entry_price, current_price, pnl, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pos['bot_id'], pos['symbol'], pos['amount'], 
                pos['entry_price'], pos['current_price'], 
                pos['pnl'], pos['timestamp'].isoformat()
            ))
logger.info(f"Dodano {len(sample_positions)} przykładowych pozycji")
        
    except sqlite3.Error as e:
logger.info(f"Błąd przy dodawaniu pozycji: {e}")
    
    conn.commit()
    conn.close()
logger.info("Dane zostały zapisane do bazy danych")

def verify_data():
    """Sprawdza czy dane zostały dodane poprawnie"""
        pass
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
logger.info("\n=== WERYFIKACJA DANYCH ===")
    
            pass
    try:
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
                pass
logger.info(f"Liczba zleceń w bazie: {orders_count}")
        pass
        
        if orders_count > 0:
            cursor.execute("SELECT * FROM orders LIMIT 3")
            orders = cursor.fetchall()
logger.info("Przykładowe zlecenia:")
            for order in orders:
logger.info(f"  {order}")
            pass
    except sqlite3.Error as e:
logger.info(f"Błąd przy sprawdzaniu zleceń: {e}")
    
                pass
    try:
        cursor.execute("SELECT COUNT(*) FROM positions")
        positions_count = cursor.fetchone()[0]
logger.info(f"Liczba pozycji w bazie: {positions_count}")
        
        if positions_count > 0:
            cursor.execute("SELECT * FROM positions LIMIT 3")
            positions = cursor.fetchall()
logger.info("Przykładowe pozycje:")
            for pos in positions:
logger.info(f"  {pos}")
    except sqlite3.Error as e:
logger.info(f"Błąd przy sprawdzaniu pozycji: {e}")
    
    conn.close()

if __name__ == "__main__":
logger.info("🔍 Sprawdzanie struktury bazy danych i dodawanie przykładowych danych portfela")
logger.info("=" * 70)
    
    check_database_structure()
    add_sample_portfolio_data()
    verify_data()
logger.info("\n✅ Zakończono!")