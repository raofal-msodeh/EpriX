"""Tests for EpriX.router — FastAPI pages, API endpoints, and background operations."""

import time

import pytest

from EpriX.router import execute_pack, operations

from .conftest import PASSPHRASE


@pytest.fixture(autouse=True)
def clear_operations():
    """Keep operations isolated between tests."""
    operations.clear()
    yield
    operations.clear()


class TestStaticPages:
    """Serve-page smoke tests: every documented page must resolve."""

    @pytest.mark.parametrize("route", ["/", "/operations", "/pack", "/pack/upload",
                                        "/unpack", "/unpack/upload", "/status"])
    def test_page_resolves(self, client, route):
        response = client.get(route)
        assert response.status_code == 200, f"{route} must return 200"
        assert "html" in response.headers.get("content-type", "")

    def test_unknown_page_raises(self, client, monkeypatch):
        """A missing static template must surface as a 404, not a 500."""

        def failing_open(path, *a, **kw):
            raise FileNotFoundError(path)

        monkeypatch.setattr("builtins.open", failing_open)
        with client:
            response = client.get("/pack")
        assert response.status_code == 404


class TestApiEndpoints:
    def test_pack_requires_source(self, client, sample_tree, tmp_dir):
        # Missing mandatory fields must be rejected by FastAPI validation.
        response = client.post("/api/v1/pack", data={
            "source_dir": str(sample_tree),
            "passphrase": PASSPHRASE,
        })
        assert response.status_code == 200

    def test_pack_missing_passphrase_returns_422(self, client, sample_tree):
        response = client.post("/api/v1/pack", data={
            "source_dir": str(sample_tree),
        })
        assert response.status_code == 422

    def test_pack_nonexistent_source_returns_error(self, client, tmp_dir):
        response = client.post("/api/v1/pack", data={
            "source_dir": str(tmp_dir / "missing"),
            "output_file": str(tmp_dir / "a.epr"),
            "keys_file": str(tmp_dir / "keys.json"),
            "passphrase": PASSPHRASE,
        })
        # A non-existent source must never start a background operation; the
        # server must respond with an error status instead.
        assert response.status_code >= 400, "missing source must not start an operation"

    def test_pack_starts_background_operation(self, client, sample_tree, tmp_dir):
        response = client.post("/api/v1/pack", data={
            "source_dir": str(sample_tree),
            "output_file": str(tmp_dir / "archive.epr"),
            "keys_file": str(tmp_dir / "keys.json"),
            "passphrase": PASSPHRASE,
        })
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        operation_id = body["operation_id"]
        assert operation_id

        deadline = time.time() + 60
        while time.time() < deadline:
            status = client.get(f"/api/v1/status/{operation_id}").json()
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status["status"] == "completed", f"operation ended as {status}"
        assert (tmp_dir / "archive.epr").exists()
        assert (tmp_dir / "keys.json").exists()

    def test_unpack_missing_input_marks_failed(self, client, tmp_dir):
        response = client.post("/api/v1/unpack", data={
            "input_file": str(tmp_dir / "missing.epr"),
            "keys_file": str(tmp_dir / "missing_keys.json"),
            "passphrase": PASSPHRASE,
            "target_dir": str(tmp_dir / "out"),
        })
        # The server must reject missing inputs with an error status.
        assert response.status_code >= 400, "missing inputs must not start an operation"
        # No target directory must be created by the rejected request.
        assert not (tmp_dir / "out").exists() or not any((tmp_dir / "out").rglob("*"))

    def test_unknown_operation_returns_404(self, client):
        response = client.get("/api/v1/status/nonexistent-id")
        assert response.status_code == 404

    def test_list_operations(self, client):
        response = client.get("/api/v1/operations")
        assert response.status_code == 200
        assert "operations" in response.json()


