from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Centralized Argon2id hasher — Phase 11
# Parameters follow OWASP Argon2id guidance; single instance is reused.
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash plaintext password with Argon2id. Never store plaintext."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    return _ph.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify plain password against Argon2id hash. Returns False on mismatch."""
    try:
        _ph.verify(hashed_password, plain_password)
        return True
    except (VerifyMismatchError, Exception):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if hash needs rehashing due to param changes (utility for future)."""
    try:
        return _ph.check_needs_rehash(hashed_password)
    except Exception:
        return True
