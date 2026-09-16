import math
from datetime import datetime
from typing import List, Dict, Any, Tuple
from shapely.geometry import LineString, Point

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 coordinates."""
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class TrajectoryBuilder:
    """
    Constructs coherent vessel trajectories from cleaned AIS position updates.
    """
    @staticmethod
    def build_trajectory(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Sort chronologically
        sorted_pos = sorted(positions, key=lambda x: x["timestamp"])
        if not sorted_pos:
            return {"coordinates": [], "length_km": 0.0, "duration_hours": 0.0, "avg_speed": 0.0}

        coords = [[p["lon"], p["lat"]] for p in sorted_pos]
        total_dist_km = 0.0
        for i in range(len(sorted_pos) - 1):
            p1 = sorted_pos[i]
            p2 = sorted_pos[i + 1]
            total_dist_km += haversine_distance_km(p1["lat"], p1["lon"], p2["lat"], p2["lon"])

        start_time = sorted_pos[0]["timestamp"]
        end_time = sorted_pos[-1]["timestamp"]
        duration_hours = max((end_time - start_time).total_seconds() / 3600.0, 0.001)
        avg_speed = total_dist_km / duration_hours if duration_hours > 0 else 0.0

        return {
            "coordinates": coords,
            "length_km": total_dist_km,
            "duration_hours": duration_hours,
            "avg_speed_kmh": avg_speed,
            "waypoints_count": len(sorted_pos),
            "start_time": start_time,
            "end_time": end_time,
        }
