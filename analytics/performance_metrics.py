
from __future__ import annotations
from typing import List, Dict, Optional
import math

def sharpe_ratio(equity: List[float], risk_free: float = 0.0) -> Optional[float]:
    if len(equity) < 2:
        return None
    rets = [(equity[i]-equity[i-1])/equity[i-1] if equity[i-1] else 0.0 for i in range(1, len(equity))]
    avg = sum(rets)/len(rets) - risk_free
    var = sum((r-avg)**2 for r in rets)/max(1, len(rets)-1)
    std = math.sqrt(var) if var>0 else 0.0
    if std==0.0:
        return None
    return avg/std

def sortino_ratio(equity: List[float], risk_free: float = 0.0) -> Optional[float]:
    if len(equity) < 2:
        return None
    rets = [(equity[i]-equity[i-1])/equity[i-1] if equity[i-1] else 0.0 for i in range(1, len(equity))]
    downside = [min(0.0, r-risk_free) for r in rets]
    dd_var = sum(d*d for d in downside)/max(1, len(downside))
    dd = math.sqrt(dd_var)
    avg = sum(rets)/len(rets) - risk_free
    if dd==0.0:
        return None
    return avg/dd

def max_drawdown(equity: List[float]) -> Optional[float]:
    if not equity:
        return None
    peak = equity[0]
    mdd = 0.0
    for x in equity:
        if x>peak: peak=x
        dd = (peak - x)/peak if peak else 0.0
        if dd>mdd: mdd=dd
    return mdd

def summarize_equity(equity: List[float]) -> Dict[str, float]:
    sr = sharpe_ratio(equity) or 0.0
    sor = sortino_ratio(equity) or 0.0
    mdd = max_drawdown(equity) or 0.0
    return {
        "sharpe": round(sr, 4),
        "sortino": round(sor, 4),
        "max_drawdown": round(mdd, 4),
        "final_equity": round(equity[-1], 2) if equity else 0.0,
        "pnl": round((equity[-1]-equity[0]), 2) if equity else 0.0
    }
