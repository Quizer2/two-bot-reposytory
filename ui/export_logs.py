from pathlib import Path
import json, csv

LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "events.jsonl"

def export_json(path: Path) -> int:
    path.write_text(LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else "", encoding="utf-8")
    return sum(1 for _ in LOG_FILE.open("r", encoding="utf-8")) if LOG_FILE.exists() else 0

def export_csv(path: Path) -> int:
    if not LOG_FILE.exists():
        path.write_text("", encoding="utf-8")
        return 0
    rows = []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            rows.append([rec.get("ts"), rec.get("event"), json.dumps(rec.get("payload", {}), ensure_ascii=False)])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts","event","payload"])
        w.writerows(rows)
    return len(rows)
