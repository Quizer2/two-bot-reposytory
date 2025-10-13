#!/usr/bin/env python3
"""
Debug script to test ConfigManager production_mode reading
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import ConfigManager
import logging
logger = logging.getLogger(__name__)

def main():
logger.info("=== Debug ConfigManager ===")
    
    # Initialize ConfigManager
    config = ConfigManager()
logger.info("\n1. Testing get_setting('app', 'production_mode', False)")
    result = config.get_setting('app', 'production_mode', False)
logger.info(f"Result: {result}")
logger.info("\n2. Getting full app config")
    app_config = config.get_app_config()
logger.info(f"App config keys: {list(app_config.keys()) if isinstance(app_config, dict) else 'not dict'}")
    
    if isinstance(app_config, dict) and 'app' in app_config:
        pass
logger.info(f"App section: {app_config['app']}")
            pass
        if 'production_mode' in app_config['app']:
logger.info(f"production_mode in app section: {app_config['app']['production_mode']}")
logger.info("\n=== End Debug ===")
    pass

if __name__ == "__main__":
    main()