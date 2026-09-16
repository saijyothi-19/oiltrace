import os
import math
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.satellite import SatelliteImage
from app.models.spill import SpillEvent, SpillDetection, SpillStatus
from app.models.drift import DriftSimulation, DriftParticle, SimulationType, SimulationStatus
from app.models.vessel import Vessel, AisPosition
from app.models.attribution import VesselCandidate, PriorityLevel
from app.models.investigation import Investigation, InvestigationStatus
from app.attribution.scorer import AttributionScoringEngine
from app.drift.simulation import LagrangianDriftSimulator
from app.core.config import settings

router = APIRouter(prefix="/api/demo", tags=["Demo Scenario Loader"])

@router.post("/load")
def load_demo_investigation(db: Session = Depends(get_db)):
    """
    Populates a complete, realistic, scientifically coherent demonstration scenario:
    - Sentinel-1A SAR scene off Mumbai / Arabian Sea maritime corridor
    - Characterized oil spill polygon (14.2 km², 18.4 km perimeter, 93.5% confidence)
    - Backward Lagrangian hindcast with origin uncertainty ellipse
    - 5 candidate vessels with distinct behavioral and trajectory patterns
    - Generated investigation dossier and active case file
    """
    now = datetime.now(timezone.utc)
    spill_time = now - timedelta(hours=2)
    origin_time = spill_time - timedelta(hours=8)

    # Base coordinates: Arabian Sea shipping lane (~35 nautical miles west of Mumbai)
    # Origin: [72.25, 18.75] -> Drift advects North-East towards [72.48, 18.96]
    spill_lon, spill_lat = 72.48, 18.96
    origin_lon, origin_lat = 72.25, 18.75

    # 1. Clear any existing demo spill records with this product ID
    demo_product_id = "S1A_IW_GRDH_1SDV_20260914T100000_OFFSHORE_MUMBAI_DEMO"
    existing_sat = db.query(SatelliteImage).filter(SatelliteImage.product_id == demo_product_id).first()
    if existing_sat:
        for sp in existing_sat.spill_events:
            db.query(Investigation).filter(Investigation.spill_event_id == sp.id).delete()
            db.query(VesselCandidate).filter(VesselCandidate.spill_event_id == sp.id).delete()
            db.query(DriftSimulation).filter(DriftSimulation.spill_event_id == sp.id).delete()
            db.delete(sp)
        db.delete(existing_sat)
        db.commit()

    # 2. Create Satellite Image
    sat_img = SatelliteImage(
        product_id=demo_product_id,
        satellite="Sentinel-1A (Synthetic Demo)",
        sensor="C-SAR (IW Mode)",
        acquisition_time=spill_time,
        polarization="VV",
        orbit="DESCENDING",
        file_path="./data/demo/synthetic_sar_scene.tif",
        thumbnail_path="./data/demo/synthetic_sar_thumb.png",
        metadata_json={
            "orbit_number": 48921,
            "incidence_angle_deg": 38.4,
            "synthetic_watermark": "Synthetic demonstration data — not real-world evidence.",
        },
        bounding_geometry={
            "type": "Polygon",
            "coordinates": [[[71.8, 18.4], [72.9, 18.4], [72.9, 19.4], [71.8, 19.4], [71.8, 18.4]]]
        }
    )
    db.add(sat_img)
    db.flush()

    # 3. Create Oil Spill Polygon
    # Characteristic elongated plume shape formed by ocean drift
    spill_coords = [
        [72.46, 18.94],
        [72.50, 18.95],
        [72.52, 18.98],
        [72.49, 18.99],
        [72.45, 18.97],
        [72.46, 18.94],
    ]
    spill = SpillEvent(
        satellite_image_id=sat_img.id,
        detected_at=spill_time,
        confidence=0.935,
        area_km2=14.20,
        perimeter_km=18.40,
        centroid={"type": "Point", "coordinates": [spill_lon, spill_lat]},
        bounding_box={
            "type": "Polygon",
            "coordinates": [[[72.45, 18.94], [72.52, 18.94], [72.52, 18.99], [72.45, 18.99], [72.45, 18.94]]]
        },
        spill_geometry={
            "type": "Polygon",
            "coordinates": [spill_coords]
        },
        status=SpillStatus.DETECTED,
        model_version="unet-v1.0-baseline",
    )
    db.add(spill)
    db.flush()

    # 4. Create Backward Lagrangian Drift Hindcast
    simulator = LagrangianDriftSimulator()
    sim_data = simulator.simulate(
        center_lon=spill_lon,
        center_lat=spill_lat,
        start_time=spill_time,
        duration_hours=8.0,
        timestep_minutes=20,
        particle_count=120,
        is_backward=True,
    )

    drift_sim = DriftSimulation(
        spill_event_id=spill.id,
        simulation_type=SimulationType.BACKWARD,
        start_time=origin_time,
        end_time=spill_time,
        duration_hours=8.0,
        particle_count=120,
        model_name="OpenDrift Lagrangian Backward Emulator",
        confidence=0.89,
        status=SimulationStatus.COMPLETED,
        origin_probability_geometry=sim_data["origin_probability_geometry"],
        parameters_json={
            "environmental": sim_data["environmental_conditions"],
            "synthetic_watermark": "Synthetic demonstration data — not real-world evidence.",
        }
    )
    db.add(drift_sim)
    db.flush()

    # Save sampled drifter particles
    for p in sim_data["particles"][:30]:
        for lon, lat, ts in p["history"][::3]:
            particle_rec = DriftParticle(
                simulation_id=drift_sim.id,
                particle_id=p["id"],
                timestamp=ts,
                position={"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            )
            db.add(particle_rec)

    # 5. Populate 5 Characteristic Demonstration AIS Vessels
    # Candidate 1: MT ARABIAN PRIDE (Crude Oil Tanker)
    # Passes directly through origin polygon at origin_time, with subtle speed drop from 14.5 to 7.8 kts -> HIGH
    # Candidate 2: MV HIMALAYA TRADER (Bulk Carrier)
    # In shipping lane, 12 km north of origin, passes 1.5 hrs later -> MEDIUM
    # Candidate 3: FV SAGAR KANYA (Trawler)
    # Lingers near current spill location, but was 45 km south at origin time -> LOW
    # Candidate 4: MSC INDUS (Container Ship)
    # Crosses shipping corridor 7 hours after release window -> LOW
    # Candidate 5: MT AL-BAHR (Chemical Tanker)
    # Transponder goes dark for 2.5 hours right at the origin window -> Flagged with data gap

    demo_vessels = [
        {
            "mmsi": "419001888",
            "name": "MT ARABIAN PRIDE",
            "ship_type": "Crude Oil Tanker",
            "flag": "Liberia",
            "imo": "9812450",
            "length": 245.0,
            "width": 42.0,
            "waypoints": [
                (origin_lon - 0.25, origin_lat - 0.20, origin_time - timedelta(hours=2.5), 14.2, 50.0),
                (origin_lon - 0.10, origin_lat - 0.08, origin_time - timedelta(hours=1.0), 14.0, 50.0),
                (origin_lon + 0.01, origin_lat + 0.01, origin_time, 7.8, 55.0),  # In origin ellipse, speed dropped!
                (origin_lon + 0.12, origin_lat + 0.10, origin_time + timedelta(hours=1.5), 13.5, 52.0),
                (origin_lon + 0.30, origin_lat + 0.25, origin_time + timedelta(hours=3.5), 14.1, 50.0),
            ]
        },
        {
            "mmsi": "419002555",
            "name": "MV HIMALAYA TRADER",
            "ship_type": "Bulk Carrier",
            "flag": "Panama",
            "imo": "9745120",
            "length": 190.0,
            "width": 32.0,
            "waypoints": [
                (origin_lon - 0.20, origin_lat + 0.12, origin_time - timedelta(hours=1.0), 12.5, 65.0),
                (origin_lon, origin_lat + 0.11, origin_time + timedelta(hours=1.0), 12.4, 65.0),
                (origin_lon + 0.20, origin_lat + 0.10, origin_time + timedelta(hours=3.0), 12.3, 65.0),
            ]
        },
        {
            "mmsi": "419003111",
            "name": "FV SAGAR KANYA",
            "ship_type": "Fishing Vessel",
            "flag": "India",
            "imo": "N/A",
            "length": 28.0,
            "width": 7.5,
            "waypoints": [
                (spill_lon - 0.05, spill_lat - 0.35, origin_time, 4.2, 10.0),
                (spill_lon - 0.02, spill_lat - 0.20, origin_time + timedelta(hours=4.0), 4.5, 15.0),
                (spill_lon + 0.02, spill_lat + 0.02, spill_time, 3.8, 20.0),  # Near spill now, but far at release
            ]
        },
        {
            "mmsi": "419004999",
            "name": "MSC INDUS",
            "ship_type": "Container Ship",
            "flag": "Malta",
            "imo": "9934812",
            "length": 366.0,
            "width": 51.0,
            "waypoints": [
                (origin_lon - 0.30, origin_lat - 0.25, spill_time + timedelta(hours=2.0), 19.5, 45.0),
                (origin_lon, origin_lat, spill_time + timedelta(hours=3.5), 19.2, 45.0),
                (origin_lon + 0.30, origin_lat + 0.25, spill_time + timedelta(hours=5.0), 19.0, 45.0),
            ]
        },
        {
            "mmsi": "419005444",
            "name": "MT AL-BAHR",
            "ship_type": "Chemical Tanker",
            "flag": "Marshall Islands",
            "imo": "9618400",
            "length": 160.0,
            "width": 26.0,
            "waypoints": [
                (origin_lon - 0.15, origin_lat - 0.12, origin_time - timedelta(hours=2.0), 13.0, 52.0),
                # AIS Gap of 3 hours near origin:
                (origin_lon + 0.18, origin_lat + 0.14, origin_time + timedelta(hours=1.5), 12.8, 52.0),
            ]
        },
    ]

    scorer = AttributionScoringEngine()
    scored_candidates = []

    for v_data in demo_vessels:
        vessel = db.query(Vessel).filter(Vessel.mmsi == v_data["mmsi"]).first()
        if not vessel:
            vessel = Vessel(
                mmsi=v_data["mmsi"],
                name=v_data["name"],
                ship_type=v_data["ship_type"],
                flag=v_data["flag"],
                imo=v_data["imo"],
                length=v_data["length"],
                width=v_data["width"],
                metadata_json={"synthetic_watermark": "Synthetic demonstration data — not real-world evidence."},
            )
            db.add(vessel)
            db.flush()

        # Delete existing positions for clean re-load
        db.query(AisPosition).filter(AisPosition.vessel_id == vessel.id).delete()

        positions = []
        for lon, lat, ts, spd, cog in v_data["waypoints"]:
            pos = AisPosition(
                vessel_id=vessel.id,
                timestamp=ts,
                position={"type": "Point", "coordinates": [round(lon, 4), round(lat, 4)]},
                speed=spd,
                course=cog,
                heading=cog,
                navigation_status="Under way using engine",
            )
            positions.append(pos)
            db.add(pos)
        db.flush()

        # Score candidate
        eval_res = scorer.evaluate_vessel(
            vessel=vessel,
            positions=positions,
            origin_geometry_dict=drift_sim.origin_probability_geometry,
            origin_center_lat=origin_lat,
            origin_center_lon=origin_lon,
            origin_time=origin_time,
            temporal_window_hours=12.0,
            spatial_radius_km=50.0,
        )

        candidate = VesselCandidate(
            spill_event_id=spill.id,
            vessel_id=vessel.id,
            spatial_score=eval_res["spatial_score"],
            temporal_score=eval_res["temporal_score"],
            trajectory_score=eval_res["trajectory_score"],
            behaviour_score=eval_res["behaviour_score"],
            data_quality_score=eval_res["data_quality_score"],
            overall_score=eval_res["overall_score"],
            priority=eval_res["priority"],
            explanation_json=eval_res["explanation"],
        )
        scored_candidates.append(candidate)
        db.add(candidate)

    # 6. Create Case Investigation
    investigation = Investigation(
        spill_event_id=spill.id,
        status=InvestigationStatus.UNDER_REVIEW,
        notes=(
            "AUTOMATED CASE INITIALIZATION:\n"
            "- Satellite SAR detection confirmed 14.2 km² crude slick along Mumbai offshore corridor.\n"
            "- Backward Lagrangian hindcast models origin release window at T - 8 hours.\n"
            "- Candidate attribution prioritizes MT ARABIAN PRIDE (Score: 91.4, HIGH) due to spatial-temporal intersection and operational speed drop."
        )
    )
    db.add(investigation)
    db.commit()

    return {
        "success": True,
        "spill_id": spill.id,
        "vessels_loaded": len(demo_vessels),
        "candidates_ranked": len(scored_candidates),
        "message": "Demo investigation scenario loaded successfully with 5 candidate vessels and backward hindcast drift.",
        "synthetic_disclaimer": "Synthetic demonstration data — not real-world evidence.",
    }
