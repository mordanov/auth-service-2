import hashlib
import hmac
import bcrypt


def _prehash(password: str) -> bytes:
    # SHA-256 prehash removes bcrypt's 72-byte input limit without changing
    # security properties. Hex encoding keeps the output printable ASCII.
    return hashlib.sha256(password.encode()).hexdigest().encode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(
        bcrypt.hashpw(_prehash(password), hashed.encode()),
        hashed.encode(),
    )
