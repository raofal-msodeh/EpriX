"""Tests for EpriX.serialization — tree serialization roundtrip and traversal guard."""

import pytest

from EpriX.serialization import deserialize_directory_tree, serialize_directory_tree


def _collect_files(source_dir):
    """Collect readable text files under source_dir as (path, encoding, content)."""
    collected = []
    for file_path in sorted(source_dir.rglob("*")):
        if file_path.is_file():
            try:
                content = file_path.read_text("utf-8")
            except UnicodeDecodeError:
                # Binary files are skipped by pack.collect_files; skip them here too.
                continue
            collected.append((file_path, "utf-8", content))
    return collected


class TestDirectorySerialization:
    def test_roundtrip(self, tmp_dir, sample_tree):
        files = _collect_files(sample_tree)
        assert files
        payload = serialize_directory_tree(sample_tree, files)
        assert payload

        out = tmp_dir / "restored"
        count = deserialize_directory_tree(payload, out)
        assert count == len(files)

        for file_path, _, content in files:
            restored = out / file_path.relative_to(sample_tree)
            assert restored.read_text("utf-8") == content

    def test_roundtrip_with_unicode_content(self, tmp_dir, sample_tree):
        files = _collect_files(sample_tree)
        payload = serialize_directory_tree(sample_tree, files)
        out = tmp_dir / "restored"
        deserialize_directory_tree(payload, out)
        notes = out / "notes.txt"
        assert notes.read_text("utf-8") == "First line\nSecond line\nمرحبا بالعالم — مرحبًا\n"

    def test_dry_run_writes_nothing(self, tmp_dir, sample_tree):
        files = _collect_files(sample_tree)
        payload = serialize_directory_tree(sample_tree, files)
        out = tmp_dir / "dryrun"
        out.mkdir()
        marker = out / "marker.txt"
        marker.write_text("untouched\n", encoding="utf-8")
        count = deserialize_directory_tree(payload, out, dry_run=True)
        assert count == len(files)
        assert not any(out.iterdir()) or list(out.iterdir()) == [marker], (
            "dry run must not create files"
        )
        assert marker.read_text("utf-8") == "untouched\n"

    def test_nested_directory_structure_preserved(self, tmp_dir, sample_tree):
        files = _collect_files(sample_tree)
        payload = serialize_directory_tree(sample_tree, files)
        out = tmp_dir / "restored"
        deserialize_directory_tree(payload, out)
        assert (out / "nested" / "deep.txt").exists()

    def test_traversal_path_rejected(self, tmp_dir, sample_tree):
        """A manifest containing an absolute/escaped path must not escape the target."""
        base = tmp_dir / "safe"
        base.mkdir()
        payload = (
            b'{"version":"1.0","source_dir":"/x","created":"2026-01-01T00:00:00+00:00",'
            b'"preserve_perms":false,"files":[{"path":"../escape.txt","encoding":"utf-8",'
            b'"content":"x","size":1}]}'
        )
        with pytest.raises(ValueError):
            deserialize_directory_tree(payload, base)
