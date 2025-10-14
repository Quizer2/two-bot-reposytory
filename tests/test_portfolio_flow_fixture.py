import json
from pathlib import Path

from tools.generate_portfolio_fixture import build_portfolio_fixture


def test_portfolio_flow_fixture_is_current():
    expected = build_portfolio_fixture()
    stored = json.loads(Path("analytics/portfolio_flow_snapshot.json").read_text(encoding="utf-8"))
    assert stored == expected
