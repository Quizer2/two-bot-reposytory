"""
Helper utilities for CryptoBotDesktop.
This file previously had broken try/except indentation; rebuilt safely.
"""

from __future__ import annotations

import json
import asyncio
import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime

try:
    import aiohttp
except Exception:
    aiohttp = None  # allow import without aiohttp for offline tests

# Add safe event loop helper
def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Return current running loop or create and set a new one on the main thread.
    Safe to call from synchronous context."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        # No running loop in this thread
        try:
            # Try policy's get_event_loop (may auto-create on main thread)
            loop = asyncio.get_event_loop()
            if loop is None:
                raise RuntimeError("No loop returned by get_event_loop")
            return loop
        except Exception:
            # Explicitly create and set a new loop
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
            except Exception:
                # If setting fails, just return the created loop
                pass
            return loop

def schedule_coro_safely(coro_or_factory: "asyncio.coroutines" , run_in_thread_if_no_loop: bool = True):
    """Unified helper to schedule an async coroutine safely.
    Accepts either a coroutine object or a zero-arg callable that returns a coroutine (factory).
    - If a running event loop exists in the current thread, schedule via loop.create_task and return the Task.
    - If no running loop exists:
      * when run_in_thread_if_no_loop is True: run the coroutine in a background daemon thread using asyncio.run() and return None
      * otherwise: do nothing and return None (and DO NOT create the coroutine to avoid warnings)
    This avoids 'coroutine was never awaited' warnings in sync contexts (e.g., tests).
    """
    def _get_coro():
        if callable(coro_or_factory) and not inspect.iscoroutine(coro_or_factory):
            return coro_or_factory()
        return coro_or_factory
    try:
        loop = asyncio.get_running_loop()
        coro = _get_coro()
        if not inspect.iscoroutine(coro):
            async def _async_wrapper():
                return coro

            coro = _async_wrapper()
        return loop.create_task(coro)
    except RuntimeError:
        # No running loop
        if run_in_thread_if_no_loop:
            import threading as _th
            def _runner():
                coro = _get_coro()
                if not inspect.iscoroutine(coro):
                    async def _async_wrapper():
                        return coro

                    coro = _async_wrapper()
                asyncio.run(coro)

            _th.Thread(target=_runner, daemon=True).start()
        return None
    except Exception:
        # Defensive: if anything unexpected happens, fall back to thread run to avoid dropped coroutines
        try:
            import threading as _th
            def _runner():
                coro = _get_coro()
                if not inspect.iscoroutine(coro):
                    async def _async_wrapper():
                        return coro

                    coro = _async_wrapper()
                asyncio.run(coro)

            _th.Thread(target=_runner, daemon=True).start()
        except Exception:
            pass
        return None

# Import ValidationHelper from core.data_manager
try:
    from core.data_manager import ValidationHelper
except ImportError:
    # Fallback ValidationHelper if core.data_manager is not available
    class ValidationHelper:
        @staticmethod
        def validate_trading_pair(pair):
            return isinstance(pair, str) and len(pair) > 0
        
        @staticmethod
        def validate_amount(amount):
            try:
                return float(amount) > 0
            except:
                return False
        
        @staticmethod
        def validate_percentage(percentage):
            try:
                val = float(percentage)
                return 0 <= val <= 100
            except:
                return False


class Helpers:
    @staticmethod
    def read_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        try:
            p = Path(file_path)
            if not p.exists():
                return None
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None


class CalculationHelper:
    """Helper class for financial calculations"""
    
    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """Calculate percentage change between two values"""
        try:
            if old_value == 0:
                return 0.0
            return ((new_value - old_value) / old_value) * 100
        except:
            return 0.0
    
    @staticmethod
    def calculate_profit_loss(entry_price: float, current_price: float, quantity: float) -> float:
        """Calculate profit/loss for a position"""
        try:
            return (current_price - entry_price) * quantity
        except:
            return 0.0
    
    @staticmethod
    def calculate_roi(initial_investment: float, current_value: float) -> float:
        """Calculate Return on Investment"""
        try:
            if initial_investment == 0:
                return 0.0
            return ((current_value - initial_investment) / initial_investment) * 100
        except:
            return 0.0
    
    @staticmethod
    def calculate_average(values: list) -> float:
        """Calculate average of a list of values"""
        try:
            if not values:
                return 0.0
            return sum(values) / len(values)
        except:
            return 0.0


class FormatHelper:
    """Helper class for formatting various data types"""
    
    @staticmethod
    def format_currency(value: float, currency: str = "USD") -> str:
        """Format currency value"""
        try:
            if currency == "USD":
                return f"${value:,.2f}"
            elif currency == "BTC":
                return f"{value:.8f} BTC"
            elif currency == "ETH":
                return f"{value:.6f} ETH"
            else:
                return f"{value:.4f} {currency}"
        except:
            return f"0.00 {currency}"
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage value"""
        try:
            return f"{value:.2f}%"
        except:
            return "0.00%"
    
    @staticmethod
    def format_number(value: float, decimals: int = 2) -> str:
        """Format number with specified decimals"""
        try:
            return f"{value:,.{decimals}f}"
        except:
            return "0.00"
    
    @staticmethod
    def format_datetime(dt: datetime) -> str:
        """Format datetime for display"""
        try:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "N/A"
    
    @staticmethod
    def format_time_ago(dt: datetime) -> str:
        """Format time as 'X minutes ago' etc."""
        try:
            now = datetime.now()
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hours ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        except:
            return "N/A"

    @staticmethod
    def write_json_file(file_path: Union[str, Path], data: Dict[str, Any]) -> bool:
        try:
            p = Path(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    @staticmethod
    async def http_json(url: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Minimal, safe HTTP JSON helper with robust exception handling."""
        if aiohttp is None:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(url, timeout=timeout) as resp:
                        try:
                            if resp.status == 200:
                                return await resp.json()
                            else:
                                return None
                        except Exception:
                            return None
                else:
                    async with session.post(url, json=payload or {}, timeout=timeout) as resp:
                        try:
                            if resp.status in (200, 201):
                                return await resp.json()
                            else:
                                return None
                        except Exception:
                            return None
        except Exception:
            return None
