"""Phase 49 — guessed IDs never cross the ownership boundary (404, never 403/data)."""

import tempfile
import uuid
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import sessionmaker

from app.services import job_service

from .helpers import login, make_project, setup, tag, teardown

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def test_guessed_ids_stay_invisible():
    tmpdir = tempfile.mkdtemp(prefix="sec_xproj_")
    client, engine = setup(tmpdir)
    try:
        ha = login(client, tag("sec-xA"))
        hb = login(client, tag("sec-xB"))
        space_a, pid_a = make_project(client, ha, suffix="XA")
        make_project(client, hb, suffix="XB")

        with patch("app.api.v1.materials.process_pdf") as mock_task:
            mock_task.delay.return_value = MagicMock(id="mock-id")
            resp = client.post(
                f"/api/v1/projects/{pid_a}/materials",
                files={"file": ("doc.pdf", MINIMAL_PDF, "application/pdf")},
                headers=ha,
            )
        assert resp.status_code == 201, resp.text
        material_id = resp.json()["id"]

        Sess = sessionmaker(bind=engine)
        db = Sess()
        try:
            job = job_service.create_job(db, job_type="process_pdf", material_id=uuid.UUID(material_id))
            db.commit()
            job_id = str(job.id)
        finally:
            db.close()

        foreign = str(uuid.uuid4())
        checks = [
            ("GET", f"/api/v1/spaces/{space_a}", None),
            ("GET", f"/api/v1/spaces/{space_a}/projects", None),
            ("GET", f"/api/v1/projects/{pid_a}", None),
            ("GET", f"/api/v1/projects/{pid_a}/materials", None),
            ("GET", f"/api/v1/projects/{pid_a}/structure", None),
            ("GET", f"/api/v1/projects/{pid_a}/dashboard", None),
            ("GET", f"/api/v1/projects/{pid_a}/growth", None),
            ("GET", f"/api/v1/projects/{pid_a}/analytics", None),
            ("GET", f"/api/v1/jobs/{job_id}", None),
            ("GET", f"/api/v1/jobs/{foreign}", None),
            ("POST", f"/api/v1/projects/{pid_a}/tutor/ask", {"question": "Hi?"}),
            ("POST", f"/api/v1/projects/{pid_a}/quizzes/generate",
             {"concept_id": foreign, "num_questions": 5, "mode": "practice"}),
            ("POST", f"/api/v1/projects/{pid_a}/assessment/open-ended",
             {"concept_id": foreign, "answer_text": "An answer."}),
        ]
        for method, path, body in checks:
            resp = client.request(method, path, json=body, headers=hb)
            assert resp.status_code == 404, f"{method} {path} -> {resp.status_code}"
            assert resp.json()["error"]["code"] == "not_found"

        # List endpoints leak nothing: B's spaces contain only B's space.
        resp = client.get("/api/v1/spaces", headers=hb)
        assert resp.status_code == 200
        assert space_a not in [s["id"] for s in resp.json()]
    finally:
        teardown(engine)
