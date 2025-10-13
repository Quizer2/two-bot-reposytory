import math
from statistics import mean, pstdev
from typing import List, Tuple

def equity_curve(returns: List[float], start_equity: float = 1.0) -> List[float]:
    eq = [start_equity]
    for r in returns:
        eq.append(eq[-1] * (1.0 + r))
    return eq

def max_drawdown(equity: List[float]) -> float:
    peak = equity[0]
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak > 0 else 0
        mdd = max(mdd, dd)
    return mdd

def sharpe_ratio(returns: List[float], risk_free: float = 0.0, periods_per_year: int = 365) -> float:
    if not returns:
        return 0.0
    excess = [r - risk_free/periods_per_year for r in returns]
    sigma = pstdev(excess) if len(excess) > 1 else 0.0
    if sigma == 0:
        return 0.0
    return (mean(excess) / sigma) * math.sqrt(periods_per_year)

def win_rate(trades: List[Tuple[float, float]]) -> float:
    # trades: list of (entry_price, exit_price) for long trades
    if not trades:
        return 0.0
    wins = sum(1 for e,x in trades if x > e)
    return wins / len(trades)
