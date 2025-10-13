from typing import List, Dict, Tuple, Callable, Optional
import csv
from pathlib import Path
from utils.metrics import equity_curve, max_drawdown, sharpe_ratio, win_rate

Candle = Dict[str, float]
SignalFunc = Callable[[List[Candle], int], Optional[str]]  # 'buy'|'sell'|None

def load_ohlcv_csv(path: Path) -> List[Candle]:
    rows: List[Candle] = []
    with path.open('r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            # expected columns: timestamp, open, high, low, close, volume
            rows.append({
                't': int(row.get('timestamp') or row.get('time') or 0),
                'o': float(row.get('open', 0)),
                'h': float(row.get('high', 0)),
                'l': float(row.get('low', 0)),
                'c': float(row.get('close', 0)),
                'v': float(row.get('volume', 0)),
            })
    return rows

def sma(values: List[float], period: int) -> List[float]:
    out = []
    s = 0.0
    for i,v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i-period]
        out.append(s/period if i+1 >= period else None)
    return out

def sma_cross_strategy(short:int=10, long:int=20) -> SignalFunc:
    def fn(candles: List[Candle], i: int) -> Optional[str]:
        closes = [c['c'] for c in candles[:i+1]]
        s = sma(closes, short)
        l = sma(closes, long)
        if i == 0 or s[i] is None or l[i] is None:
            return None
        prev = i-1
        if s[prev] is None or l[prev] is None:
            return None
        # crossover
        if s[prev] <= l[prev] and s[i] > l[i]:
            return 'buy'
        if s[prev] >= l[prev] and s[i] < l[i]:
            return 'sell'
        return None
    return fn

def backtest(candles: List[Candle], signal: SignalFunc) -> Dict:
    position = None  # store entry price
    trades: List[Tuple[float,float]] = []
    returns: List[float] = []
    for i in range(len(candles)):
        sig = signal(candles, i)
        # auto-close on last candle if still open
        if i == len(candles)-1 and position is not None:
                entry = position
                exitp = candles[i]['c']
                trades.append((entry, exitp))
                returns.append((exitp-entry)/entry)
                position = None
        px = candles[i]['c']
        if sig == 'buy' and position is None:
            position = px
        elif sig == 'sell' and position is not None:
            # close long
            entry = position
            exitp = px
            trades.append((entry, exitp))
            r = (exitp - entry)/entry
            returns.append(r)
            position = None
    eq = equity_curve(returns, start_equity=1.0)
    mdd = max_drawdown(eq)
    sr = sharpe_ratio(returns)
    wr = win_rate(trades)
    total_pnl = eq[-1]-1.0 if eq else 0.0
    return {
        'trades': trades,
        'returns': returns,
        'equity': eq,
        'metrics': {
            'total_pnl': total_pnl,
            'win_rate': wr,
            'max_drawdown': mdd,
            'sharpe': sr,
            'num_trades': len(trades),
        }
    }
