"""Tests for EpriX.ignore — .eprignore pattern matching."""


from EpriX.ignore import IgnoreFilter


class TestIgnoreFilter:
    def test_ignore_listed_file(self, tmp_dir):
        source = tmp_dir / "src"
        source.mkdir()
        (source / ".eprignore").write_text("secrets/\n*.log\n")
        (source / "readme.txt").write_text("keep\n")
        secret = source / "secrets"
        secret.mkdir()
        (secret / "key.txt").write_text("ignore\n")
        log = source / "app.log"
        log.write_text("ignore\n")

        ignore_filter = IgnoreFilter(source)
        assert ignore_filter.should_ignore(secret / "key.txt")
        assert ignore_filter.should_ignore(log)
        assert not ignore_filter.should_ignore(source / "readme.txt")

    def test_no_ignore_file_ignores_nothing(self, tmp_dir):
        source = tmp_dir / "src"
        source.mkdir()
        (source / "file.txt").write_text("keep\n")
        assert not (source / ".eprignore").exists()
        ignore_filter = IgnoreFilter(source)
        assert not ignore_filter.should_ignore(source / "file.txt")

    def test_dotfiles_are_honored(self, tmp_dir):
        source = tmp_dir / "src"
        source.mkdir()
        (source / ".eprignore").write_text("__pycache__/\n*.pyc\n")
        cache = source / "__pycache__"
        cache.mkdir()
        (cache / "mod.cpython-312.pyc").write_bytes(b"\x00")

        ignore_filter = IgnoreFilter(source)
        assert ignore_filter.should_ignore(cache / "mod.cpython-312.pyc")
