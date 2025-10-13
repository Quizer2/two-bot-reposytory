#!/usr/bin/env python3
"""
Test pobierania sald portfela z API Binance

Ten skrypt testuje funkcjonalność pobierania rzeczywistych sald
z API Binance dla portfolio.
"""

import sys
import os
import asyncio
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Dodaj ścieżkę do modułów aplikacji
sys.path.insert(0, str(Path(__file__).parent))

async def test_binance_portfolio():
    """Test pobierania sald z API Binance"""
logger.info("🧪 Testowanie pobierania sald z API Binance...")
    
    try:
        from app.api_config_manager import APIConfigManager
        from app.exchange import get_exchange_adapter
        
        # Test konfiguracji API
        api_manager = APIConfigManager()
logger.info("✅ APIConfigManager zainicjalizowany")
        
        # Sprawdź konfigurację Binance
        binance_config = api_manager.get_exchange_config('binance')
logger.info(f"📋 Konfiguracja Binance: {binance_config}")
        
        if not binance_config:
            pass
logger.info("❌ Brak konfiguracji Binance")
logger.info("💡 Skonfiguruj klucze API w ustawieniach aplikacji")
            return False
        
            pass
        if not binance_config.get('enabled'):
logger.info("❌ Binance API jest wyłączone")
logger.info("💡 Włącz Binance API w ustawieniach")
            return False
            pass
        
        if not binance_config.get('api_key') or not binance_config.get('secret'):
logger.info("❌ Brak kluczy API")
logger.info("💡 Dodaj klucze API w ustawieniach")
            return False
logger.info("✅ Konfiguracja API jest poprawna")
        
        # Test połączenia z Binance
logger.info("🔗 Łączenie z Binance...")
        binance = get_exchange_adapter(
            'binance',
            api_key=binance_config['api_key'],
            api_secret=binance_config['secret'],
            testnet=binance_config.get('sandbox', True)
        )
        
        await binance.connect()
logger.info("✅ Połączono z Binance")
        
        # Test pobierania sald
logger.info("💰 Pobieranie sald...")
            pass
        balances = await binance.get_balance()
        
        if not balances:
logger.info("❌ Nie udało się pobrać sald")
            return False
logger.info(f"✅ Pobrano salda dla {len(balances)} walut")
        
            pass
        # Wyświetl niezerowe salda
                pass
        total_value = 0.0
logger.info("\n📊 Niezerowe salda:")
        for currency, balance_info in balances.items():
                    pass
                        pass
            balance = balance_info.get('total', 0.0)
                            pass
            if balance > 0:
logger.info(f"  {currency}: {balance}")
                
                        pass
                # Pobierz cenę dla głównych kryptowalut
                    pass
                if currency != 'USDT':
                    try:
                        price = await binance.get_current_price(f"{currency}/USDT")
                        if price:
                            usd_value = balance * price
                            total_value += usd_value
logger.info(f"    Cena: ${price:.4f}, Wartość: ${usd_value:.2f}")
                    except Exception as e:
logger.info(f"    Błąd pobierania ceny: {e}")
                else:
                    total_value += balance
logger.info(f"    Wartość: ${balance:.2f}")
logger.info(f"\n💵 Łączna wartość portfela: ${total_value:.2f}")
        
        # Zamknij połączenie
        await binance.disconnect()
logger.info("✅ Rozłączono z Binance")
        
        return True
        
        pass
    except Exception as e:
logger.info(f"❌ Błąd podczas testowania: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_portfolio_integration():
    """Test integracji z Portfolio"""
logger.info("\n🧪 Testowanie integracji z Portfolio...")
            pass
    
    try:
        from ui.portfolio import Portfolio
        
        # Utwórz instancję Portfolio
        portfolio = Portfolio()
logger.info("✅ Portfolio utworzone")
        
        # Test ładowania sald z Binance
        result = await portfolio.load_binance_balances()
        
        if result:
                pass
            balances = result['balances']
            portfolio_data = result['portfolio_data']
logger.info(f"✅ Pobrano {len(balances)} walut z Portfolio")
            pass
logger.info(f"💵 Łączna wartość: ${portfolio_data['total_value']:.2f}")
            
            # Wyświetl top 5 walut
            sorted_balances = sorted(
                balances.items(), 
                key=lambda x: x[1]['usd_value'], 
                reverse=True
            )[:5]
logger.info("\n🏆 Top 5 walut:")
            for currency, data in sorted_balances:
logger.info(f"  {currency}: {data['balance']:.6f} (${data['usd_value']:.2f})")
            
            return True
        else:
logger.info("❌ Nie udało się pobrać sald przez Portfolio")
            return False
        
    except Exception as e:
logger.info(f"❌ Błąd integracji Portfolio: {e}")
        import traceback
        traceback.print_exc()
        return False
        pass

async def main():
        pass
    """Główna funkcja testowa"""
logger.info("🚀 Test pobierania sald portfela z API Binance\n")
    
    # Test 1: Bezpośrednie API
    success1 = await test_binance_portfolio()
    
    # Test 2: Integracja z Portfolio
    success2 = await test_portfolio_integration()
logger.info(f"\n📋 Wyniki testów:")
logger.info(f"  API Binance: {'✅ PASS' if success1 else '❌ FAIL'}")
logger.info(f"  Integracja Portfolio: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
logger.info("\n🎉 Wszystkie testy przeszły pomyślnie!")
logger.info("💡 Portfolio będzie teraz pobierać rzeczywiste salda z Binance")
    else:
logger.info("\n⚠️  Niektóre testy nie powiodły się")
logger.info("💡 Sprawdź konfigurację API w ustawieniach aplikacji")

if __name__ == "__main__":
    asyncio.run(main())