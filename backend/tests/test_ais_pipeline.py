import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.ais.cleaner import AisRecordCleaner
from app.ais.trajectory import TrajectoryBuilder, haversine_distance_km

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_ais_cleaner_valid():
    raw = {
        "mmsi": "419000123",
        "latitude": 18.9220,
        "longitude": 72.8346,
        "speed": 12.4,
        "course": 210.0,
        "heading": 212.0,
        "timestamp": "2026-09-14T10:00:00Z",
        "name": "ARABIAN CARRIER",
        "ship_type": "Tanker",
    }
    cleaned = AisRecordCleaner.clean_record(raw)
    assert cleaned is not None
    assert cleaned["mmsi"] == "419000123"
    assert cleaned["lat"] == 18.9220
    assert cleaned["lon"] == 72.8346
    assert cleaned["speed"] == 12.4

def test_ais_cleaner_filters_invalid_data():
    # Invalid MMSI
    assert AisRecordCleaner.clean_record({"mmsi": "123", "latitude": 18.0, "longitude": 72.0, "timestamp": "2026-09-14T10:00:00Z"}) is None
    # Invalid Latitude (> 90)
    assert AisRecordCleaner.clean_record({"mmsi": "419000123", "latitude": 95.0, "longitude": 72.0, "timestamp": "2026-09-14T10:00:00Z"}) is None
    # Physically impossible commercial speed (> 50 kts)
    assert AisRecordCleaner.clean_record({"mmsi": "419000123", "latitude": 18.0, "longitude": 72.0, "speed": 120.0, "timestamp": "2026-09-14T10:00:00Z"}) is None
    # Null island (0, 0)
    assert AisRecordCleaner.clean_record({"mmsi": "419000123", "latitude": 0.0, "longitude": 0.0, "timestamp": "2026-09-14T10:00:00Z"}) is None

def test_haversine_distance():
    # Mumbai to Goa ~400 km
    mumbai_lat, mumbai_lon = 18.9220, 72.8346
    goa_lat, goa_lon = 15.4989, 73.8278
    dist = haversine_distance_km(mumbai_lat, mumbai_lon, goa_lat, goa_lon)
    assert 380.0 < dist < 420.0

def test_ais_csv_import_api(client):
    csv_content = (
        "mmsi,latitude,longitude,speed,course,heading,timestamp,name,ship_type\n"
        "419111222,19.05,72.75,14.2,180.0,180.0,2026-09-14T06:00:00Z,OCEAN LEADER,Tanker\n"
        "419111222,18.95,72.75,13.8,180.0,180.0,2026-09-14T07:00:00Z,OCEAN LEADER,Tanker\n"
        "419111222,18.85,72.75,14.0,180.0,180.0,2026-09-14T08:00:00Z,OCEAN LEADER,Tanker\n"
        "419333444,19.10,72.60,11.0,220.0,220.0,2026-09-14T06:30:00Z,BHARAT PRIDE,Cargo\n"
    )
    response = client.post(
        "/api/ais/import",
        files={"file": ("test_ais.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_records"] == 4
    assert data["vessels_updated"] == 2

def test_ais_nearby_query_api(client):
    response = client.get("/api/ais/nearby?lat=19.0&lon=72.75&radius_km=30.0")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    # Check closest vessel distance is within 30 km
    assert results[0]["closest_distance_km"] <= 30.0
