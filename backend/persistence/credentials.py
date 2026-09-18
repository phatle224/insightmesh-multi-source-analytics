"""The only boundary allowed to encrypt or decrypt datasource credentials."""

import json
from collections.abc import Mapping
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class CredentialDecryptionError(RuntimeError):
    pass


class CredentialCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("ascii"))

    def encrypt(self, credentials: Mapping[str, Any]) -> bytes:
        payload = json.dumps(dict(credentials), separators=(",", ":"), sort_keys=True).encode()
        return self._fernet.encrypt(payload)

    def decrypt(self, ciphertext: bytes) -> dict[str, Any]:
        try:
            value = json.loads(self._fernet.decrypt(ciphertext))
        except (InvalidToken, json.JSONDecodeError) as exc:
            raise CredentialDecryptionError("Unable to decrypt datasource credentials") from exc
        if not isinstance(value, dict):
            raise CredentialDecryptionError("Credential payload must be an object")
        return value
