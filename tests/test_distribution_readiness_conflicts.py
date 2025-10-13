from tools import check_distribution_readiness as readiness


def _build_conflict_text() -> str:
    """Return a string that mimics git conflict markers without embedding them in the source file."""

    marker_start = ("<" * 7) + " HEAD"
    marker_mid = "=" * 7
    marker_end = (">" * 7) + " branch"
    return "\n".join([
        "print('start')",
        marker_start,
        marker_mid,
        marker_end,
        "",
    ])


def test_conflict_check_detects_markers(tmp_path, monkeypatch):
    conflicted = tmp_path / "conflicted.py"
    conflicted.write_text(_build_conflict_text(), encoding="utf-8")

    monkeypatch.setattr(readiness, "_list_tracked_files", lambda: [conflicted])

    result = readiness._check_conflict_markers()

    assert result.status == "error"
    assert str(conflicted) in result.details["files"]


def test_conflict_check_passes_clean_files(tmp_path, monkeypatch):
    clean = tmp_path / "clean.py"
    clean.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(readiness, "_list_tracked_files", lambda: [clean])

    result = readiness._check_conflict_markers()

    assert result.status == "ok"
    assert result.details == {}


def test_conflict_check_ignores_ascii_separators(tmp_path, monkeypatch):
    banner = tmp_path / "banner.txt"
    banner.write_text("================================\n", encoding="utf-8")

    monkeypatch.setattr(readiness, "_list_tracked_files", lambda: [banner])

    result = readiness._check_conflict_markers()

    assert result.status == "ok"
