from pathlib import Path
import json, os
from typing import Optional
from cryptography.fernet import Fernet
from hashlib import sha256
from base64 import urlsafe_b64encode
from .encryption import derive_key, load_or_create_salt
from utils.logger import get_logger, LogType
logger = get_logger(__name__, LogType.SECURITY)

STORE = Path(__file__).resolve().parents[1] / "data"
STORE.mkdir(parents=True, exist_ok=True)
MASTER_META = STORE / "master.key"  # contains {"kdf_salt":..., "hash":...}

def _kdf(password: str, salt: bytes) -> bytes:
    # derive 32 bytes key for Fernet from password+salt using existing derive_key()
    raw = derive_key(password)  # uses global salt from encryption module
    # mix in local salt and produce 32 bytes
    digest = sha256(raw + salt).digest()
    return urlsafe_b64encode(digest)

def is_initialized() -> bool:
    return MASTER_META.exists()

def setup_master_password(password: str) -> None:
    local_salt = os.urandom(16)
    key = _kdf(password, local_salt)
    # store only hash to verify later
    digest = sha256(key).hexdigest()
    MASTER_META.write_text(json.dumps({"kdf_salt": local_salt.hex(), "hash": digest}), encoding="utf-8")
    try:
        os.chmod(MASTER_META, 0o600)
    except Exception as e:
        logger.error(f"Failed to set permissions on {MASTER_META}: {e}", exc_info=True)

def verify_master_password(password: str) -> bool:
    if not MASTER_META.exists():
        return False
    meta = json.loads(MASTER_META.read_text(encoding="utf-8"))
    local_salt = bytes.fromhex(meta["kdf_salt"])
    key = _kdf(password, local_salt)
    return sha256(key).hexdigest() == meta["hash"]

def get_fernet(password: str) -> Fernet:
    # returns Fernet based on user password
    if not MASTER_META.exists():
        raise RuntimeError("Master password not initialized")
    meta = json.loads(MASTER_META.read_text(encoding="utf-8"))
    local_salt = bytes.fromhex(meta["kdf_salt"])
    key = _kdf(password, local_salt)
    return Fernet(key)
