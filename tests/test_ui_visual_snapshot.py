import json
from pathlib import Path

from tools.ui_snapshot import capture_bot_card_snapshot


def test_bot_card_snapshot_matches_fixture():
    snapshot = capture_bot_card_snapshot()
    fixture_path = Path("analytics/ui_bot_card_snapshot.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert snapshot == fixture
