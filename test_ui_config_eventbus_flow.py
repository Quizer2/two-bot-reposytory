"""
Test przepływu danych UI → ConfigManager → EventBus
Weryfikuje czy zmiany w UI są poprawnie zapisywane przez ConfigManager i propagowane przez EventBus
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any

# Dodaj ścieżkę do modułów
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import get_config_manager
from utils.event_bus import get_event_bus, EventTypes
from utils.logger import get_logger

class UIConfigEventBusFlowTest:
    """Test przepływu danych UI → ConfigManager → EventBus"""
    
    def __init__(self):
        self.logger = get_logger("UIConfigEventBusFlowTest")
        self.config_manager = get_config_manager()
        self.event_bus = get_event_bus()
        self.events_received = []
        self.test_results = []
        
    def setup_event_listener(self):
        """Konfiguruje nasłuchiwanie eventów"""
        def on_config_updated(event_data):
            self.events_received.append({
                'timestamp': datetime.now().isoformat(),
                'event_type': 'CONFIG_UPDATED',
                'data': event_data
            })
            self.logger.info(f"Received CONFIG_UPDATED event: {event_data}")
        
        self.event_bus.subscribe(EventTypes.CONFIG_UPDATED, on_config_updated)
        self.logger.info("Event listener configured")
    
    def simulate_ui_risk_settings_change(self):
        """Symuluje zmianę ustawień ryzyka z UI"""
        try:
            self.logger.info("=== Test 1: Symulacja zmiany ustawień ryzyka z UI ===")
            
            # Pobierz aktualną konfigurację
            current_config = self.config_manager.get_app_config()
            
            # Symuluj zmianę limitów ryzyka (jak z UI)
            new_risk_settings = {
                'max_daily_loss': 500.0,
                'max_position_size': 1000.0,
                'stop_loss_percentage': 5.0,
                'take_profit_percentage': 10.0,
                'max_open_positions': 3
            }
            
            # Aktualizuj konfigurację
            current_config['trading']['risk_management'] = new_risk_settings
            
            # Zapisz przez ConfigManager (symulacja akcji z UI)
            events_before = len(self.events_received)
            self.config_manager.save_config('app', current_config)
            
            # Sprawdź czy event został wysłany
            time.sleep(0.1)  # Krótka pauza na propagację eventu
            events_after = len(self.events_received)
            
            if events_after > events_before:
                self.test_results.append({
                    'test': 'UI Risk Settings Change',
                    'status': 'PASSED',
                    'details': f'Event propagated successfully. Events: {events_before} → {events_after}'
                })
                self.logger.info("✅ UI Risk Settings Change - PASSED")
            else:
                self.test_results.append({
                    'test': 'UI Risk Settings Change',
                    'status': 'FAILED',
                    'details': f'No event received. Events: {events_before} → {events_after}'
                })
                self.logger.error("❌ UI Risk Settings Change - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'UI Risk Settings Change',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ UI Risk Settings Change - ERROR: {e}")
    
    def simulate_ui_bot_config_change(self):
        """Symuluje zmianę konfiguracji bota z UI"""
        try:
            self.logger.info("=== Test 2: Symulacja zmiany konfiguracji bota z UI ===")
            
            # Pobierz aktualną konfigurację
            current_config = self.config_manager.get_app_config()
            
            # Symuluj zmianę konfiguracji bota (jak z UI)
            new_bot_settings = {
                'enabled': True,
                'strategy': 'ai_trading',
                'symbol': 'BTCUSDT',
                'amount': 100.0,
                'interval': '1h'
            }
            
            # Dodaj nową sekcję bot_config
            if 'bots' not in current_config:
                current_config['bots'] = {}
            current_config['bots']['test_bot'] = new_bot_settings
            
            # Zapisz przez ConfigManager (symulacja akcji z UI)
            events_before = len(self.events_received)
            self.config_manager.save_config('app', current_config)
            
            # Sprawdź czy event został wysłany
            time.sleep(0.1)  # Krótka pauza na propagację eventu
            events_after = len(self.events_received)
            
            if events_after > events_before:
                self.test_results.append({
                    'test': 'UI Bot Config Change',
                    'status': 'PASSED',
                    'details': f'Event propagated successfully. Events: {events_before} → {events_after}'
                })
                self.logger.info("✅ UI Bot Config Change - PASSED")
            else:
                self.test_results.append({
                    'test': 'UI Bot Config Change',
                    'status': 'FAILED',
                    'details': f'No event received. Events: {events_before} → {events_after}'
                })
                self.logger.error("❌ UI Bot Config Change - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'UI Bot Config Change',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ UI Bot Config Change - ERROR: {e}")
    
    def simulate_ui_theme_change(self):
        """Symuluje zmianę motywu UI"""
        try:
            self.logger.info("=== Test 3: Symulacja zmiany motywu UI ===")
            
            # Pobierz aktualną konfigurację UI
            current_ui_config = self.config_manager.get_ui_config()
            
            # Symuluj zmianę motywu (jak z UI)
            current_ui_config['theme'] = 'dark' if current_ui_config.get('theme') == 'light' else 'light'
            current_ui_config['last_updated'] = datetime.now().isoformat()
            
            # Zapisz przez ConfigManager (symulacja akcji z UI)
            events_before = len(self.events_received)
            self.config_manager.save_config('ui', current_ui_config)
            
            # Sprawdź czy event został wysłany
            time.sleep(0.1)  # Krótka pauza na propagację eventu
            events_after = len(self.events_received)
            
            if events_after > events_before:
                self.test_results.append({
                    'test': 'UI Theme Change',
                    'status': 'PASSED',
                    'details': f'Event propagated successfully. Events: {events_before} → {events_after}'
                })
                self.logger.info("✅ UI Theme Change - PASSED")
            else:
                self.test_results.append({
                    'test': 'UI Theme Change',
                    'status': 'FAILED',
                    'details': f'No event received. Events: {events_before} → {events_after}'
                })
                self.logger.error("❌ UI Theme Change - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'UI Theme Change',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ UI Theme Change - ERROR: {e}")
    
    def verify_event_structure(self):
        """Weryfikuje strukturę otrzymanych eventów"""
        try:
            self.logger.info("=== Test 4: Weryfikacja struktury eventów ===")
            
            if not self.events_received:
                self.test_results.append({
                    'test': 'Event Structure Verification',
                    'status': 'FAILED',
                    'details': 'No events received to verify'
                })
                self.logger.error("❌ Event Structure Verification - FAILED: No events")
                return
            
            # Sprawdź ostatni event
            last_event = self.events_received[-1]
            required_fields = ['config_type', 'old_config', 'new_config', 'timestamp']
            
            missing_fields = []
            for field in required_fields:
                if field not in last_event['data']:
                    missing_fields.append(field)
            
            if not missing_fields:
                self.test_results.append({
                    'test': 'Event Structure Verification',
                    'status': 'PASSED',
                    'details': f'All required fields present: {required_fields}'
                })
                self.logger.info("✅ Event Structure Verification - PASSED")
            else:
                self.test_results.append({
                    'test': 'Event Structure Verification',
                    'status': 'FAILED',
                    'details': f'Missing fields: {missing_fields}'
                })
                self.logger.error(f"❌ Event Structure Verification - FAILED: Missing {missing_fields}")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Event Structure Verification',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Event Structure Verification - ERROR: {e}")
    
    def test_config_persistence(self):
        """Testuje czy zmiany są trwale zapisane"""
        try:
            self.logger.info("=== Test 5: Weryfikacja trwałości zapisów ===")
            
            # Sprawdź czy ostatnie zmiany są zapisane w plikach
            app_config = self.config_manager.get_app_config()
            ui_config = self.config_manager.get_ui_config()
            
            # Sprawdź czy test_bot istnieje w konfiguracji
            if 'bots' in app_config and 'test_bot' in app_config['bots']:
                persistence_check = True
                details = "Configuration changes persisted successfully"
            else:
                persistence_check = False
                details = "Configuration changes not found in saved config"
            
            if persistence_check:
                self.test_results.append({
                    'test': 'Config Persistence',
                    'status': 'PASSED',
                    'details': details
                })
                self.logger.info("✅ Config Persistence - PASSED")
            else:
                self.test_results.append({
                    'test': 'Config Persistence',
                    'status': 'FAILED',
                    'details': details
                })
                self.logger.error("❌ Config Persistence - FAILED")
                
        except Exception as e:
            self.test_results.append({
                'test': 'Config Persistence',
                'status': 'ERROR',
                'details': f'Exception: {str(e)}'
            })
            self.logger.error(f"❌ Config Persistence - ERROR: {e}")
    
    def run_all_tests(self):
        """Uruchamia wszystkie testy przepływu UI → ConfigManager → EventBus"""
        self.logger.info("🚀 Starting UI → ConfigManager → EventBus Flow Tests")
        
        # Konfiguruj nasłuchiwanie eventów
        self.setup_event_listener()
        
        # Uruchom testy
        self.simulate_ui_risk_settings_change()
        self.simulate_ui_bot_config_change()
        self.simulate_ui_theme_change()
        self.verify_event_structure()
        self.test_config_persistence()
        
        # Podsumowanie
        self.print_summary()
        
        return self.test_results
    
    def print_summary(self):
        """Wyświetla podsumowanie testów"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 PODSUMOWANIE TESTÓW UI → ConfigManager → EventBus")
        self.logger.info("="*60)
        
        passed = sum(1 for result in self.test_results if result['status'] == 'PASSED')
        failed = sum(1 for result in self.test_results if result['status'] == 'FAILED')
        errors = sum(1 for result in self.test_results if result['status'] == 'ERROR')
        total = len(self.test_results)
        
        self.logger.info(f"📈 Wyniki: {passed}/{total} testów przeszło pomyślnie")
        self.logger.info(f"✅ Przeszły: {passed}")
        self.logger.info(f"❌ Nie przeszły: {failed}")
        self.logger.info(f"⚠️ Błędy: {errors}")
        
        self.logger.info(f"\n📨 Otrzymane eventy: {len(self.events_received)}")
        
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'FAILED' else "⚠️"
            self.logger.info(f"{status_icon} {result['test']}: {result['status']}")
            if result['status'] != 'PASSED':
                self.logger.info(f"   Details: {result['details']}")
        
        self.logger.info("="*60)

def main():
    """Główna funkcja testowa"""
    test = UIConfigEventBusFlowTest()
    results = test.run_all_tests()
    
    # Zapisz wyniki do pliku
    with open('ui_config_eventbus_flow_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'UI → ConfigManager → EventBus Flow',
            'results': results,
            'events_received': test.events_received
        }, f, indent=2, ensure_ascii=False)
    
    return results

if __name__ == "__main__":
    main()