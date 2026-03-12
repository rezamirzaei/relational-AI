from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


class PasswordHasher:
    _salt_bytes = 16
    _n = 2**14
    _r = 8
    _p = 1
    _dklen = 64

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(self._salt_bytes)
        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self._n,
            r=self._r,
            p=self._p,
            dklen=self._dklen,
        )
        salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
        key_text = base64.urlsafe_b64encode(derived_key).decode("ascii")
        return f"scrypt${salt_text}${key_text}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, salt_text, key_text = password_hash.split("$", maxsplit=2)
        except ValueError:
            return False
        if algorithm != "scrypt":
            return False

        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected_key = base64.urlsafe_b64decode(key_text.encode("ascii"))
        candidate_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self._n,
            r=self._r,
            p=self._p,
            dklen=self._dklen,
        )
        return hmac.compare_digest(expected_key, candidate_key)
