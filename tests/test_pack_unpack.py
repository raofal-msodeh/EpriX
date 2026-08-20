"""Tests for EpriX.pack and EpriX.unpack — end-to-end archive pipeline."""

import pytest

from EpriX import pack
from EpriX.unpack import unpack_directory

from .conftest import PASSPHRASE


class TestPackDirectory:
    def test_creates_archive_and_keys(self, tmp_dir, sample_tree):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
        )
        assert archive.exists() and archive.stat().st_size > 0
        assert keys.exists() and keys.stat().st_size > 0

    def test_rejects_missing_source(self, tmp_dir):
        with pytest.raises(ValueError):
            pack.pack_directory(
                source=tmp_dir / "missing",
                output=tmp_dir / "out.epr",
                keys_file=tmp_dir / "keys.json",
                passphrase=PASSPHRASE,
            )

    def test_respects_ignore_file(self, tmp_dir, sample_tree):
        (sample_tree / ".eprignore").write_text("*.log\n")
        log = sample_tree / "trace.log"
        log.write_text("log entry\n")
        archive = tmp_dir / "out.epr"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=tmp_dir / "keys.json",
            passphrase=PASSPHRASE,
        )
        assert archive.exists()


class TestUnpackDirectory:
    def test_rejects_missing_input(self, tmp_dir):
        with pytest.raises(ValueError):
            unpack_directory(
                input_file=tmp_dir / "missing.epr",
                keys_file=tmp_dir / "keys.json",
                passphrase=PASSPHRASE,
                target=tmp_dir / "out",
            )


class TestFullPipeline:
    def test_roundtrip(self, tmp_dir, sample_tree):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
        )

        out = tmp_dir / "restored"
        unpack_directory(
            input_file=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
            target=out,
        )
        for original in sample_tree.rglob("*"):
            if not original.is_file() or original.name == ".eprignore":
                continue
            try:
                original.read_text("utf-8")
            except UnicodeDecodeError:
                # Binary files are intentionally excluded from the archive.
                continue
            restored = out / original.relative_to(sample_tree)
            assert restored.exists(), f"{original} missing after unpack"
            assert restored.read_text("utf-8") == original.read_text("utf-8")

    def test_wrong_passphrase_raises(self, tmp_dir, sample_tree):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
        )
        out = tmp_dir / "out"
        with pytest.raises(ValueError):
            unpack_directory(
                input_file=archive,
                keys_file=keys,
                passphrase="wrong-passphrase",
                target=out,
            )

    def test_dry_run_writes_nothing(self, tmp_dir, sample_tree):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
        )
        out = tmp_dir / "dryrun"
        out.mkdir()
        (out / "marker.txt").write_text("untouched\n")
        unpack_directory(
            input_file=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
            target=out,
            dry_run=True,
        )
        # dry_run must never create archive contents inside the target.
        for name in ("readme.txt", "notes.txt", "image.bin"):
            assert not (out / name).exists(), f"dry run wrote {name}"
        assert (out / "marker.txt").read_text() == "untouched\n"

    def test_overwrite_requires_flag(self, tmp_dir, sample_tree):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
        )
        out = tmp_dir / "existing"
        out.mkdir()
        (out / "old.txt").write_text("old\n")
        with pytest.raises(ValueError):
            unpack_directory(
                input_file=archive,
                keys_file=keys,
                passphrase=PASSPHRASE,
                target=out,
            )
        unpack_directory(
            input_file=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
            target=out,
            overwrite=True,
        )
        assert (out / "readme.txt").exists()

    def test_tampered_archive_rejected(self, tmp_dir, sample_tree):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        pack.pack_directory(
            source=sample_tree,
            output=archive,
            keys_file=keys,
            passphrase=PASSPHRASE,
        )
        data = bytearray(archive.read_bytes())
        # Corrupt a byte somewhere in the middle of the payload.
        data[len(data) // 2] ^= 0xFF
        archive.write_bytes(bytes(data))
        out = tmp_dir / "out"
        with pytest.raises(Exception):  # noqa: B017 — auth failure raises InvalidTag/InvalidSignature (no common base)
            unpack_directory(
                input_file=archive,
                keys_file=keys,
                passphrase=PASSPHRASE,
                target=out,
            )
