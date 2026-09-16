"""Phase 49 — materials are metadata-only over the API: no route serves file
bytes, and metadata is strictly owner-scoped."""

import tempfile
from unittest.mock import MagicMock, patch

from .helpers import login, make_project, setup, tag, teardown

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _upload(client, pid, headers):
    with patch("app.api.v1.materials.process_pdf") as mock_task:
        mock_task.delay.return_value = MagicMock(id="mock-id")
        resp = client.post(
            f"/api/v1/projects/{pid}/materials",
            files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_metadata_owner_scoped_and_json_only():
    tmpdir = tempfile.mkdtemp(prefix="sec_mat_")
    client, engine = setup(tmpdir)
    try:
        ha = login(client, tag("sec-mown"))
        hb = login(client, tag("sec-mstr"))
        _, pid = make_project(client, ha)
        mat = _upload(client, pid, ha)

        resp = client.get(f"/api/v1/projects/{pid}/materials", headers=ha)
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        assert [m["id"] for m in resp.json()] == [mat["id"]]
        assert b"%PDF" not in resp.content  # metadata only, never bytes

        assert client.get(f"/api/v1/projects/{pid}/materials", headers=hb).status_code == 404
        assert client.get(f"/api/v1/projects/{pid}/materials").status_code == 401
    finally:
        teardown(engine)


def test_no_route_serves_file_bytes():
    """Plausible download paths must not exist and no response may carry %PDF."""
    tmpdir = tempfile.mkdtemp(prefix="sec_mat_")
    client, engine = setup(tmpdir)
    try:
        h = login(client, tag("sec-mbytes"))
        _, pid = make_project(client, h)
        mat = _upload(client, pid, h)
        candidates = [
            f"/api/v1/projects/{pid}/materials/{mat['id']}",
            f"/api/v1/projects/{pid}/materials/{mat['id']}/download",
            f"/api/v1/projects/{pid}/materials/{mat['id']}/file",
            f"/api/v1/materials/{mat['id']}",
            "/uploads/doc.pdf",
        ]
        for path in candidates:
            resp = client.get(path, headers=h)
            assert resp.status_code == 404, path
            assert not resp.content.startswith(b"%PDF"), path
    finally:
        teardown(engine)
