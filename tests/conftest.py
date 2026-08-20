"""Shared fixtures for the EpriX test suite."""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from EpriX import pack as _pack
from EpriX.router import app

PASSPHRASE = "a-very-strong-test-passphrase-!2026"


@pytest.fixture()
def tmp_dir(tmp_path):
    """Provide an isolated temporary directory for test assets."""
    return tmp_path


@pytest.fixture()
def sample_tree(tmp_dir):
    """Create a small sample project tree containing text, binary and unicode files."""
    src = tmp_dir / "src"
    src.mkdir()
    (src / "readme.txt").write_text("EpriX test readme\n", encoding="utf-8")
    (src / "notes.txt").write_text(
        "First line\nSecond line\nمرحبا بالعالم — مرحبًا\n", encoding="utf-8"
    )
    (src / "image.bin").write_bytes(bytes(range(256)) * 4)
    sub = src / "nested"
    sub.mkdir()
    (sub / "deep.txt").write_text("deeply nested file\n", encoding="utf-8")
    return src


@pytest.fixture()
def client():
    """Provide a FastAPI TestClient for the router app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def packed_archive(tmp_dir, sample_tree):
    """Pack sample_tree into a .epr archive together with its keys file."""
    archive = tmp_dir / "archive.epr"
    keys = tmp_dir / "keys.json"
    _pack.pack_directory(
        source=sample_tree,
        archive_file=archive,
        keys_file=keys,
        passphrase=PASSPHRASE,
        compression="zstd",
    )
    return archive, keys
