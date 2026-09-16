import pytest
from app.models.investigation import InvestigationStatus

def test_investigations_lifecycle(client):
    # First ensure we have a valid spill event
    spills_resp = client.get("/api/spills")
    assert spills_resp.status_code == 200
    spills = spills_resp.json()
    if not spills:
        # Load demo if no spills
        client.post("/api/demo/load")
        spills = client.get("/api/spills").json()

    spill_id = spills[0]["id"]

    # 1. List investigations
    list_resp = client.get("/api/investigations")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)

    # 2. Create a new investigation
    create_payload = {
        "spill_event_id": spill_id,
        "status": InvestigationStatus.NEW.value,
        "notes": "Initial satellite detection recorded. Opening investigation."
    }
    create_resp = client.post("/api/investigations", json=create_payload)
    # Could be 201 Created or 200 OK (if already created for this spill)
    assert create_resp.status_code in (200, 201)
    created = create_resp.json()
    inv_id = created["id"]
    assert created["spill_event_id"] == spill_id

    # 3. Retrieve specific investigation
    get_resp = client.get(f"/api/investigations/{inv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == inv_id

    # 4. Update investigation
    update_payload = {
        "status": InvestigationStatus.UNDER_REVIEW.value,
        "notes": "Backward drift hindcasting completed. Correlating with AIS transponders.",
    }
    update_resp = client.patch(f"/api/investigations/{inv_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == InvestigationStatus.UNDER_REVIEW.value
    assert "Backward drift" in updated["notes"]

    # 5. Filter by status
    filter_resp = client.get(f"/api/investigations?status={InvestigationStatus.UNDER_REVIEW.value}")
    assert filter_resp.status_code == 200
    filtered = filter_resp.json()
    assert any(i["id"] == inv_id for i in filtered)

def test_report_generation_endpoints(client):
    # Find any spill in the database
    spills_resp = client.get("/api/spills")
    assert spills_resp.status_code == 200
    spills = spills_resp.json()
    assert len(spills) > 0

    spill_id = spills[0]["id"]

    # Test JSON Dossier
    report_json_resp = client.get(f"/api/reports/{spill_id}")
    assert report_json_resp.status_code == 200
    dossier = report_json_resp.json()

    assert "report_id" in dossier
    assert "disclaimer" in dossier
    assert "not establish legal responsibility" in dossier["disclaimer"].lower()
    assert "spill_incident" in dossier
    assert "oceanographic_drift" in dossier
    assert "ranked_candidate_vessels" in dossier
    assert "scientific_limitations" in dossier
    assert len(dossier["scientific_limitations"]) >= 3

    # Test Printable HTML Dossier
    report_html_resp = client.get(f"/api/reports/{spill_id}/html")
    assert report_html_resp.status_code == 200
    assert "text/html" in report_html_resp.headers["content-type"]
    html_content = report_html_resp.text
    assert "Marine Oil Spill Attribution Dossier" in html_content
    assert "OILTRACE" in html_content
    assert "DISCLAIMER" in html_content
    assert "Ranked Candidate Vessels" in html_content
