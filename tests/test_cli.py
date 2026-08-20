"""Tests for EpriX.cli — argument parser and command dispatch."""

import pytest

from EpriX.cli import create_parser, main


class TestParser:
    def test_root_parser_has_subcommands(self):
        parser = create_parser()
        names = parser._subparsers._group_actions[0].choices
        # Subcommands must include pack, unpack and server.
        assert {"pack", "unpack", "server"} <= set(names)

    def test_pack_requires_mandatory_options(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["pack"])

    def test_pack_parses_options(self):
        parser = create_parser()
        args = parser.parse_args([
            "pack",
            "--source", "/tmp/src",
            "--output", "/tmp/out.epr",
            "--keys", "/tmp/keys.json",
            "--passphrase", "secret",
        ])
        assert str(args.source) == "/tmp/src"
        assert str(args.output) == "/tmp/out.epr"

    def test_unpack_parses_flags(self):
        parser = create_parser()
        args = parser.parse_args([
            "unpack",
            "--input", "/tmp/a.epr",
            "--keys", "/tmp/keys.json",
            "--passphrase", "secret",
            "--target", "/tmp/out",
            "--dry-run",
            "--overwrite",
        ])
        assert args.dry_run is True
        assert args.overwrite is True


class TestMainDispatch:
    def test_missing_command_exits(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["eprtool"])
        with pytest.raises(SystemExit):
            main()

    def test_pack_roundtrip_via_cli(self, tmp_dir, sample_tree, monkeypatch):
        archive = tmp_dir / "out.epr"
        keys = tmp_dir / "keys.json"
        monkeypatch.setattr("sys.argv", [
            "eprtool", "pack",
            "--source", str(sample_tree),
            "--output", str(archive),
            "--keys", str(keys),
            "--passphrase", "a-very-strong-test-passphrase-!2026",
        ])
        rc = main()
        assert rc == 0, "pack command must succeed"
        assert archive.exists()

        out = tmp_dir / "restored"
        monkeypatch.setattr("sys.argv", [
            "eprtool", "unpack",
            "--input", str(archive),
            "--keys", str(keys),
            "--passphrase", "a-very-strong-test-passphrase-!2026",
            "--target", str(out),
        ])
        rc = main()
        assert rc == 0
        assert (out / "readme.txt").exists()

    def test_console_entry_point_installed(self):
        import shutil

        eprix = shutil.which("eprix")
        assert eprix is not None, "eprix console script must be installed"
