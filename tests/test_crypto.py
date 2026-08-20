"""Tests for EpriX.crypto — key derivation and multi-layer encryption."""

import pytest

from EpriX.crypto import (
    decrypt_multilayer,
    derive_keys_from_passphrase,
    encrypt_multilayer,
)

SAMPLE_DATA = b"EpriX multi-layer encryption test payload"


class TestKeyDerivation:
    def test_derives_correct_number_of_keys(self):
        salt = b"\x01" * 16
        keys = derive_keys_from_passphrase("secret", salt)
        assert len(keys) == 6

    def test_keys_are_deterministic(self):
        salt = b"\x02" * 16
        first = derive_keys_from_passphrase("secret", salt)
        second = derive_keys_from_passphrase("secret", salt)
        assert first == second

    def test_different_passphrases_differ(self):
        salt = b"\x03" * 16
        a = derive_keys_from_passphrase("alpha", salt)
        b = derive_keys_from_passphrase("beta", salt)
        assert a != b

    def test_different_salts_differ(self):
        a = derive_keys_from_passphrase("secret", b"\x01" * 16)
        b = derive_keys_from_passphrase("secret", b"\x02" * 16)
        assert a != b


class TestMultiLayerEncryption:
    def test_roundtrip(self):
        ciphertext, metadata = encrypt_multilayer(SAMPLE_DATA, "test-passphrase")
        assert ciphertext != SAMPLE_DATA
        plaintext = decrypt_multilayer(ciphertext, metadata, "test-passphrase")
        assert plaintext == SAMPLE_DATA

    def test_roundtrip_empty_bytes(self):
        ciphertext, metadata = encrypt_multilayer(b"", "test-passphrase")
        assert decrypt_multilayer(ciphertext, metadata, "test-passphrase") == b""

    def test_wrong_passphrase_raises(self):
        ciphertext, metadata = encrypt_multilayer(SAMPLE_DATA, "correct")
        with pytest.raises(Exception):  # noqa: B017 — auth failure raises InvalidTag/InvalidSignature (no common base)  # InvalidTag / InvalidSignature on auth failure
            decrypt_multilayer(ciphertext, metadata, "wrong")

    def test_ciphertext_changes_with_salt(self):
        """Two encryptions of the same payload must not produce identical output."""
        a, _ = encrypt_multilayer(SAMPLE_DATA, "pass")
        b, _ = encrypt_multilayer(SAMPLE_DATA, "pass")
        assert a != b
