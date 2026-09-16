def test_demo_load_endpoint(client):
    """
    Verify that calling /api/demo/load successfully provisions
    the end-to-end offshore Mumbai demonstration scenario.
    """
    resp = client.post("/api/demo/load")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert "spill_id" in data
    assert data["vessels_loaded"] == 5
    assert data["candidates_ranked"] == 5
    assert "Synthetic demonstration data" in data["synthetic_disclaimer"]

def test_demo_spill_and_drift_data(client):
    """
    Verify that the demo spill has associated drift simulations and candidates.
    """
    demo_load = client.post("/api/demo/load").json()
    spill_id = demo_load["spill_id"]

    spill_resp = client.get(f"/api/spills/{spill_id}")
    assert spill_resp.status_code == 200
    spill = spill_resp.json()
    assert spill["area_km2"] > 0
    assert spill["perimeter_km"] > 0
    assert spill["spill_geometry"] is not None

    # Check candidate attribution for this spill
    cand_resp = client.get(f"/api/attribution/{spill_id}/candidates")
    assert cand_resp.status_code == 200
    candidates = cand_resp.json()
    assert len(candidates) >= 5

    for cand in candidates:
        assert 0.0 <= cand["overall_score"] <= 100.0
        assert 0.0 <= cand["spatial_score"] <= 100.0
        assert 0.0 <= cand["temporal_score"] <= 100.0
        assert 0.0 <= cand["trajectory_score"] <= 100.0
        assert "explanation_json" in cand
        assert "explanation_points" in cand["explanation_json"]
        assert len(cand["explanation_json"]["explanation_points"]) > 0

    # Top candidate should have high score
    top_cand = candidates[0]
    assert top_cand["priority"] in ["HIGH", "CRITICAL"]

def test_vessel_profiles_and_trajectories(client):
    """
    Verify vessel list and AIS trajectory endpoint for demo vessels.
    """
    vessels_resp = client.get("/api/ais/vessels")
    assert vessels_resp.status_code == 200
    vessels = vessels_resp.json()
    assert len(vessels) >= 5

    arabian_pride = next((v for v in vessels if "ARABIAN PRIDE" in v["name"].upper()), None)
    assert arabian_pride is not None
    assert arabian_pride["mmsi"] == "419001888"

    # Query vessel details
    vessel_resp = client.get(f"/api/ais/vessel/{arabian_pride['mmsi']}")
    assert vessel_resp.status_code == 200
    vessel_info = vessel_resp.json()
    assert vessel_info["mmsi"] == "419001888"
    assert vessel_info["name"] == "MT ARABIAN PRIDE"

    # Query track positions
    track_resp = client.get(f"/api/ais/vessel/{arabian_pride['mmsi']}/track")
    assert track_resp.status_code == 200
    positions = track_resp.json()
    assert isinstance(positions, list)
    assert len(positions) >= 2
    assert "position" in positions[0]
    assert "coordinates" in positions[0]["position"]
    coords = positions[0]["position"]["coordinates"]
    assert len(coords) == 2  # [lon, lat]

    # Check for AIS-gap vessel MT AL-BAHR
    al_bahr = next((v for v in vessels if "AL-BAHR" in v["name"].upper()), None)
    assert al_bahr is not None
