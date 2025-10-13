
import os, sys, json, math, random, time
from pathlib import Path

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

REPORT = {"strategies": {}, "summary": {}}

def gen_series(n=200, amp=1.0, noise=0.02):
    data=[]
    for i in range(n):
        base = 20000 + 1000*math.sin(i/15.0) + 500*math.sin(i/7.0)
        price = base * (1 + random.uniform(-noise, noise))
        data.append(price)
    return data

def sma(sig, w):
    if len(sig) < w: return None
    return sum(sig[-w:])/w

def ema(prev, price, a=0.1):
    return (a*price + (1-a)*prev) if prev is not None else price

def run_backtest(name, series):
    equity=1000.0
    position=0.0
    entry=None
    trades=0
    wins=0
    ema_val=None
    history=[]
    for p in series:
        history.append(p)
        sig="HOLD"
        if name=="SMA":
            ma_fast=sma(history, 5); ma_slow=sma(history, 20)
            if ma_fast and ma_slow:
                if ma_fast>ma_slow and position==0:
                    sig="BUY"
                elif ma_fast<ma_slow and position>0:
                    sig="SELL"
        elif name=="EMA":
            ema_val = ema(ema_val, p, 0.12)
            ma_slow = sma(history, 18)
            if ma_slow:
                if ema_val>ma_slow and position==0:
                    sig="BUY"
                elif ema_val<ma_slow and position>0:
                    sig="SELL"
        elif name=="MeanReversion":
            m=sma(history, 20)
            if m:
                dev = (p-m)/m
                if dev<-0.01 and position==0: sig="BUY"
                elif dev>0.01 and position>0: sig="SELL"
        elif name=="Momentum":
            if len(history)>10:
                if p>history[-10] and position==0: sig="BUY"
                elif p<history[-10] and position>0: sig="SELL"
        # execute
        if sig=="BUY" and position==0:
            position = 1.0
            entry = p
            trades+=1
        elif sig=="SELL" and position>0:
            pnl = (p-entry)
            if pnl>0: wins+=1
            equity += pnl
            position=0.0
            entry=None
    # close EOD
    if position>0 and entry is not None:
        equity += (history[-1]-entry)
        trades+=1
        if history[-1]-entry>0: wins+=1
        position=0.0
    return {
        "final_equity": round(equity, 2),
        "pnl": round(equity-1000.0, 2),
        "trades": trades,
        "win_rate": round((wins/max(trades,1)), 3)
    }

def main():
    random.seed(42)
    series = gen_series(240)
    results={}
    for name in ["SMA","EMA","MeanReversion","Momentum"]:
        results[name]=run_backtest(name, series)
    # summary
    best = max(results.items(), key=lambda kv: kv[1]["pnl"])[0]
    worst = min(results.items(), key=lambda kv: kv[1]["pnl"])[0]
    REPORT["strategies"]=results
    REPORT["summary"]={"best_strategy": best, "worst_strategy": worst}
    out = Path(BASE)/"tests"/"backtest_report.json"
    out.write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    print(out)

if __name__=="__main__":
    main()
