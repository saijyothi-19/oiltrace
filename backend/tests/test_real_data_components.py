"""
OILTRACE — Real-Data Components & Provenance Test Suite (SIH26143).
Validates:
1. Copernicus CDSE Sentinel-1 Search and latest acquisition endpoints.
2. Environmental Multi-Provider Engine (Open-Meteo, Synthetic Fallback, Composite).
3. Geometric Spill Characterization & Scientific Spill Age Estimation.
4. AIS Vessel Trajectory Anomaly Detection & Track Reconstruction.
5. Reverse Hindcasting & Attribution Engine with Origin Confidence.
6. System Data Provenance & Operational State API.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.vessel import Vessel, AisPosition
from app.services.copernicus_service import CopernicusSatelliteService
from app.services.environmental_service import (
    SyntheticEnvironmentalProvider,
    OpenMeteoMarineProvider,
    CompositeEnvironmentalProvider,
)
from app.geospatial.characterization import SpillAgeEstimator, SpillCharacterizationEngine
from app.ais.anomaly import VesselBehaviourAnomalyDetector


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_copernicus_service_bbox_math():
    """Verify centroid-radius to bounding box calculation."""
    min_lon, min_lat, max_lon, max_lat = CopernicusSatelliteService.bbox_from_point_radius(
        lat=18.9, lon=72.8, radius_km=50.0
    )
    assert min_lon < 72.8 < max_lon
    assert min_lat < 18.9 < max_lat
    # Check degree span is approximately 0.9 deg lat (~100km total box)
    assert 0.8 < (max_lat - min_lat) < 1.0


def test_copernicus_search_api_endpoint(client):
    """Verify /api/satellite/cdse/search returns proper schema and acquisitions."""
    resp = client.get(
        "/api/satellite/cdse/search",
        params={
            "min_lon": 72.0,
            "min_lat": 18.0,
            "max_lon": 73.5,
            "max_lat": 19.5,
            "limit": 10,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "acquisitions" in data
    assert "total_found" in data
    assert "is_demo" in data
    assert "data_source" in data
    assert isinstance(data["acquisitions"], list)
    if data["acquisitions"]:
        p = data["acquisitions"][0]
        assert "acquisition_id" in p or "product_id" in p
        assert "product_id" in p
        assert "satellite" in p
        assert "acquisition_time" in p
        assert "polarization" in p


def test_copernicus_latest_acquisition_endpoint(client):
    """Verify /api/satellite/latest returns scientifically honest naming and metadata."""
    resp = client.get("/api/satellite/latest", params={"latitude": 18.9, "longitude": 72.8, "radius_km": 60})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_title"] == "Latest Available Sentinel-1 Acquisition"
    assert "acquisition" in data
    if data["acquisition"]:
        acq = data["acquisition"]
        assert "satellite" in acq
        assert "Sentinel-1" in acq["satellite"]
        assert "data_source" in data


def test_environmental_providers():
    """Verify synthetic and composite environmental engine output."""
    now = datetime.now(timezone.utc)
    
    # 1. Synthetic Provider (Monsoon climatology)
    synth = SyntheticEnvironmentalProvider()
    cond = synth.get_conditions(lat=19.0, lon=72.5, timestamp=now)
    assert "Climatological" in cond["source"]
    assert "wind" in cond
    assert "currents" in cond
    assert cond["currents"]["speed_mps"] > 0
    assert 0 <= cond["currents"]["direction_deg"] <= 360

    # 2. Composite Provider (Cascading fallback)
    composite = CompositeEnvironmentalProvider()
    c_cond = composite.get_conditions(lat=19.0, lon=72.5, timestamp=now)
    assert "u" in c_cond["currents"]
    assert "v" in c_cond["currents"]
    assert "speed_mps" in c_cond["currents"]


def test_environment_api_endpoints(client):
    """Verify /api/environment/current and /api/environment/history."""
    resp = client.get("/api/environment/current", params={"latitude": 18.9, "longitude": 72.8, "force_demo": True})
    assert resp.status_code == 200
    data = resp.json()
    assert "currents" in data
    assert "wind" in data
    assert "source" in data
    assert data["is_demo"] is True

    hist_resp = client.get("/api/environment/history", params={"latitude": 18.9, "longitude": 72.8, "step_hours": 6, "force_demo": True})
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert isinstance(hist_data, list)
    assert len(hist_data) >= 3


def test_spill_age_estimator():
    """Verify scientific spill age estimation calculations and caveats."""
    res = SpillAgeEstimator.estimate_age(
        area_km2=8.5,
        perimeter_km=14.0,
        elongation=5.2,
        major_axis_km=6.8,
        wind_speed_mps=6.5,
    )
    assert res["status"] == "ESTIMATED_RANGE"
    assert "estimated_age_range_hours" in res
    min_h, max_h = res["estimated_age_range_hours"]
    assert min_h < max_h
    assert "caveat" in res
    assert "methodology" in res


def test_ais_anomaly_detector():
    """Verify rule-based maritime AIS behavior anomaly detection."""
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(hours=3)
    
    class MockPos:
        def __init__(self, ts, lon, lat, speed, course):
            self.timestamp = ts
            self.position = {"coordinates": [lon, lat]}
            self.speed = speed
            self.course = course

    track = [
        MockPos(t0 + timedelta(minutes=0), 72.70, 18.80, 14.2, 180.0),
        MockPos(t0 + timedelta(minutes=30), 72.70, 18.82, 13.8, 180.0),
        MockPos(t0 + timedelta(minutes=60), 72.70, 18.83, 1.2, 190.0),
        MockPos(t0 + timedelta(minutes=90), 72.71, 18.83, 0.8, 210.0),
        MockPos(t0 + timedelta(minutes=120), 72.71, 18.84, 1.1, 220.0),
        MockPos(t0 + timedelta(minutes=150), 72.73, 18.88, 12.5, 180.0),
    ]

    analysis = VesselBehaviourAnomalyDetector.analyze_trajectory(track, origin_lat=18.83, origin_lon=72.70)
    assert analysis["has_anomaly"] is True
    assert len(analysis["anomaly_signals"]) > 0
    types = [a["type"] for a in analysis["anomaly_signals"]]
    assert "SUDDEN_SPEED_REDUCTION" in types or "LOITERING_PATTERN" in types


def test_ais_track_and_anomalies_api(client):
    """Verify AIS vessel track and anomalies endpoints."""
    # Seed vessel and waypoints if not present
    db = SessionLocal()
    try:
        v = db.query(Vessel).filter(Vessel.mmsi == "419000101").first()
        if not v:
            v = Vessel(mmsi="419000101", name="PACIFIC JEWEL", ship_type="Tanker", flag="India")
            db.add(v)
            db.flush()
        
        pos_count = db.query(AisPosition).filter(AisPosition.vessel_id == v.id).count()
        if pos_count == 0:
            now = datetime.now(timezone.utc)
            for i in range(5):
                p = AisPosition(
                    vessel_id=v.id,
                    timestamp=now - timedelta(minutes=30 * (5 - i)),
                    position={"type": "Point", "coordinates": [72.8 + i * 0.02, 18.9 + i * 0.02]},
                    speed=12.0 - (2.0 if i == 2 else 0),
                    course=160.0,
                )
                db.add(p)
        db.commit()
    finally:
        db.close()

    track_resp = client.get("/api/ais/track/419000101")
    assert track_resp.status_code == 200
    positions = track_resp.json()
    assert isinstance(positions, list)
    assert len(positions) > 0

    anom_resp = client.get("/api/ais/vessel/419000101/anomalies")
    assert anom_resp.status_code == 200
    anom_data = anom_resp.json()
    assert "has_anomaly" in anom_data
    assert "vessel" in anom_data
    assert anom_data["vessel"]["mmsi"] == "419000101"


def test_hindcast_api_alias(client):
    """Verify POST /api/drift/hindcast alias endpoint."""
    spill = client.post("/api/spills", json={
        "confidence": 0.92,
        "area_km2": 9.5,
        "perimeter_km": 12.0,
        "centroid": {"type": "Point", "coordinates": [72.8, 18.9]},
        "spill_geometry": {
            "type": "Polygon",
            "coordinates": [[[72.75, 18.85], [72.85, 18.85], [72.85, 18.95], [72.75, 18.95], [72.75, 18.85]]]
        },
        "status": "DETECTED",
    }).json()
    
    hind_resp = client.post("/api/drift/hindcast", json={
        "spill_event_id": spill["id"],
        "duration_hours": 6.0,
        "particle_count": 30,
    })
    assert hind_resp.status_code == 200
    hind_data = hind_resp.json()
    assert hind_data["simulation_type"] == "BACKWARD"
    assert "origin_probability_geometry" in hind_data
    assert "parameters_json" in hind_data
    params = hind_data["parameters_json"]
    assert "origin" in params
    assert "time_window" in params
    assert "uncertainty_km" in params


def test_attribution_run_api(client):
    """Verify POST /api/attribution/run endpoint."""
    spill = client.post("/api/spills", json={
        "confidence": 0.95,
        "area_km2": 6.0,
        "perimeter_km": 10.0,
        "centroid": {"type": "Point", "coordinates": [72.8, 18.9]},
        "spill_geometry": {
            "type": "Polygon",
            "coordinates": [[[72.75, 18.85], [72.85, 18.85], [72.85, 18.95], [72.75, 18.95], [72.75, 18.85]]]
        },
        "status": "DETECTED",
    }).json()

    # Pre-run hindcast for spill so attribution has origin geometry
    client.post("/api/drift/hindcast", json={
        "spill_event_id": spill["id"],
        "duration_hours": 6.0,
        "particle_count": 25,
    })

    run_resp = client.post("/api/attribution/run", json={
        "spill_event_id": spill["id"],
        "spatial_radius_km": 50.0,
        "temporal_window_hours": 12.0,
    })
    assert run_resp.status_code == 200
    candidates = run_resp.json()
    assert isinstance(candidates, list)


def test_system_provenance_api(client):
    """Verify GET /api/system/provenance metadata integrity."""
    resp = client.get("/api/system/provenance")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_status" in data
    assert "timestamp" in data
    assert "provenance_layers" in data
    layers = data["provenance_layers"]
    assert "satellite" in layers
    assert "environment" in layers
    assert "ais" in layers
    assert "ml_model" in layers
    assert layers["satellite"]["layer"] == "Satellite Imagery"
    assert "mode_badge" in layers["satellite"]
    assert "mode_badge" in layers["ml_model"]
