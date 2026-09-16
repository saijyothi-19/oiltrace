from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from shapely.geometry import shape, Point

from app.models.vessel import Vessel, AisPosition
from app.ais.trajectory import haversine_distance_km

class AisSpatialFilter:
    """
    Spatial-temporal query engine for querying AIS transiting vessels within a given
    geographical radius and release time window from an estimated spill origin.
    """
    @staticmethod
    def find_nearby_vessels(
        db: Session,
        center_lat: float,
        center_lon: float,
        radius_km: float = 50.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        # Approximate bounding box for fast preliminary filtering
        # 1 deg latitude ≈ 111.32 km
        lat_delta = radius_km / 110.574
        lon_delta = radius_km / (111.320 * max(abs(math.cos(math.radians(center_lat))), 0.1))

        min_lat = center_lat - lat_delta
        max_lat = center_lat + lat_delta
        min_lon = center_lon - lon_delta
        max_lon = center_lon + lon_delta

        query = db.query(AisPosition).join(Vessel)

        if start_time:
            query = query.filter(AisPosition.timestamp >= start_time)
        if end_time:
            query = query.filter(AisPosition.timestamp <= end_time)

        all_positions = query.all()

        # Group by vessel and compute minimum distance to origin
        vessel_records: Dict[int, List[AisPosition]] = {}
        for pos in all_positions:
            if not pos.position or not isinstance(pos.position, dict):
                continue
            coords = pos.position.get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]
            dist = haversine_distance_km(center_lat, center_lon, lat, lon)
            if dist <= radius_km:
                if pos.vessel_id not in vessel_records:
                    vessel_records[pos.vessel_id] = []
                vessel_records[pos.vessel_id].append(pos)

        results = []
        for vessel_id, positions in vessel_records.items():
            vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
            if not vessel:
                continue
            min_dist = min(
                haversine_distance_km(center_lat, center_lon, p.position["coordinates"][1], p.position["coordinates"][0])
                for p in positions
            )
            results.append({
                "vessel": vessel,
                "positions_count": len(positions),
                "closest_distance_km": min_dist,
            })

        results.sort(key=lambda x: x["closest_distance_km"])
        return results

import math
