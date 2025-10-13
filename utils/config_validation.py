import yaml
from pathlib import Path
import os
from utils.secure_store import get_exchange_credentials

REQUIRED_KEYS = [
    ("database", "path"),
    ("production_mode", ),
]

def validate_app_config(config: dict | None = None) -> list[str]:
    cfg_path = Path(__file__).resolve().parents[1] / "config" / "app_config.yaml"
    problems: list[str] = []
    try:
        data = config if isinstance(config, dict) else (yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {})
    except Exception as e:
        return [f"config_read_error: {e}"]
    for keys in REQUIRED_KEYS:
        node = data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                problems.append(f"missing: {'/'.join(keys)}")
                break
            node = node[k]
    # Validate API keys presence for enabled exchanges (if not public_only)
    exchanges = data.get('exchanges', {}) or {}
    if isinstance(exchanges, dict):
        for name, ex_cfg in exchanges.items():
            try:
                enabled = bool(ex_cfg.get('enabled', False))
            except Exception:
                enabled = False
            if not enabled:
                continue
            public_only = bool(ex_cfg.get('public_only', False))
            if public_only:
                continue
            testnet = bool(ex_cfg.get('testnet', False) or ex_cfg.get('sandbox', False))
            required = ['api_key', 'api_secret']
            if (name or '').lower() in ('kucoin', 'coinbase'):
                required.append('passphrase')
            creds = {}
            try:
                creds = get_exchange_credentials((name or '').lower(), testnet=testnet) or {}
            except Exception:
                creds = {}
            for key in required:
                cfg_val = ex_cfg.get(key)
                if not cfg_val and not creds.get(key):
                    problems.append(f"missing_credentials:{name}:{key}")
    return problems
