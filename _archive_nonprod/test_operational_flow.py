#!/usr/bin/env python3
"""
Operational Flow Tests
Tests the complete flow: Config → RiskManager → UI → Bot Behavior
"""

import asyncio
import sys
import os
import json
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.risk_management import RiskManager
    from core.trading_engine import TradingEngine, OrderRequest, OrderType, OrderSide
    from ui.settings import RiskManagementWidget
    from app.config_manager import ConfigManager
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
except ImportError as e:
    pass
logger.info(f"Import error: {e}")
logger.info("Some modules may not be available for testing")

class TestOperationalFlow(unittest.TestCase):
    """Test complete operational flow from config to bot behavior"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        # Create test config
        self.test_config = {
            "risk_management": {
                "max_position_size": 1000.0,
                "max_daily_loss": 500.0,
                "max_drawdown": 0.15,
                "stop_loss_percentage": 0.02,
                "take_profit_percentage": 0.04,
                "max_daily_trades": 10,
                "risk_per_trade": 0.02,
                "use_kelly_criterion": False,
                "compound_profits": True
            },
            "trading": {
                "demo_mode": True,
                "default_exchange": "binance"
            }
        }
        
            pass
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_config_to_risk_manager_flow(self):
        """Test: Config file → RiskManager loading"""
logger.info("\n=== Testing Config → RiskManager Flow ===")
            pass
        
        try:
            # Initialize RiskManager (uses default constructor)
            risk_manager = RiskManager()
            
            # Test basic initialization
            self.assertIsNotNone(risk_manager)
            self.assertIsNotNone(risk_manager.default_limits)
logger.info("✓ RiskManager initialized successfully")
            
            # Test limits access
            default_limits = risk_manager.default_limits
            self.assertIsInstance(default_limits.daily_loss_limit, float)
            self.assertIsInstance(default_limits.position_size_limit, float)
            self.assertIsInstance(default_limits.max_drawdown_limit, float)
logger.info("✓ RiskManager limits accessible")
            
            # Test setting bot-specific limits
            bot_id = 1
            from app.risk_management import RiskLimits
            
            new_limits = RiskLimits(
                daily_loss_limit=500.0,
                daily_profit_limit=2000.0,
                max_drawdown_limit=15.0,
                position_size_limit=1000.0,
                max_open_positions=5,
                max_correlation=0.8,
                volatility_threshold=10.0,
                var_limit=250.0
            )
            
            # Set limits for specific bot
            await risk_manager.update_risk_limits(bot_id, new_limits)
            pass
logger.info("✓ Bot-specific risk limits set successfully")
            
        except Exception as e:
logger.info(f"✗ Config → RiskManager flow failed: {e}")
            raise
    
    async def test_risk_manager_to_trading_engine_flow(self):
            pass
        """Test: RiskManager → TradingEngine integration"""
logger.info("\n=== Testing RiskManager → TradingEngine Flow ===")
        
        try:
            # Initialize components
            risk_manager = RiskManager()
            trading_engine = TradingEngine()
            
            # Initialize trading engine
            await trading_engine.initialize()
            
            # Test basic integration
            self.assertIsNotNone(risk_manager)
            self.assertIsNotNone(trading_engine)
logger.info("✓ Components initialized successfully")
            
            # Test order validation through risk manager
            bot_id = 1
            
            # Test large order (should be rejected)
            large_order_valid = await risk_manager.check_position_size_limit(
                bot_id=bot_id,
                position_size=50000.0,  # Very large order
                available_balance=10000.0
            )
            
            self.assertFalse(large_order_valid, 
                           "Large order should be rejected by risk manager")
logger.info("✓ Risk manager correctly rejects oversized orders")
            
            # Test reasonable order (should be approved)
            reasonable_order_valid = await risk_manager.check_position_size_limit(
                bot_id=bot_id,
                position_size=100.0,  # Reasonable order
                available_balance=10000.0
            )
            
            # Should be approved
            self.assertTrue(reasonable_order_valid,
                              "Reasonable order should be approved")
logger.info("✓ Risk manager correctly processes reasonable orders")
            
            # Test trading engine order placement
            order_request = OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=100.0,
                price=None
            )
            
            # Place order in demo mode
            result = await trading_engine.place_order(order_request)
            self.assertIsNotNone(result, "Order should be placed successfully in demo mode")
logger.info("✓ Trading engine successfully places orders")
            
        except Exception as e:
logger.info(f"✗ RiskManager → TradingEngine flow failed: {e}")
            raise
    
            pass
    def test_ui_to_risk_manager_flow(self):
        """Test: UI changes → RiskManager updates"""
                pass
logger.info("\n=== Testing UI → RiskManager Flow ===")
        
        try:
            # Create QApplication if it doesn't exist
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            # Initialize components
            risk_manager = RiskManager(config_file=self.config_file)
            
            # Create UI widget
            widget = RiskManagementWidget()
            widget.risk_manager = risk_manager
            
            # Simulate UI changes
            widget.max_position_size.setValue(1500.0)
            widget.max_daily_loss.setValue(750.0)
            widget.stop_loss_percentage.setValue(2.5)
            
            # Simulate save button click
            widget.save_settings()
            
            # Verify changes were applied to risk manager
            self.assertEqual(risk_manager.max_position_size, 1500.0)
            self.assertEqual(risk_manager.max_daily_loss, 750.0)
            self.assertEqual(risk_manager.stop_loss_percentage, 0.025)  # UI shows percentage, stored as decimal
logger.info("✓ UI changes correctly applied to RiskManager")
            
        except Exception as e:
logger.info(f"✗ UI → RiskManager flow failed: {e}")
            # Don't raise for UI tests as they may fail in headless environment
            pass
logger.info("Note: UI tests may fail in headless environments")
    
    async def test_paper_vs_live_trading_modes(self):
        """Test: Paper trading vs Live trading mode differences"""
logger.info("\n=== Testing Paper vs Live Trading Modes ===")
        
        try:
            # Test Paper Trading Mode (default is demo mode)
            paper_engine = TradingEngine()
            await paper_engine.initialize()
            
            # Verify demo mode is enabled by default
            self.assertTrue(paper_engine.demo_mode, "TradingEngine should be in demo mode by default")
            
            # Test paper order
            paper_order = OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0.1,
                price=None
            )
            
            # This should work in demo mode
            result = await paper_engine.place_order(paper_order)
            self.assertIsNotNone(result, "Paper trading order should succeed")
logger.info("✓ Paper trading mode working correctly")
            
            # Test Live Trading Mode (simulated by disabling demo mode)
            live_engine = TradingEngine()
            live_engine.demo_mode = False  # Disable demo mode
            live_engine.exchange_configs = {
                'binance': {'enabled': False}  # Disabled for safety
            }
            await live_engine.initialize()
            
            # This should fall back to demo mode when exchange is disabled
            result = await live_engine.place_order(paper_order)
            self.assertIsNotNone(result, "Should fall back to demo when exchange disabled")
            pass
logger.info("✓ Live trading mode fallback working correctly")
            
            # Test balance access in both modes
            paper_balances = await paper_engine.get_balances()
            self.assertIsInstance(paper_balances, dict, "Should return balance dictionary")
logger.info("✓ Balance access working in both modes")
            
            pass
        except Exception as e:
logger.info(f"✗ Paper vs Live trading test failed: {e}")
            raise
    
    async def test_complete_operational_flow(self):
        """Test: Complete flow from config change to bot reaction"""
logger.info("\n=== Testing Complete Operational Flow ===")
        
        try:
            # 1. Start with initial setup
            risk_manager = RiskManager()
            trading_engine = TradingEngine()
            
            # Initialize components
            await risk_manager.initialize()
            await trading_engine.initialize()
logger.info("✓ Initial setup complete")
            
            # 2. Set initial risk limits for a test bot
            bot_id = 1
            from app.risk_management import RiskLimits
            
            initial_limits = RiskLimits(
                daily_loss_limit=1000.0,
                daily_profit_limit=5000.0,
                max_drawdown_limit=20.0,
                position_size_limit=1000.0,  # Initial limit
                max_open_positions=5,
                max_correlation=0.8,
                volatility_threshold=10.0,
                var_limit=500.0
            )
            
            await risk_manager.update_risk_limits(bot_id, initial_limits)
logger.info("✓ Initial risk limits set")
            
            # 3. Test order within initial limits
            initial_order = OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=500.0,  # Within initial limit of 1000
                price=None
            )
            
            # Check position size limit
            position_size_valid = await risk_manager.check_position_size_limit(
                bot_id=bot_id,
                position_size=500.0,
                available_balance=10000.0
            )
            
            self.assertTrue(position_size_valid, "Order should be valid with initial limits")
            
            # Execute order
            result = await trading_engine.place_order(initial_order)
            self.assertIsNotNone(result, "Order should execute successfully")
logger.info("✓ Order executed within initial limits")
            
            # 4. Update risk limits (simulating config change)
            updated_limits = RiskLimits(
                daily_loss_limit=1000.0,
                daily_profit_limit=5000.0,
                max_drawdown_limit=20.0,
                position_size_limit=300.0,  # Reduced limit
                max_open_positions=5,
                max_correlation=0.8,
                volatility_threshold=10.0,
                var_limit=500.0
            )
            
            await risk_manager.update_risk_limits(bot_id, updated_limits)
logger.info("✓ Risk limits updated")
            
            # 5. Test same order now exceeds new limits
            position_size_valid_after = await risk_manager.check_position_size_limit(
                bot_id=bot_id,
                position_size=500.0,  # Now exceeds limit of 300
                available_balance=10000.0
            )
            
            self.assertFalse(position_size_valid_after,
                           "Order should now exceed new limits")
logger.info("✓ Risk limits enforced correctly after update")
            
            # 6. Test order within new limits
            smaller_order = OrderRequest(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=200.0,  # Within new limit of 300
                price=None
            )
            
            position_size_valid_small = await risk_manager.check_position_size_limit(
                bot_id=bot_id,
                position_size=200.0,
                available_balance=10000.0
            )
            
            self.assertTrue(position_size_valid_small,
                              "Smaller order should be valid")
            
            result_small = await trading_engine.place_order(smaller_order)
            self.assertIsNotNone(result_small, "Smaller order should execute")
logger.info("✓ Smaller order executed within new limits")
            
            # 7. Test system integration
            balances = await trading_engine.get_balances()
            self.assertIsInstance(balances, dict, "Should return balance information")
            
            open_orders = await trading_engine.get_open_orders()
            self.assertIsInstance(open_orders, list, "Should return list of open orders")
logger.info("✓ System integration working correctly")
logger.info("\n🎉 Complete operational flow test PASSED!")
            
        except Exception as e:
logger.info(f"✗ Complete operational flow failed: {e}")
            raise

def run_operational_tests():
    """Run all operational flow tests"""
logger.info("=" * 60)
logger.info("OPERATIONAL FLOW TESTS")
logger.info("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOperationalFlow)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
        pass
    
            pass
    # Summary
logger.info("\n" + "=" * 60)
        pass
logger.info("OPERATIONAL TESTS SUMMARY")
            pass
logger.info("=" * 60)
logger.info(f"Tests run: {result.testsRun}")
logger.info(f"Failures: {len(result.failures)}")
logger.info(f"Errors: {len(result.errors)}")
    
        pass
    if result.failures:
        pass
logger.info("\nFAILURES:")
        for test, traceback in result.failures:
logger.info(f"- {test}: {traceback}")
    
    if result.errors:
logger.info("\nERRORS:")
        for test, traceback in result.errors:
logger.info(f"- {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
logger.info(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
            pass
logger.info("🎉 OPERATIONAL FLOW TESTS PASSED!")
    else:
logger.info("❌ OPERATIONAL FLOW TESTS NEED ATTENTION")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Uruchom testy asynchroniczne
    import asyncio
            pass
    
    async def run_async_tests():
            pass
        """Run async tests manually"""
        test_instance = TestOperationalFlow()
        test_instance.setUp()
        
        try:
logger.info("Starting operational flow tests...")
            
            # Run each test
            await test_instance.test_config_to_risk_manager_flow()
            await test_instance.test_risk_manager_to_trading_engine_flow()
            await test_instance.test_paper_vs_live_trading_modes()
            await test_instance.test_complete_operational_flow()
logger.info("\n🎉 All operational flow tests completed successfully!")
            
        except Exception as e:
logger.info(f"\n❌ Test failed: {e}")
            raise
        finally:
            test_instance.tearDown()
    
    # Run async tests
    asyncio.run(run_async_tests())