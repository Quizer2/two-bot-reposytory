"""Generate deterministic portfolio flow snapshot for regression tests."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.portfolio_manager import PortfolioManager, PortfolioData


def build_portfolio_fixture() -> dict:
    manager = PortfolioManager(
        data_manager=_FixtureDataManager(
            PortfolioData(
                total_value=18200.0,
                available_balance=11000.0,
                invested_amount=7200.0,
                profit_loss=384.0,
                profit_loss_percent=5.63,
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
                    {
                        "symbol": "BTC/EUR",
                        "amount": 0.1,
                        "value": 3200.0,
                        "change_24h": 1.3,
                    },
                ],
                last_updated=datetime.utcnow(),
            )
        )
    )

    summary = _run(manager.get_portfolio_summary())
    positions = [
        {
            "symbol": pos.symbol,
            "amount": pos.amount,
            "value": pos.value,
            "profit_loss": pos.profit_loss,
            "profit_loss_percent": pos.profit_loss_percent,
        }
        for pos in summary.positions
    ]

    return {
        "summary": {
            "total_value": summary.total_value,
            "available_balance": summary.available_balance,
            "invested_amount": summary.invested_amount,
            "total_profit_loss": summary.total_profit_loss,
            "total_profit_loss_percent": summary.total_profit_loss_percent,
            "daily_change": summary.daily_change,
            "daily_change_percent": summary.daily_change_percent,
        },
        "positions": positions,
    }


def write_fixture(path: Path) -> dict:
    payload = build_portfolio_fixture()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def _run(awaitable):
    import asyncio

    return asyncio.get_event_loop().run_until_complete(awaitable)


class _FixtureDataManager:
    def __init__(self, portfolio: PortfolioData) -> None:
        self._portfolio = portfolio

    async def get_portfolio_data(self) -> PortfolioData:
        return self._portfolio


def main() -> None:  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Generate portfolio flow snapshot")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analytics/portfolio_flow_snapshot.json"),
        help="Destination file",
    )
    args = parser.parse_args()
    write_fixture(args.output)


if __name__ == "__main__":  # pragma: no cover
    main()
