from pathlib import Path
import json
import os
from typing import Optional
from cryptography.fernet import InvalidToken
from .master_password import get_fernet

STORE = Path(__file__).resolve().parents[1] / "data"
SEC_FILE = STORE / "secrets.json"

ENV_PREFIX = "CRYPTOBOT_"  # ENV fallback, e.g., CRYPTOBOT_API_KEY

def load_all() -> dict:
    if SEC_FILE.exists():
        try:
            return json.loads(SEC_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_all(data: dict) -> None:
    SEC_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def delete_secret(name: str) -> None:
    """Remove a secret entry from the secure store if it exists."""
    data = load_all()
    if name in data:
        del data[name]
        save_all(data)

def put_secret(name: str, value: str, master_password: str) -> None:
    f = get_fernet(master_password)
    token = f.encrypt(value.encode("utf-8")).decode("utf-8")
    data = load_all()
    data[name] = token
    save_all(data)

def get_secret(name: str, master_password: str) -> Optional[str]:
    # Prefer ENV if present
    env_name = ENV_PREFIX + name.upper()
    env_val = os.environ.get(env_name)
    if env_val:
        return env_val
    
    data = load_all()
    token = data.get(name)
    if not token:
        return None
    f = get_fernet(master_password)
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None

# Helper to fetch exchange credentials from ENV or encrypted store
from typing import Dict

def get_exchange_credentials(exchange: str, master_password: Optional[str] = None, testnet: bool = False) -> Dict[str, Optional[str]]:
    """Fetch exchange API credentials.
    Order of precedence:
    1) Environment variables (preferred, no decryption)
    2) Encrypted secrets store (requires master_password)
    
    ENV variables supported (uppercase):
    - CRYPTOBOT_<EXCHANGE>_API_KEY
    - CRYPTOBOT_<EXCHANGE>_API_SECRET
    - CRYPTOBOT_<EXCHANGE>_PASSPHRASE (if applicable)
    Also supported testnet variants with suffix _TESTNET.
    
    Secrets store names (lowercase):
    - <exchange>_api_key[_testnet]
    - <exchange>_api_secret[_testnet]
    - <exchange>_passphrase[_testnet]
    """
    exu = (exchange or '').upper()
    suffix = '_TESTNET' if testnet else ''
    env_candidates = {
        'api_key': [f"{ENV_PREFIX}{exu}_API_KEY{suffix}", f"{ENV_PREFIX}{exu}_API_KEY"],
        'api_secret': [f"{ENV_PREFIX}{exu}_API_SECRET{suffix}", f"{ENV_PREFIX}{exu}_API_SECRET"],
        'passphrase': [f"{ENV_PREFIX}{exu}_PASSPHRASE{suffix}", f"{ENV_PREFIX}{exu}_PASSPHRASE"],
    }
    creds: Dict[str, Optional[str]] = {'api_key': None, 'api_secret': None, 'passphrase': None}
    # Try ENV
    for k, names in env_candidates.items():
        for name in names:
            val = os.environ.get(name)
            if val:
                creds[k] = val
                break
    # Try encrypted store if not found and master_password provided
    if master_password:
        # prefer testnet-specific names first
        for k in ['api_key', 'api_secret', 'passphrase']:
            if creds[k]:
                continue
            name_base = f"{exchange.lower()}_{k}"
            names = [f"{name_base}_testnet", name_base] if testnet else [name_base]
            for nm in names:
                val = get_secret(nm, master_password)
                if val:
                    creds[k] = val
                    break
    return creds
