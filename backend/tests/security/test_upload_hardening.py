"""Phase 49 — upload size/type enforcement re-tested + traversal at the API level."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from .helpers import login, make_project, setup, tag, teardown

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _upload(client, pid, headers, filename, content, content_type):
    with patch("app.api.v1.materials.process_pdf") as mock_task:
        mock_task.delay.return_value = MagicMock(id="mock-id")
        return client.post(
            f"/api/v1/projects/{pid}/materials",
            files={"file": (filename, content, content_type)},
            headers=headers,
        )


def test_wrong_extension_and_type_and_magic_rejected():
    tmpdir = tempfile.mkdtemp(prefix="sec_upload_")
    client, engine = setup(tmpdir)
    try:
        h = login(client, tag("sec-up"))
        _, pid = make_project(client, h)
        assert _upload(client, pid, h, "notes.txt", b"plain text", "text/plain").status_code == 400
        assert _upload(client, pid, h, "notes.pdf", b"plain text", "text/plain").status_code == 400
        resp = _upload(client, pid, h, "notes.pdf", b"not a pdf at all", "application/pdf")
        assert resp.status_code == 400, resp.text
        assert resp.json()["error"]["code"] == "bad_request"
    finally:
        teardown(engine)


def test_oversized_pdf_rejected_with_413():
    tmpdir = tempfile.mkdtemp(prefix="sec_upload_")
    client, engine = setup(tmpdir)
    try:
        h = login(client, tag("sec-big"))
        _, pid = make_project(client, h)
        big = b"%PDF" + b"\x00" * (10 * 1024 * 1024 + 1)
        resp = _upload(client, pid, h, "big.pdf", big, "application/pdf")
        assert resp.status_code == 413, resp.status_code
        assert resp.json()["error"]["code"] == "payload_too_large"
    finally:
        teardown(engine)


def test_traversal_filename_never_escapes_project_dir():
    tmpdir = tempfile.mkdtemp(prefix="sec_upload_")
    client, engine = setup(tmpdir)
    try:
        h = login(client, tag("sec-trav"))
        _, pid = make_project(client, h)
        resp = _upload(client, pid, h, "../../evil.pdf", MINIMAL_PDF, "application/pdf")
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["filename"] == "evil.pdf"
        assert ".." not in body["storage_path"]
        real = os.path.realpath(body["storage_path"])
        assert real.startswith(os.path.realpath(os.path.join(tmpdir, pid)) + os.sep)
        assert os.path.exists(real)
    finally:
        teardown(engine)


def test_upload_requires_auth_and_ownership():
    tmpdir = tempfile.mkdtemp(prefix="sec_upload_")
    client, engine = setup(tmpdir)
    try:
        ha = login(client, tag("sec-own"))
        hb = login(client, tag("sec-stranger"))
        _, pid = make_project(client, ha)
        resp = _upload(client, pid, hb, "doc.pdf", MINIMAL_PDF, "application/pdf")
        assert resp.status_code == 404, resp.text  # existence hidden, not 403
        assert resp.json()["error"]["code"] == "not_found"
        resp = client.post(
            f"/api/v1/projects/{pid}/materials",
            files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "authentication_required"
    finally:
        teardown(engine)
