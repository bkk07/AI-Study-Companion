import pytest

from app.core.security import hash_password, verify_password


def test_hash_is_argon2id():
    h = hash_password("supersecret123")
    assert h.startswith("$argon2id$")


def test_correct_password_verifies():
    pwd = "correcthorsebatterystaple"
    h = hash_password(pwd)
    assert verify_password(h, pwd) is True


def test_wrong_password_fails():
    h = hash_password("rightpassword123")
    assert verify_password(h, "wrongpassword123") is False


def test_same_password_different_hashes_due_to_salt():
    pwd = "samepassword123"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    assert h1 != h2  # salt ensures uniqueness
    assert verify_password(h1, pwd) is True
    assert verify_password(h2, pwd) is True


def test_empty_password_raises():
    with pytest.raises(ValueError):
        hash_password("")
    with pytest.raises(ValueError):
        hash_password(None)  # type: ignore[arg-type]


def test_verify_invalid_hash_returns_false():
    assert verify_password("not-a-valid-hash", "anything") is False
    assert verify_password("$argon2id$v=19$m=65536,t=3,p=4$invalid", "pwd") is False
