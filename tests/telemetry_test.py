
import os, sys, json, time, sqlite3, importlib
from pathlib import Path

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)

def main():
    t0=time.time()
    events_published=0
    db_writes=0
    errors=0
    try:
        event_bus = importlib.import_module("utils.event_bus")
        bus = event_bus.get_event_bus()
        for i in range(50):
            try:
                bus.publish("PerfEvent", {"i":i})
                events_published+=1
            except Exception:
                errors+=1
        # DB touch
        dbp = os.path.join(BASE, "data", "database.db")
        Path(os.path.dirname(dbp)).mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(dbp)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS telemetry (ts REAL, k TEXT, v REAL)")
        for i in range(20):
            c.execute("INSERT INTO telemetry VALUES (strftime('%s','now'), ?, ?)", (f"k{i}", float(i)))
            db_writes+=1
        conn.commit(); conn.close()
    except Exception:
        errors+=1
    t1=time.time()
    rep={
        "runtime_sec": round(t1-t0,3),
        "events_published": events_published,
        "db_writes": db_writes,
        "errors": errors
    }
    out = Path(BASE)/"tests"/"telemetry_report.json"
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(out)

if __name__=="__main__":
    main()
