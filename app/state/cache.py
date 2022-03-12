from __future__ import annotations

from ast import Str

from cryptography.hazmat.backends import default_backend as backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

import app.utils
from app.state.services import Geolocation

geoloc: dict[str, Geolocation] = {}


class PasswordCache:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def cache_password(self, password_md5: str, encrypted_password: str) -> None:
        self._cache[encrypted_password] = password_md5

    def verify_password(self, password_md5: str, encrypted_password: str) -> bool:
        if cached_result := self._cache.get(encrypted_password):
            return cached_result == password_md5

        return verify_password(password_md5, encrypted_password)


password = PasswordCache()


def generate_password(password_md5: bytes) -> str:
    assert isinstance(password_md5, bytes)  # to prevent issues in the future

    k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"", backend=backend())

    encrypted_password = k.derive(password_md5).decode("unicode-escape")
    password.cache_password(password_md5, encrypted_password)

    return encrypted_password


def encode_password(pw: str) -> bytes:
    return pw.encode("ISO-8859-1").decode("unicode-escape").encode("ISO-8859-1")


def verify_password(password_md5: str, encrypted_password: str) -> bool:
    try:
        k = HKDFExpand(
            algorithm=hashes.SHA256(),
            length=32,
            info=b"",
            backend=backend(),
        )

        k.verify(password_md5, encrypted_password)
        password.cache_password(password_md5, encrypted_password)

        return True
    except Exception:
        return False
