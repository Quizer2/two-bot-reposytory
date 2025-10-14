from utils.config_manager import ConfigManager


def test_supported_trading_pairs_default(tmp_path):
    manager = ConfigManager(config_dir=tmp_path)
    pairs = manager.get_supported_trading_pairs()

    assert "BTC/EUR" in pairs
    assert "ETH/USDT" in pairs
    # lista powinna być deduplikowana oraz zachować co najmniej kilkanaście pozycji
    assert len(pairs) >= 10
