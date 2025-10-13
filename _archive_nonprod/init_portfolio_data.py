#!/usr/bin/env python3
"""
Skrypt do inicjalizacji bazy danych i dodania przykładowych danych portfela
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Dodaj ścieżkę do modułów aplikacji
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Database
import logging
logger = logging.getLogger(__name__)

async def init_database_and_add_sample_data():
    """Inicjalizuje bazę danych i dodaje przykładowe dane portfela"""
    
    try:
        pass
logger.info("Inicjalizacja bazy danych...")
        db = Database()
        
        # Sprawdź czy tabele istnieją
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        table_names = [table[0] for table in tables]
logger.info(f"Istniejące tabele: {table_names}")
        
            pass
        if 'orders' not in table_names or 'positions' not in table_names:
logger.info("Tabele nie istnieją. Inicjalizuję bazę danych...")
            await db.init_database()
logger.info("Baza danych zainicjalizowana.")
        
        # Dodaj przykładowe zlecenia
logger.info("Dodawanie przykładowych zleceń...")
        
        sample_orders = [
            {
                'bot_id': 1,
                'exchange_order_id': 'order_001',
                'client_order_id': 'client_001',
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'type': 'market',
                'amount': 0.1,
                'price': 45000.0,
                'filled_amount': 0.1,
                'average_price': 45000.0,
                'status': 'filled',
                'fee': 4.5,
                'fee_asset': 'USDT',
                'timestamp': (datetime.now() - timedelta(days=5)).isoformat(),
                'filled_at': (datetime.now() - timedelta(days=5)).isoformat(),
                'raw_data': json.dumps({'exchange': 'binance'})
            },
            {
                'bot_id': 1,
                'exchange_order_id': 'order_002',
                'client_order_id': 'client_002',
                'symbol': 'ETH/USDT',
                'side': 'buy',
                'type': 'market',
                'amount': 2.0,
                'price': 3000.0,
                'filled_amount': 2.0,
                'average_price': 3000.0,
                'status': 'filled',
                'fee': 6.0,
                'fee_asset': 'USDT',
                'timestamp': (datetime.now() - timedelta(days=3)).isoformat(),
                'filled_at': (datetime.now() - timedelta(days=3)).isoformat(),
                'raw_data': json.dumps({'exchange': 'binance'})
            },
            {
                'bot_id': 1,
                'exchange_order_id': 'order_003',
                'client_order_id': 'client_003',
                'symbol': 'ADA/USDT',
                'side': 'buy',
                'type': 'limit',
                'amount': 1000.0,
                'price': 0.5,
                'filled_amount': 1000.0,
                'average_price': 0.5,
                'status': 'filled',
                'fee': 0.5,
                'fee_asset': 'USDT',
                'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
                'filled_at': (datetime.now() - timedelta(days=1)).isoformat(),
                'raw_data': json.dumps({'exchange': 'binance'})
            }
        ]
            pass
        
        for order in sample_orders:
            await db.add_order(**order)
logger.info(f"Dodano zlecenie: {order['symbol']} {order['side']} {order['amount']}")
        
        # Dodaj przykładowe pozycje
logger.info("Dodawanie przykładowych pozycji...")
        
        sample_positions = [
            {
                'bot_id': 1,
                'symbol': 'SOL/USDT',
                'side': 'long',
                'size': 10.0,
                'entry_price': 150.0,
                'current_price': 155.0,
                'unrealized_pnl': 50.0,
                'status': 'open'
            },
            {
                'bot_id': 1,
                'symbol': 'DOT/USDT',
                'side': 'long',
                'size': 100.0,
                'entry_price': 8.0,
                'current_price': 8.5,
                'unrealized_pnl': 50.0,
                'status': 'open'
            }
            pass
        ]
        
        for position in sample_positions:
            await db.add_position(**position)
logger.info(f"Dodano pozycję: {position['symbol']} {position['side']} {position['size']}")
        
        # Sprawdź dodane dane
        orders = await db.get_bot_orders(bot_id=1)
        positions = await db.get_positions(bot_id=1)
logger.info(f"\nPodsumowanie:")
logger.info(f"Dodano {len(orders)} zleceń")
logger.info(f"Dodano {len(positions)} pozycji")
            pass
                pass
        
        # Oblicz całkowitą wartość portfela
            pass
                pass
        total_value = 0
        for order in orders:
            if order['status'] == 'filled':
                total_value += order['filled_amount'] * order['average_price']
        
        for position in positions:
            if position['status'] == 'open':
                total_value += position['size'] * position['current_price']
logger.info(f"Całkowita wartość portfela: ${total_value:,.2f}")
        
        await conn.close()
    pass
logger.info("Inicjalizacja zakończona pomyślnie!")
        
    except Exception as e:
logger.info(f"Błąd podczas inicjalizacji: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(init_database_and_add_sample_data())