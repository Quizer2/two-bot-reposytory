"""Failsafe manager for safeguarding bots during unexpected shutdowns."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


class FailSafeManager:
    """Coordinates runtime snapshots and recovery routines for hard shutdowns."""

    def __init__(
        self,
        database_manager,
        bot_manager=None,
        trading_engine=None,
        notification_manager=None,
    ) -> None:
        self.db = database_manager
        self.bot_manager = bot_manager
        self.trading_engine = trading_engine
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._last_state: Dict[str, Any] = {}
        self._recovery_triggered = False

    async def initialize(self) -> bool:
        """Load previous state and mark the runtime as active."""

        if self.db is None:
            raise ValueError("FailSafeManager requires a database manager instance")

        try:
            state = await self.db.get_system_failover_state()
            if state:
                self._last_state = state
                if not state.get('clean_shutdown', True):
                    await self._handle_unclean_shutdown(state)

            await self.db.mark_clean_shutdown(False, status='running')
            self._initialized = True
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Failed to initialize FailSafeManager: %s", exc)
            return False

    async def record_snapshot(self, snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Persist the current runtime snapshot for crash recovery."""

        if not self._initialized:
            return self._last_state

        snapshot = snapshot or {}

        active_bot_ids = sorted(set(self._collect_active_bot_ids(snapshot)))
        open_orders = self._collect_open_orders(snapshot)
        context = dict(snapshot)
        context['active_bot_ids'] = active_bot_ids
        context['open_orders'] = open_orders
        context['last_snapshot'] = datetime.utcnow().isoformat()

        try:
            state = await self.db.upsert_system_failover_state(
                status=snapshot.get('status', 'running'),
                active_bots=len(active_bot_ids),
                open_orders=len(open_orders),
                context=context,
                clean_shutdown=False,
            )
            if state:
                self._last_state = state
            return self._last_state
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.warning("Failed to persist failsafe snapshot: %s", exc)
            return self._last_state

    async def mark_clean_shutdown(self) -> Dict[str, Any]:
        """Mark the last checkpoint as a clean shutdown."""

        try:
            state = await self.db.mark_clean_shutdown(True, status='stopped')
            if state:
                self._last_state = state
            return self._last_state
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Failed to mark clean shutdown: %s", exc)
            return self._last_state

    def get_last_state(self) -> Dict[str, Any]:
        return dict(self._last_state)

    def requires_operator_attention(self) -> bool:
        return not self._last_state.get('clean_shutdown', True) or self._recovery_triggered

    async def _handle_unclean_shutdown(self, state: Dict[str, Any]) -> None:
        self._recovery_triggered = True
        await self.db.record_system_failover_event('unclean_shutdown_detected', state)

        context = state.get('context') or {}
        active_ids: Iterable[Any] = context.get('active_bot_ids') or []

        for bot_id in active_ids:
            parsed_id: Optional[int] = None
            try:
                parsed_id = int(bot_id)
            except Exception:
                parsed_id = None

            if parsed_id is None:
                continue

            try:
                await self.db.update_bot_status(parsed_id, 'paused', "Recovery after unexpected shutdown")
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Failed to pause bot %s during recovery: %s", bot_id, exc)

        if self.bot_manager and hasattr(self.bot_manager, 'shutdown'):
            try:
                await self.bot_manager.shutdown(pause_only=True)  # type: ignore[arg-type]
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Bot manager shutdown during recovery failed: %s", exc)

        if self.trading_engine and hasattr(self.trading_engine, 'active_orders'):
            await self._cancel_runtime_orders()

        await self._notify_recovery_required(state)

    async def _cancel_runtime_orders(self) -> None:
        try:
            active_orders = getattr(self.trading_engine, 'active_orders', {}) or {}
        except Exception:
            active_orders = {}

        if not active_orders:
            return

        for order_id, order in list(active_orders.items()):
            try:
                symbol = getattr(order, 'symbol', None)
                await self.trading_engine.cancel_order(order_id, symbol)
            except Exception as exc:  # pragma: no cover - runtime safety
                self.logger.warning("Failed to cancel order %s during recovery: %s", order_id, exc)

    async def _notify_recovery_required(self, state: Dict[str, Any]) -> None:
        if not self.notification_manager or not hasattr(self.notification_manager, 'send_notification'):
            return

        try:
            from app.notifications import NotificationChannel, NotificationPriority, NotificationType
        except Exception:  # pragma: no cover - notifications optional
            NotificationChannel = NotificationPriority = NotificationType = None

        title = "Przywracanie po awarii zasilania"
        message = (
            "Wykryto poprzednie niepoprawne zamknięcie aplikacji. Wszystkie boty zostały"
            " oznaczone jako wstrzymane do czasu potwierdzenia operatora."
        )

        kwargs: Dict[str, Any] = {}
        if NotificationType:
            kwargs['notification_type'] = NotificationType.CRITICAL
        if NotificationPriority:
            kwargs['priority'] = NotificationPriority.URGENT
        if NotificationChannel:
            kwargs['channels'] = [NotificationChannel.DESKTOP]

        try:
            await self.notification_manager.send_notification(title, message, **kwargs)
        except Exception as exc:  # pragma: no cover - notification failure should not block recovery
            self.logger.warning("Notification dispatch failed during recovery: %s", exc)

        await self.db.record_system_failover_event('operator_notification_sent', state)

    def _collect_active_bot_ids(self, snapshot: Dict[str, Any]) -> List[str]:
        ids: List[str] = []
        provided = snapshot.get('active_bot_ids') or []
        ids.extend(str(item) for item in provided if item is not None)

        if self.bot_manager and hasattr(self.bot_manager, 'active_bots'):
            try:
                ids.extend(str(bot_id) for bot_id in getattr(self.bot_manager, 'active_bots').keys())
            except Exception:  # pragma: no cover - robustness
                pass

        return ids

    def _collect_open_orders(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        orders: List[Dict[str, Any]] = []
        provided = snapshot.get('open_orders') or []
        if isinstance(provided, list):
            orders.extend(provided)

        try:
            active_orders = getattr(self.trading_engine, 'active_orders', {}) or {}
        except Exception:
            active_orders = {}

        for order_id, order in active_orders.items():
            try:
                status = getattr(order, 'status', None)
                if hasattr(status, 'value'):
                    status = status.value
                orders.append(
                    {
                        'order_id': order_id,
                        'symbol': getattr(order, 'symbol', ''),
                        'status': status or 'unknown',
                        'quantity': getattr(order, 'quantity', None),
                    }
                )
            except Exception:  # pragma: no cover
                continue

        return orders


__all__ = ['FailSafeManager']

