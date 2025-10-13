from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

from analytics.performance_metrics import summarize_equity
from utils.event_bus import EventTypes, get_event_bus
from utils.helpers import schedule_coro_safely

logger = logging.getLogger(__name__)


class AIBotDataProvider:
    """Aggregate live market, risk and strategy information for the AI bot.

    The provider is responsible for collecting real-time market data, risk
    metrics and historical analytics so that the AI trading bot as well as the
    dashboard widgets receive a comprehensive dataset without needing to query
    every subsystem directly.
    """

    def __init__(self, integrated_data_manager=None):
        self.integrated_data_manager = integrated_data_manager
        self.market_data_manager = getattr(integrated_data_manager, "market_data_manager", None)
        self.risk_manager = getattr(integrated_data_manager, "risk_manager", None)

        self.event_bus = get_event_bus()
        self._price_history: Dict[str, Deque[Tuple[datetime, float]]] = defaultdict(
            lambda: deque(maxlen=720)
        )
        self._last_snapshot: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()
        self._running = False
        self._background_task: Optional[asyncio.Task] = None
        self.update_interval = 5.0
        self._learning_metadata = self._load_learning_metadata()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def attach_integrated_manager(self, manager) -> None:
        self.integrated_data_manager = manager
        if manager:
            if getattr(manager, "market_data_manager", None):
                self.market_data_manager = manager.market_data_manager
            if getattr(manager, "risk_manager", None):
                self.risk_manager = manager.risk_manager

    def set_market_data_manager(self, market_data_manager) -> None:
        self.market_data_manager = market_data_manager

    def set_risk_manager(self, risk_manager) -> None:
        self.risk_manager = risk_manager

    def start_background_updates(self, interval: float = 5.0) -> None:
        self.update_interval = max(1.0, float(interval))
        if self._running:
            return
        self._running = True

        async def _loop() -> None:
            try:
                await self._emit_snapshot()
                while self._running:
                    await asyncio.sleep(self.update_interval)
                    await self._emit_snapshot()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AI data provider background loop crashed")

        task = schedule_coro_safely(_loop, run_in_thread_if_no_loop=False)
        if isinstance(task, asyncio.Task):
            self._background_task = task
        else:
            self._background_task = None

    async def stop_background_updates(self) -> None:
        self._running = False
        task = self._background_task
        self._background_task = None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.debug("Ignoring error while stopping AI data provider", exc_info=True)

    async def manual_refresh(self, symbols: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        return await self._emit_snapshot(symbols=symbols)

    # ------------------------------------------------------------------
    # Snapshot accessors
    # ------------------------------------------------------------------
    def get_last_snapshot(self) -> Optional[Dict[str, Any]]:
        return self._last_snapshot

    def get_price_history(self, symbol: str, limit: int = 240) -> List[Tuple[datetime, float]]:
        history = list(self._price_history.get(symbol, []))
        if limit > 0:
            return history[-limit:]
        return history

    # ------------------------------------------------------------------
    # Internal snapshot construction
    # ------------------------------------------------------------------
    async def _emit_snapshot(
        self,
        symbols: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        snapshot = await self.collect_snapshot(symbols=symbols)
        if snapshot:
            try:
                if self.integrated_data_manager is not None:
                    await self.integrated_data_manager._notify_ui_callbacks("ai_snapshot", snapshot)
            except Exception:
                logger.exception("Failed to notify UI about AI snapshot")
            try:
                self.event_bus.publish(EventTypes.AI_SNAPSHOT_READY, snapshot)
            except Exception:
                logger.debug("Publishing AI snapshot event failed", exc_info=True)
        return snapshot

    async def collect_snapshot(
        self,
        symbols: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            resolved_symbols = list(symbols or self._resolve_symbols())
            bot_payload = await self._fetch_bot_payload()
            bot_entries = bot_payload.get("bots", [])

            market_overview = await self._gather_market_overview(resolved_symbols)
            order_books, candles = await self._gather_depth_and_candles(resolved_symbols)
            price_spikes = self._detect_price_spikes(resolved_symbols)
            trend_map = {
                symbol: self._calculate_trend(self._select_candles(symbol, candles))
                for symbol in resolved_symbols
            }

            risk_metrics = await self._gather_risk_metrics(bot_entries)
            correlations = self._compute_correlations(resolved_symbols)
            strategy_catalog = self._collect_strategy_catalog()
            recommendations = self._build_recommendations(
                bot_entries, risk_metrics, trend_map, price_spikes
            )
            technicals = self._build_technical_snapshots(
                resolved_symbols, candles, trend_map
            )
            feature_matrix = self._build_feature_matrix(
                bot_entries,
                risk_metrics,
                market_overview,
                technicals,
                recommendations,
                strategy_catalog,
            )
            learning_summary = self._build_learning_summary(resolved_symbols)
            sentiment = self._compute_sentiment(market_overview)
            risk_reports = await self._collect_risk_reports(bot_entries)

            snapshot = {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "symbols": resolved_symbols,
                "market_overview": market_overview,
                "price_spikes": price_spikes,
                "order_books": order_books,
                "candles": {
                    symbol: [self._serialise_candle(c) for c in self._select_candles(symbol, candles)]
                    for symbol in resolved_symbols
                },
                "risk_metrics": risk_metrics,
                "strategy_recommendations": recommendations,
                "learning": learning_summary,
                "market_sentiment": sentiment,
                "correlations": correlations,
                "bot_overview": bot_entries,
                "technical_indicators": technicals,
                "feature_matrix": feature_matrix,
                "strategy_catalog": strategy_catalog,
                "risk_reports": risk_reports,
            }

            self._last_snapshot = snapshot
            return snapshot

    # ------------------------------------------------------------------
    # Data gathering helpers
    # ------------------------------------------------------------------
    async def _gather_market_overview(self, symbols: List[str]) -> List[Dict[str, Any]]:
        if not self.market_data_manager or not symbols:
            return []

        tasks = [self.market_data_manager.get_current_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        overview: List[Dict[str, Any]] = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception) or result is None:
                logger.debug("Skipping price snapshot for %s due to error: %s", symbol, result)
                continue
            price = getattr(result, "price", None)
            timestamp = getattr(result, "timestamp", datetime.utcnow())
            self._append_price_history(symbol, float(price or 0.0), timestamp)
            overview.append(
                {
                    "symbol": symbol,
                    "price": float(getattr(result, "price", 0.0)),
                    "bid": float(getattr(result, "bid", 0.0)),
                    "ask": float(getattr(result, "ask", 0.0)),
                    "volume_24h": float(getattr(result, "volume_24h", 0.0)),
                    "change_24h": float(getattr(result, "change_24h", 0.0)),
                    "change_24h_percent": float(getattr(result, "change_24h_percent", 0.0)),
                    "timestamp": timestamp.isoformat(),
                }
            )
        return overview

    async def _gather_depth_and_candles(
        self,
        symbols: List[str],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        order_books: List[Dict[str, Any]] = []
        candle_map: Dict[str, List[Dict[str, Any]]] = {}

        if not self.market_data_manager:
            return order_books, candle_map

        depth_symbols = symbols[: min(3, len(symbols))]
        for symbol in depth_symbols:
            try:
                orderbook = await self.market_data_manager.get_orderbook(symbol, depth=10)
            except Exception as exc:
                logger.debug("Orderbook fetch failed for %s: %s", symbol, exc)
                orderbook = None
            if orderbook:
                order_books.append(
                    {
                        "symbol": symbol,
                        "bids": [
                            {"price": float(price), "quantity": float(qty)}
                            for price, qty in list(getattr(orderbook, "bids", []))[:5]
                        ],
                        "asks": [
                            {"price": float(price), "quantity": float(qty)}
                            for price, qty in list(getattr(orderbook, "asks", []))[:5]
                        ],
                        "timestamp": getattr(orderbook, "timestamp", datetime.utcnow()).isoformat(),
                    }
                )

        candle_symbols = symbols[: min(4, len(symbols))]
        for symbol in candle_symbols:
            try:
                candles = await self.market_data_manager.fetch_candles(symbol, timeframe="1m", limit=90)
            except Exception as exc:
                logger.debug("Candle fetch failed for %s: %s", symbol, exc)
                candles = []
            candle_map[symbol] = candles or []
        return order_books, candle_map

    async def _gather_risk_metrics(self, bot_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        risk_manager = self._resolve_risk_manager()
        metrics_list: List[Dict[str, Any]] = []
        historical = self._learning_metadata.get("bots", {})

        for bot in bot_entries:
            bot_id = str(bot.get("id") or bot.get("bot_id") or bot.get("name") or "")
            if not bot_id:
                continue

            metrics: Optional[Dict[str, Any]] = None
            if risk_manager is not None:
                try:
                    numeric_id = self._safe_int(bot.get("id") or bot.get("bot_id"))
                    if numeric_id is not None and hasattr(risk_manager, "get_risk_metrics"):
                        result = await risk_manager.get_risk_metrics(numeric_id)
                        if result is not None:
                            if isinstance(result, dict):
                                metrics = dict(result)
                            elif is_dataclass(result):
                                metrics = asdict(result)
                            elif hasattr(result, "to_dict"):
                                metrics = result.to_dict()
                except Exception as exc:
                    logger.debug("Risk metrics fetch failed for bot %s: %s", bot_id, exc)

            if metrics is None:
                metrics = dict(historical.get(bot_id, {}))

            risk_level = self._determine_risk_level(metrics)
            metrics_list.append(
                {
                    "bot_id": bot_id,
                    "name": bot.get("name") or bot_id,
                    "symbol": bot.get("symbol") or bot.get("pair"),
                    "risk_level": risk_level,
                    **(metrics or {}),
                }
            )
        return metrics_list

    def _build_recommendations(
        self,
        bot_entries: List[Dict[str, Any]],
        risk_metrics: List[Dict[str, Any]],
        trend_map: Dict[str, Dict[str, Any]],
        price_spikes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []
        metrics_map = {entry["bot_id"]: entry for entry in risk_metrics}
        spikes_map = {entry["symbol"]: entry for entry in price_spikes}

        for bot in bot_entries:
            bot_id = str(bot.get("id") or bot.get("bot_id") or bot.get("name") or "")
            if not bot_id:
                continue
            symbol = bot.get("symbol") or bot.get("pair") or ""
            metrics = metrics_map.get(bot_id, {})
            trend_info = trend_map.get(symbol, {"trend": "unknown", "change_percent": 0.0})
            risk_level = metrics.get("risk_level", "unknown")

            base_confidence = 0.55
            recommendation_parts: List[str] = []

            trend = trend_info.get("trend", "unknown")
            change = trend_info.get("change_percent", 0.0)
            if trend == "bullish":
                recommendation_parts.append("Silny trend wzrostowy – można zwiększyć ekspozycję lub stosować strategie momentum.")
                base_confidence += 0.15
            elif trend == "bearish":
                recommendation_parts.append("Trend spadkowy – rozważ hedging, krótkie pozycje lub zmniejszenie ekspozycji.")
                base_confidence -= 0.2
            else:
                recommendation_parts.append("Rynek boczny – najlepiej sprawdzą się strategie grid/market-neutral.")

            spike = spikes_map.get(symbol)
            if spike:
                direction = spike.get("direction", "")
                spike_change = spike.get("change_percent", 0.0)
                recommendation_parts.append(
                    f"Wykryto iglicę {spike_change:.2f}% ({direction}). Reaguj dynamicznie na zwiększoną zmienność."
                )
                base_confidence -= 0.05

            if risk_level in ("high", "critical"):
                recommendation_parts.append("Poziom ryzyka wysoki – dopilnuj limitów i przygotuj scenariusze awaryjne.")
                base_confidence -= 0.2
            elif risk_level == "low":
                base_confidence += 0.1

            if change and abs(change) < 0.3:
                base_confidence -= 0.05

            recommendations.append(
                {
                    "bot_id": bot_id,
                    "bot_name": bot.get("name") or bot_id,
                    "symbol": symbol,
                    "risk_level": risk_level,
                    "trend": trend,
                    "trend_change_percent": change,
                    "confidence": max(0.0, min(1.0, round(base_confidence, 2))),
                    "recommendation": " ".join(recommendation_parts).strip(),
                }
            )
        return recommendations

    def _build_technical_snapshots(
        self,
        symbols: List[str],
        candle_map: Dict[str, List[Dict[str, Any]]],
        trend_map: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        snapshots: Dict[str, Dict[str, Any]] = {}
        for symbol in symbols:
            candles = self._select_candles(symbol, candle_map)
            trend_info = trend_map.get(symbol, {"trend": "unknown", "change_percent": 0.0})
            snapshots[self._normalise_symbol(symbol)] = self._compute_indicator_set(
                candles, trend_info
            )
        return snapshots

    def _collect_strategy_catalog(self) -> List[Dict[str, Any]]:
        manager = self.integrated_data_manager
        if manager is None:
            return []
        try:
            if hasattr(manager, "get_strategy_catalog"):
                return manager.get_strategy_catalog() or []
            if hasattr(manager, "strategy_engine") and hasattr(
                manager.strategy_engine, "describe_strategies"
            ):
                return manager.strategy_engine.describe_strategies() or []
        except Exception as exc:
            logger.debug("Strategy catalog fetch failed: %s", exc)
        return []

    async def _collect_risk_reports(
        self, bot_entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        risk_manager = self._resolve_risk_manager()
        if risk_manager is None or not hasattr(risk_manager, "get_risk_report"):
            return []

        reports: List[Dict[str, Any]] = []
        for bot in bot_entries:
            numeric_id = self._safe_int(bot.get("id") or bot.get("bot_id"))
            if numeric_id is None:
                continue
            try:
                report = await risk_manager.get_risk_report(numeric_id)
            except Exception as exc:
                logger.debug("Risk report fetch failed for bot %s: %s", numeric_id, exc)
                continue
            if not isinstance(report, dict):
                continue
            reports.append(self._normalise_risk_report(numeric_id, report))
        return reports

    def _build_feature_matrix(
        self,
        bot_entries: List[Dict[str, Any]],
        risk_metrics: List[Dict[str, Any]],
        market_overview: List[Dict[str, Any]],
        technicals: Dict[str, Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        strategy_catalog: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not bot_entries:
            return []

        risk_map = {entry.get("bot_id"): entry for entry in risk_metrics}
        rec_map = {entry.get("bot_id"): entry for entry in recommendations}
        strategy_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entry in strategy_catalog or []:
            key = str(entry.get("bot_id") or entry.get("strategy_id") or "")
            if key:
                strategy_map[key].append(entry)

        market_map = self._build_symbol_map(market_overview)
        features: List[Dict[str, Any]] = []

        for bot in bot_entries:
            bot_id = str(bot.get("id") or bot.get("bot_id") or bot.get("name") or "")
            if not bot_id:
                continue
            symbol = bot.get("symbol") or bot.get("pair") or ""
            symbol_key = self._normalise_symbol(symbol)

            indicator = self._lookup_symbol(symbol_key, technicals) or {}
            market_snapshot = self._lookup_symbol(symbol_key, market_map) or {}
            risk_snapshot = risk_map.get(bot_id, {})
            recommendation = rec_map.get(bot_id, {})
            strategies = strategy_map.get(bot_id, [])

            feature_entry = {
                "bot_id": bot_id,
                "name": bot.get("name") or bot_id,
                "symbol": symbol or market_snapshot.get("symbol"),
                "strategy": bot.get("strategy"),
                "price": self._safe_float(market_snapshot.get("price")),
                "change_24h_percent": self._safe_float(
                    market_snapshot.get("change_24h_percent")
                ),
                "volume_24h": self._safe_float(market_snapshot.get("volume_24h")),
                "rsi": self._safe_float(indicator.get("rsi")),
                "atr": self._safe_float(indicator.get("atr")),
                "ema_fast": self._safe_float(indicator.get("ema_fast")),
                "ema_slow": self._safe_float(indicator.get("ema_slow")),
                "macd": self._safe_float(indicator.get("macd")),
                "macd_signal": self._safe_float(indicator.get("macd_signal")),
                "macd_hist": self._safe_float(indicator.get("macd_hist")),
                "volatility": self._safe_float(indicator.get("volatility")),
                "trend": indicator.get("trend"),
                "trend_strength": self._safe_float(indicator.get("trend_strength")),
                "risk_level": risk_snapshot.get("risk_level", "unknown"),
                "max_drawdown": self._safe_float(risk_snapshot.get("max_drawdown")),
                "var_95": self._safe_float(risk_snapshot.get("var_95")),
                "exposure": self._safe_float(risk_snapshot.get("exposure")),
                "recommendation": recommendation.get("recommendation"),
                "strategy_confidence": self._safe_float(
                    recommendation.get("confidence")
                ),
                "strategy_summary": [
                    self._summarise_strategy(entry) for entry in strategies
                ],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            features.append(feature_entry)

        return features

    def _build_learning_summary(self, symbols: List[str]) -> Dict[str, Any]:
        metadata = self._learning_metadata
        datasets = metadata.get("bots", {})
        dataset_count = len(datasets)
        feature_count = 0
        for entry in datasets.values():
            feature_count = max(feature_count, len(entry.keys()))

        primary_symbol = symbols[0] if symbols else None
        history = self.get_price_history(primary_symbol, limit=240) if primary_symbol else []
        equity_curve = self._build_equity_curve(history)
        summary = summarize_equity(equity_curve) if equity_curve else {}

        return {
            "dataset_count": dataset_count,
            "feature_count": feature_count,
            "sources": list(datasets.keys()),
            "last_training": metadata.get("last_training"),
            "equity_curve": equity_curve,
            "equity_summary": summary,
        }

    def _compute_sentiment(self, overview: List[Dict[str, Any]]) -> str:
        if not overview:
            return "unknown"
        changes = [entry.get("change_24h_percent", 0.0) for entry in overview]
        avg_change = mean(changes) if changes else 0.0
        if avg_change > 1.0:
            return "bullish"
        if avg_change < -1.0:
            return "bearish"
        return "neutral"

    def _detect_price_spikes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        spikes: List[Dict[str, Any]] = []
        for symbol in symbols:
            history = list(self._price_history.get(symbol, []))
            if len(history) < 5:
                continue
            prices = [price for _, price in history]
            baseline = mean(prices[:-1])
            current = prices[-1]
            if baseline == 0:
                continue
            change_percent = (current - baseline) / baseline * 100.0
            if abs(change_percent) >= 1.0:
                severity = "medium" if abs(change_percent) < 3.0 else "high"
                direction = "up" if change_percent > 0 else "down"
                spikes.append(
                    {
                        "symbol": symbol,
                        "change_percent": round(change_percent, 2),
                        "severity": severity,
                        "direction": direction,
                        "observations": len(history),
                    }
                )
        return spikes

    def _compute_correlations(self, symbols: List[str]) -> List[Dict[str, Any]]:
        pairs: List[Dict[str, Any]] = []
        for idx, base_symbol in enumerate(symbols):
            base_history = self.get_price_history(base_symbol, limit=240)
            if len(base_history) < 10:
                continue
            base_prices = [price for _, price in base_history]
            for other_symbol in symbols[idx + 1 :]:
                other_history = self.get_price_history(other_symbol, limit=240)
                if len(other_history) < 10:
                    continue
                other_prices = [price for _, price in other_history]
                length = min(len(base_prices), len(other_prices))
                if length < 10:
                    continue
                corr = self._pearson(base_prices[-length:], other_prices[-length:])
                pairs.append(
                    {
                        "pair": f"{base_symbol}-{other_symbol}",
                        "correlation": round(corr, 4),
                        "sample_size": length,
                    }
                )
        return pairs

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    async def _fetch_bot_payload(self) -> Dict[str, Any]:
        if not self.integrated_data_manager:
            return {"bots": []}
        try:
            payload = await self.integrated_data_manager.get_bot_management_data()
        except Exception as exc:
            logger.debug("Bot payload fetch failed: %s", exc)
            payload = {}
        bots = payload.get("bots", []) if isinstance(payload, dict) else []
        normalised = [self._normalise_bot_entry(entry) for entry in bots]
        payload["bots"] = normalised
        return payload

    def _append_price_history(self, symbol: str, price: float, timestamp: datetime) -> None:
        if not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()
        self._price_history[symbol].append((timestamp, float(price)))

    def _select_candles(
        self, symbol: str, candle_map: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        if not candle_map:
            return []
        if symbol in candle_map:
            return candle_map[symbol]
        normalised = self._normalise_symbol(symbol)
        if normalised in candle_map:
            return candle_map[normalised]
        for key, value in candle_map.items():
            if self._normalise_symbol(key) == normalised:
                return value
        return []

    def _normalise_bot_entry(self, entry: Any) -> Dict[str, Any]:
        if isinstance(entry, dict):
            result = dict(entry)
        elif is_dataclass(entry):
            result = asdict(entry)
        else:
            result = {
                "id": getattr(entry, "id", None),
                "name": getattr(entry, "name", None),
                "status": getattr(entry, "status", None),
                "active": getattr(entry, "active", None),
                "profit": getattr(entry, "profit", getattr(entry, "pnl", 0.0)),
                "trades_count": getattr(entry, "trades_count", None),
                "symbol": getattr(entry, "symbol", None),
                "strategy": getattr(entry, "strategy", None),
                "created_at": getattr(entry, "created_at", None),
            }
        if isinstance(result.get("created_at"), datetime):
            result["created_at"] = result["created_at"].isoformat()
        return result

    def _calculate_trend(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(candles) < 5:
            return {"trend": "unknown", "change_percent": 0.0, "volatility": 0.0}
        closes = [float(candle.get("close", 0.0)) for candle in candles]
        start = closes[0]
        end = closes[-1]
        change_percent = ((end - start) / start * 100.0) if start else 0.0
        window = closes[-20:]
        volatility = pstdev(window) if len(window) > 1 else 0.0
        if change_percent > 0.8:
            trend = "bullish"
        elif change_percent < -0.8:
            trend = "bearish"
        else:
            trend = "sideways"
        return {
            "trend": trend,
            "change_percent": round(change_percent, 2),
            "volatility": round(volatility, 4),
        }

    def _determine_risk_level(self, metrics: Optional[Dict[str, Any]]) -> str:
        if not metrics:
            return "unknown"
        drawdown = float(metrics.get("max_drawdown", metrics.get("total_drawdown", 0.0)))
        var_95 = float(metrics.get("var_95", 0.0))
        exposure = float(metrics.get("exposure", metrics.get("current_exposure", 0.0)))
        if drawdown > 25 or var_95 > 1200 or exposure > 0.75:
            return "critical"
        if drawdown > 18 or var_95 > 900 or exposure > 0.65:
            return "high"
        if drawdown > 10 or var_95 > 500 or exposure > 0.5:
            return "medium"
        return "low"

    def _normalise_symbol(self, symbol: str) -> str:
        if not symbol:
            return ""
        cleaned = symbol.replace("/", "").replace("-", "").upper()
        return cleaned

    def _build_symbol_map(self, entries: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        mapping: Dict[str, Dict[str, Any]] = {}
        for entry in entries or []:
            symbol = entry.get("symbol")
            if not symbol:
                continue
            mapping[self._normalise_symbol(symbol)] = entry
            mapping[symbol] = entry
        return mapping

    def _lookup_symbol(self, symbol: str, mapping: Dict[str, Any]) -> Optional[Any]:
        if not mapping or not symbol:
            return None
        if symbol in mapping:
            return mapping[symbol]
        normalised = self._normalise_symbol(symbol)
        if normalised in mapping:
            return mapping[normalised]
        for key, value in mapping.items():
            if self._normalise_symbol(str(key)) == normalised:
                return value
        return None

    def _compute_indicator_set(
        self,
        candles: List[Dict[str, Any]],
        trend_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not candles:
            return {
                "trend": trend_info.get("trend", "unknown"),
                "trend_strength": trend_info.get("change_percent", 0.0),
                "volatility": 0.0,
            }

        closes = [float(c.get("close", 0.0)) for c in candles if c.get("close") is not None]
        highs = [float(c.get("high", c.get("close", 0.0))) for c in candles]
        lows = [float(c.get("low", c.get("close", 0.0))) for c in candles]
        volumes = [float(c.get("volume", 0.0)) for c in candles]

        ema_fast = self._ema_last(closes, 12)
        ema_slow = self._ema_last(closes, 26)
        macd_line, macd_signal, macd_hist = self._compute_macd(closes)
        rsi = self._compute_rsi(closes)
        atr = self._compute_atr(highs, lows, closes)
        volatility = pstdev(closes[-30:]) if len(closes) >= 2 else 0.0

        trend_strength = trend_info.get("change_percent", 0.0)
        return {
            "ema_fast": self._safe_float(ema_fast),
            "ema_slow": self._safe_float(ema_slow),
            "macd": self._safe_float(macd_line),
            "macd_signal": self._safe_float(macd_signal),
            "macd_hist": self._safe_float(macd_hist),
            "rsi": self._safe_float(rsi),
            "atr": self._safe_float(atr),
            "volatility": round(float(volatility), 6),
            "trend": trend_info.get("trend", "unknown"),
            "trend_strength": self._safe_float(trend_strength),
            "volume": self._safe_float(volumes[-1] if volumes else None),
        }

    def _ema_last(self, values: List[float], period: int) -> Optional[float]:
        if len(values) < period or period <= 0:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for price in values[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def _compute_macd(
        self, values: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if len(values) < slow:
            return None, None, None
        ema_fast = self._ema_last(values, fast)
        ema_slow = self._ema_last(values, slow)
        if ema_fast is None or ema_slow is None:
            return None, None, None
        macd_line = ema_fast - ema_slow
        macd_series: List[float] = []
        for idx in range(slow - 1, len(values)):
            window = values[: idx + 1]
            fast_val = self._ema_last(window, fast)
            slow_val = self._ema_last(window, slow)
            if fast_val is None or slow_val is None:
                continue
            macd_series.append(fast_val - slow_val)
        macd_signal = self._ema_last(macd_series, signal_period) if macd_series else None
        macd_hist = macd_line - macd_signal if macd_signal is not None else None
        return macd_line, macd_signal, macd_hist

    def _compute_rsi(self, values: List[float], period: int = 14) -> Optional[float]:
        if len(values) <= period:
            return None
        gains: List[float] = []
        losses: List[float] = []
        for prev, current in zip(values[:-1], values[1:]):
            change = current - prev
            if change >= 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))
        avg_gain = mean(gains[-period:]) if len(gains) >= period else mean(gains) if gains else 0.0
        avg_loss = mean(losses[-period:]) if len(losses) >= period else mean(losses) if losses else 0.0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss if avg_loss else 0.0
        return 100 - (100 / (1 + rs))

    def _compute_atr(
        self, highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        if len(highs) < period + 1:
            return None
        true_ranges: List[float] = []
        for idx in range(1, len(highs)):
            tr = max(
                highs[idx] - lows[idx],
                abs(highs[idx] - closes[idx - 1]),
                abs(lows[idx] - closes[idx - 1]),
            )
            true_ranges.append(tr)
        if len(true_ranges) < period:
            return None
        return mean(true_ranges[-period:])

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    def _summarise_strategy(self, entry: Any) -> Dict[str, Any]:
        if entry is None:
            return {}
        if isinstance(entry, dict):
            summary = dict(entry)
        elif is_dataclass(entry):
            summary = asdict(entry)
        elif hasattr(entry, "to_dict"):
            summary = entry.to_dict()
        else:
            summary = {
                "strategy_id": getattr(entry, "strategy_id", None),
                "name": getattr(entry, "name", None),
                "active": getattr(entry, "active", None),
                "bot_id": getattr(entry, "bot_id", None),
            }
        last_update = summary.get("last_update")
        if isinstance(last_update, datetime):
            summary["last_update"] = last_update.isoformat()
        return summary

    def _normalise_risk_report(
        self, bot_id: int, report: Dict[str, Any]
    ) -> Dict[str, Any]:
        payload = dict(report)
        payload.setdefault("bot_id", bot_id)
        for key in ("limits", "metrics"):
            value = payload.get(key)
            if hasattr(value, "to_dict"):
                payload[key] = value.to_dict()
            elif is_dataclass(value):
                payload[key] = asdict(value)
        events = []
        for event in payload.get("recent_events", []) or []:
            if isinstance(event, dict):
                events.append(event)
            elif hasattr(event, "to_dict"):
                events.append(event.to_dict())
            elif is_dataclass(event):
                events.append(asdict(event))
        payload["recent_events"] = events
        return payload

    def _build_equity_curve(self, history: List[Tuple[datetime, float]]) -> List[float]:
        if not history:
            return []
        baseline = history[0][1] or 1.0
        curve: List[float] = []
        for _, price in history:
            curve.append(round(1000.0 * (price / baseline), 2))
        return curve

    def _pearson(self, series_a: List[float], series_b: List[float]) -> float:
        if len(series_a) != len(series_b) or len(series_a) < 2:
            return 0.0
        mean_a = mean(series_a)
        mean_b = mean(series_b)
        diff_a = [a - mean_a for a in series_a]
        diff_b = [b - mean_b for b in series_b]
        denominator = (sum(x * x for x in diff_a) * sum(y * y for y in diff_b)) ** 0.5
        if denominator == 0:
            return 0.0
        numerator = sum(x * y for x, y in zip(diff_a, diff_b))
        return max(-1.0, min(1.0, numerator / denominator))

    def _resolve_symbols(self) -> List[str]:
        if self.market_data_manager and getattr(self.market_data_manager, "tracked_symbols", None):
            return list(self.market_data_manager.tracked_symbols)
        if self._last_snapshot:
            return list(self._last_snapshot.get("symbols", []))
        return ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

    def _resolve_risk_manager(self):
        if self.risk_manager:
            return self.risk_manager
        if self.integrated_data_manager and getattr(self.integrated_data_manager, "risk_manager", None):
            return self.integrated_data_manager.risk_manager
        return None

    def _load_learning_metadata(self) -> Dict[str, Any]:
        default = {"bots": {}, "last_training": None}
        path = Path("analytics/historical_metrics.json")
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                default.update(data)
        except Exception as exc:
            logger.debug("Unable to load historical metrics snapshot: %s", exc)
        return default

    def _serialise_candle(self, candle: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(candle)
        ts = payload.get("timestamp")
        if isinstance(ts, datetime):
            payload["timestamp"] = ts.isoformat()
        return payload

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(value)
        except Exception:
            return None


_provider: Optional[AIBotDataProvider] = None


def get_ai_bot_data_provider(integrated_data_manager=None) -> AIBotDataProvider:
    global _provider
    if _provider is None:
        _provider = AIBotDataProvider(integrated_data_manager)
    elif integrated_data_manager is not None:
        _provider.attach_integrated_manager(integrated_data_manager)
    return _provider


__all__ = ["AIBotDataProvider", "get_ai_bot_data_provider"]
