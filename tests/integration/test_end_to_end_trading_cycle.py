import asyncio
from datetime import datetime

import pytest

from core.portfolio_manager import PortfolioManager, PortfolioData
from core.updated_risk_manager import UpdatedRiskManager, RiskCheckResult
from core.trading_engine import TradingEngine, OrderRequest, OrderSide, OrderType


class DummyPortfolioDataManager:
    def __init__(self) -> None:
        self.portfolio = PortfolioData(
            total_value=15000.0,
            available_balance=9000.0,
            invested_amount=6000.0,
            profit_loss=320.0,
            profit_loss_percent=4.8,
            assets=[
                {
                    "symbol": "BTC/USDT",
                    "amount": 0.25,
                    "value": 6250.0,
                    "change_24h": 1.5,
                },
                {
                    "symbol": "ETH/USDT",
                    "amount": 3.0,
                    "value": 5400.0,
                    "change_24h": 2.1,
                },
            ],
            last_updated=datetime.utcnow(),
        )

    async def get_portfolio_data(self):
        return self.portfolio


class RiskPortfolioFacade:
    def __init__(self, portfolio_manager: PortfolioManager) -> None:
        self._portfolio_manager = portfolio_manager

    async def get_portfolio_summary(self):
        return await self._portfolio_manager.get_portfolio_summary()

    async def get_portfolio_positions(self):
        summary = await self._portfolio_manager.get_portfolio_summary()
        return summary.positions if summary else []


@pytest.mark.asyncio
async def test_simulated_trading_cycle_updates_portfolio(monkeypatch):
    dummy_data = DummyPortfolioDataManager()
    portfolio_manager = PortfolioManager(data_manager=dummy_data)

    risk_facade = RiskPortfolioFacade(portfolio_manager)
    risk_manager = UpdatedRiskManager(data_manager=risk_facade)

    engine = TradingEngine()

    order_request = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.05,
        price=25000.0,
    )

    baseline_total = dummy_data.portfolio.total_value
    baseline_invested = dummy_data.portfolio.invested_amount

    assessment = await risk_manager.validate_trade_order("bot-cycle", order_request)
    assert assessment.result in {RiskCheckResult.APPROVED, RiskCheckResult.WARNING}

    effective_qty = min(order_request.quantity, assessment.max_allowed_quantity or order_request.quantity)
    response = await engine.place_order(
        symbol=order_request.symbol,
        side=order_request.side,
        quantity=effective_qty,
        price=order_request.price,
        order_type=order_request.order_type,
    )

    assert response.success is True
    assert response.symbol == "BTCUSDT"

    await portfolio_manager.update_position("BTC/USDT", effective_qty, order_request.price, transaction_type="buy")

    summary = await portfolio_manager.get_portfolio_summary()
    updated_position = next(pos for pos in summary.positions if pos.symbol == "BTC/USDT")

    assert pytest.approx(updated_position.amount, rel=1e-4) == 0.25 + effective_qty
    assert summary.total_value >= baseline_total
    assert summary.invested_amount >= baseline_invested