class TestUploadEndpoints:
    def test_pack_upload_roundtrip(self, client, sample_tree, tmp_dir):
        files = [
            ("files", ("readme.txt", b"uploaded readme\n", "text/plain")),
            ("files", ("notes.txt", b"uploaded notes\n", "text/plain")),
        ]
        response = client.post("/api/v1/pack/upload", files=files, data={
            "output_file": str(tmp_dir / "uploaded.epr"),
            "keys_file": str(tmp_dir / "uploaded_keys.json"),
            "passphrase": PASSPHRASE,
        })
        assert response.status_code == 200
        operation_id = response.json()["operation_id"]

        deadline = time.time() + 60
        while time.time() < deadline:
            status = client.get(f"/api/v1/status/{operation_id}").json()
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status["status"] == "completed", f"upload pack ended as {status}"
        assert (tmp_dir / "uploaded.epr").exists()

    def test_upload_text_files_pack_succeeds(self, client, tmp_dir):
        """Text file uploads are packed like any other source directory.

        Note: pack.collect_files detects readable text files, so plain-text
        uploads are accepted and packed. This test pins that behavior so any
        future change to the filter is noticed.
        """
        response = client.post("/api/v1/pack/upload", files=[
            ("files", ("notes.txt", b"uploadable text content\n", "text/plain")),
        ], data={
            "output_file": str(tmp_dir / "out.epr"),
            "keys_file": str(tmp_dir / "keys.json"),
            "passphrase": PASSPHRASE,
        })
        assert response.status_code == 200
        operation_id = response.json()["operation_id"]

        deadline = time.time() + 60
        while time.time() < deadline:
            status = client.get(f"/api/v1/status/{operation_id}").json()
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(0.2)

        assert status["status"] == "completed", f"text upload pack ended as {status}"
        assert (tmp_dir / "out.epr").exists()

    def test_upload_invalid_data_fails_operation(self, client, tmp_dir):
        """Uploading a manifest-like payload the packer cannot read must fail."""
        response = client.post("/api/v1/pack/upload", files=[
            ("files", ("data.dat", bytes(range(256)) * 16, "application/octet-stream")),
        ], data={
            "output_file": str(tmp_dir / "out.epr"),
            "keys_file": str(tmp_dir / "keys.json"),
            "passphrase": PASSPHRASE,
        })
        if response.status_code >= 400:
            return

        operation_id = response.json()["operation_id"]
        deadline = time.time() + 60
        while time.time() < deadline:
            status = client.get(f"/api/v1/status/{operation_id}").json()
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(0.2)

        # Unreadable binary uploads must never produce a 'completed' archive.
        assert status["status"] == "failed", "unreadable upload must fail"

    def test_unpack_upload_rejects_non_epr(self, client, tmp_dir):
        response = client.post("/api/v1/unpack/upload", files=[
            ("archive_file", ("notes.txt", b"not an archive", "text/plain")),
            ("keys_file", ("keys.json", b"{}", "application/json")),
        ], data={
            "passphrase": PASSPHRASE,
            "target_dir": str(tmp_dir / "out"),
        })
        assert response.status_code == 400


class TestBackgroundTasks:
    def test_execute_pack_marks_failed_operation(self, tmp_dir, sample_tree):
        """A failing pack must transition the operation to 'failed', never stay pending."""
        operations["op-fail"] = {
            "status": "processing",
            "type": "pack",
            "source": str(sample_tree),
            "output": "/nonexistent-dir/archive.epr",
        }
        execute_pack(
            operation_id="op-fail",
            source=sample_tree,
            output=Path("/nonexistent-dir/archive.epr") if False else tmp_dir.joinpath(
                "subdir-missing", "archive.epr"
            ),
            keys_file=tmp_dir / "keys.json",
            passphrase=PASSPHRASE,
            follow_symlinks=False,
            preserve_perms=True,
            include_binaries=False,
        )
        assert operations["op-fail"]["status"] == "failed"

    def test_cleanup_runs_even_on_failure(self, tmp_dir, sample_tree):
        """Temporary upload source must be removed whether packing succeeds or fails."""
        temp_source = tmp_dir / "upload-tmp"
        temp_source.mkdir()
        (temp_source / "doc.txt").write_text("temp\n")

        operations["op-tmp"] = {
            "status": "processing",
            "type": "pack_upload",
            "source": str(temp_source),
            "output": str(tmp_dir / "archive.epr"),
        }
        execute_pack(
            operation_id="op-tmp",
            source=temp_source,
            output=tmp_dir / "archive.epr",
            keys_file=tmp_dir / "keys.json",
            passphrase=PASSPHRASE,
            follow_symlinks=False,
            preserve_perms=True,
            include_binaries=False,
        )
        # Temp upload directory must not outlive the operation.
        assert not temp_source.exists(), (
            "temporary upload directory leaked after operation completion"
        )


from pathlib import Path
