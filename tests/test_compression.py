"""Tests for EpriX.compression — pre/post encryption compression stages."""

import pytest

from EpriX.compression import compress_data, decompress_data

PLAIN = b"EpriX compression roundtrip payload " * 100


class TestPreEncryptionCompression:
    def test_roundtrip(self):
        compressed = compress_data(PLAIN, stage="pre-encryption")
        assert compressed != PLAIN
        assert decompress_data(compressed, stage="pre-encryption") == PLAIN

    def test_binary_data_roundtrip(self):
        binary = bytes(range(256)) * 50
        compressed = compress_data(binary, stage="pre-encryption")
        assert decompress_data(compressed, stage="pre-encryption") == binary

    def test_incompressible_data(self):
        randomish = bytes(x % 251 for x in range(500))
        compressed = compress_data(randomish, stage="pre-encryption")
        assert decompress_data(compressed, stage="pre-encryption") == randomish


class TestPostEncryptionCompression:
    def test_roundtrip(self):
        compressed = compress_data(PLAIN, stage="post-encryption")
        assert decompress_data(compressed, stage="post-encryption") == PLAIN

    def test_wrong_stage_order_raises(self):
        """Compressed data from one stage must fail when decoded with the other stage."""
        pre_compressed = compress_data(PLAIN, stage="pre-encryption")
        with pytest.raises(Exception):
            decompress_data(pre_compressed, stage="post-encryption")

        post_compressed = compress_data(PLAIN, stage="post-encryption")
        with pytest.raises(Exception):
            decompress_data(post_compressed, stage="pre-encryption")


class TestEmptyData:
    def test_empty_post_encryption(self):
        compressed = compress_data(b"", stage="post-encryption")
        assert decompress_data(compressed, stage="post-encryption") == b""

    def test_empty_pre_encryption(self):
        compressed = compress_data(b"", stage="pre-encryption")
        assert decompress_data(compressed, stage="pre-encryption") == b""

    def test_small_data_still_roundtrips(self):
        """Tiny payloads must survive the two-stage pipeline intact."""
        payload = b"tiny"
        assert decompress_data(compress_data(payload, stage="pre-encryption"),
                               stage="pre-encryption") == payload
