import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.environmental_service import env_provider
from app.drift.simulation import LagrangianDriftSimulator
from app.attribution.scorer import AttributionScoringEngine
from app.models.vessel import Vessel, AisPosition
from app.models.attribution import PriorityLevel

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_environmental_provider():
    now = datetime.now(timezone.utc)
    cond = env_provider.get_conditions(lat=19.0, lon=72.5, timestamp=now)
    assert "wind" in cond
    assert "currents" in cond
    assert cond["wind"]["speed_mps"] > 0
    assert cond["currents"]["speed_mps"] > 0

def test_lagrangian_backward_hindcast():
    simulator = LagrangianDriftSimulator()
    now = datetime.now(timezone.utc)
    sim = simulator.simulate(
        center_lon=72.8,
        center_lat=18.9,
        start_time=now,
        duration_hours=6.0,
        timestep_minutes=30,
        particle_count=50,
        is_backward=True,
    )
    assert sim["simulation_type"] == "BACKWARD"
    assert sim["particle_count"] == 50
    assert len(sim["particles"]) == 50
    assert sim["origin_probability_geometry"] is not None
    assert sim["origin_probability_geometry"]["type"] == "Polygon"

def test_attribution_scoring_engine():
    scorer = AttributionScoringEngine()
    now = datetime.now(timezone.utc)
    origin_time = now - timedelta(hours=4)

    vessel = Vessel(id=99, mmsi="419000999", name="TEST TANKER", ship_type="Tanker")
    # Positions passing through origin
    p1 = AisPosition(
        vessel_id=99,
        timestamp=origin_time - timedelta(hours=1),
        position={"type": "Point", "coordinates": [72.78, 18.88]},
        speed=13.5,
        course=150.0,
    )
    p2 = AisPosition(
        vessel_id=99,
        timestamp=origin_time,
        position={"type": "Point", "coordinates": [72.80, 18.90]},  # Exact match
        speed=13.0,
        course=150.0,
    )
    p3 = AisPosition(
        vessel_id=99,
        timestamp=origin_time + timedelta(hours=1),
        position={"type": "Point", "coordinates": [72.82, 18.92]},
        speed=13.2,
        course=150.0,
    )

    origin_geom = {
        "type": "Polygon",
        "coordinates": [[[72.75, 18.85], [72.85, 18.85], [72.85, 18.95], [72.75, 18.95], [72.75, 18.85]]]
    }

    result = scorer.evaluate_vessel(
        vessel=vessel,
        positions=[p1, p2, p3],
        origin_geometry_dict=origin_geom,
        origin_center_lat=18.90,
        origin_center_lon=72.80,
        origin_time=origin_time,
    )

    assert result["overall_score"] > 80.0
    assert result["priority"] == PriorityLevel.HIGH
    assert result["spatial_score"] > 90.0
    assert result["temporal_score"] > 90.0
    assert len(result["explanation"]["explanation_points"]) >= 3
    assert len(result["explanation"]["evidence_breakdown"]) == 5

def test_attribution_end_to_end_api(client):
    # 1. Create spill
    create_payload = {
        "confidence": 0.94,
        "area_km2": 12.0,
        "perimeter_km": 15.0,
        "centroid": {"type": "Point", "coordinates": [72.75, 18.95]},
        "spill_geometry": {
            "type": "Polygon",
            "coordinates": [[[72.7, 18.9], [72.8, 18.9], [72.8, 19.0], [72.7, 19.0], [72.7, 18.9]]]
        },
        "status": "DETECTED",
    }
    spill_res = client.post("/api/spills", json=create_payload)
    spill_id = spill_res.json()["id"]

    # 2. Run backward drift
    drift_res = client.post("/api/drift/backward", json={"spill_event_id": spill_id, "duration_hours": 6.0})
    assert drift_res.status_code == 200
    assert drift_res.json()["simulation_type"] == "BACKWARD"

    # 3. Run attribution
    attr_res = client.post(f"/api/attribution/analyze/{spill_id}")
    assert attr_res.status_code == 200
    candidates = attr_res.json()
    assert isinstance(candidates, list)
