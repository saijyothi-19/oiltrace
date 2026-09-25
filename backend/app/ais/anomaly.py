"""
OILTRACE — Maritime Vessel Behavioural Anomaly Detector.
Identifies operational anomalies in vessel trajectories:
- Sudden speed drops (>35% reduction from cruising speed)
- Sharp course deviations (>45 degrees) near the origin region
- Loitering / drifting behavior (<3 knots with circular course changes)
- Suspicious AIS transmission gaps near the estimated spill release zone

CRITICAL SCIENTIFIC INTEGRITY RULE:
Anomalies are decision-support signals indicating notable operational behavior.
They DO NOT constitute proof of pollution or illegal activity.
"""
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.ais.trajectory import haversine_distance_km

class VesselBehaviourAnomalyDetector:
    """
    Transparent rule-based behavioural anomaly detection for maritime vessels.
    """

    CRUISING_SPEED_MIN_KNOTS = 8.0
    SPEED_DROP_RATIO_THRESHOLD = 0.35  # > 35% speed drop
    COURSE_DEVIATION_DEG_THRESHOLD = 45.0
    LOITERING_MAX_SPEED_KNOTS = 3.5
    AIS_GAP_HOURS_THRESHOLD = 1.5
    ORIGIN_PROXIMITY_KM = 30.0

    @classmethod
    def analyze_trajectory(
        cls,
        positions: List[Any],
        origin_lat: Optional[float] = None,
        origin_lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes a chronological series of AIS position updates for behavioural anomalies.
        """
        if not positions or len(positions) < 2:
            return {
                "has_anomaly": False,
                "anomaly_signals": [],
                "details": "Insufficient position reports to evaluate behavior.",
                "data_quality_notes": ["Single or zero AIS position reports."],
            }

        sorted_pos = sorted(positions, key=lambda p: p.timestamp)
        signals = []

        speeds = [p.speed for p in sorted_pos if p.speed is not None]
        courses = [p.course for p in sorted_pos if p.course is not None]

        # 1. Sudden Deceleration Detection
        has_speed_drop = False
        max_speed = max(speeds) if speeds else 0.0
        min_speed = min(speeds) if speeds else 0.0
        if max_speed >= cls.CRUISING_SPEED_MIN_KNOTS:
            for i in range(len(sorted_pos) - 1):
                s1 = sorted_pos[i].speed or 0.0
                s2 = sorted_pos[i + 1].speed or 0.0
                if s1 >= cls.CRUISING_SPEED_MIN_KNOTS and s2 <= (1.0 - cls.SPEED_DROP_RATIO_THRESHOLD) * s1:
                    has_speed_drop = True
                    signals.append({
                        "type": "SUDDEN_SPEED_REDUCTION",
                        "severity": "MEDIUM",
                        "description": (
                            f"Vessel decelerated sharply from {s1:.1f} kts to {s2:.1f} kts "
                            f"({(1.0 - s2/s1)*100:.0f}% reduction while underway)."
                        ),
                        "timestamp": sorted_pos[i + 1].timestamp.isoformat(),
                    })
                    break

        # 2. Loitering Pattern Detection
        slow_reports = sum(1 for s in speeds if s <= cls.LOITERING_MAX_SPEED_KNOTS)
        if len(speeds) >= 3 and (slow_reports / len(speeds)) >= 0.5:
            signals.append({
                "type": "LOITERING_PATTERN",
                "severity": "LOW",
                "description": f"Vessel exhibited low-speed loitering / slow steaming (<{cls.LOITERING_MAX_SPEED_KNOTS} kts) across {slow_reports} reports.",
                "timestamp": sorted_pos[0].timestamp.isoformat(),
            })

        # 3. Sharp Course Alteration Near Origin
        has_sharp_turn = False
        for i in range(len(sorted_pos) - 1):
            c1 = sorted_pos[i].course
            c2 = sorted_pos[i + 1].course
            if c1 is not None and c2 is not None:
                turn = abs((c2 - c1 + 180) % 360 - 180)
                if turn >= cls.COURSE_DEVIATION_DEG_THRESHOLD:
                    # Check proximity if origin is given
                    p_coords = sorted_pos[i].position.get("coordinates", [0, 0])
                    dist = 0.0
                    if origin_lat is not None and origin_lon is not None:
                        dist = haversine_distance_km(origin_lat, origin_lon, p_coords[1], p_coords[0])
                    if origin_lat is None or dist <= cls.ORIGIN_PROXIMITY_KM:
                        has_sharp_turn = True
                        signals.append({
                            "type": "SHARP_COURSE_ALTERATION",
                            "severity": "MEDIUM",
                            "description": f"Sharp course alteration of {turn:.0f}° detected {f'({dist:.1f} km from estimated origin)' if origin_lat else ''}.",
                            "timestamp": sorted_pos[i + 1].timestamp.isoformat(),
                        })
                        break

        # 4. AIS Transmission Gaps Near Origin
        has_gap = False
        max_gap_hours = 0.0
        for i in range(len(sorted_pos) - 1):
            t1 = sorted_pos[i].timestamp
            t2 = sorted_pos[i + 1].timestamp
            dt_hours = (t2 - t1).total_seconds() / 3600.0
            if dt_hours > max_gap_hours:
                max_gap_hours = dt_hours

            if dt_hours >= cls.AIS_GAP_HOURS_THRESHOLD:
                p_coords = sorted_pos[i].position.get("coordinates", [0, 0])
                dist = 0.0
                if origin_lat is not None and origin_lon is not None:
                    dist = haversine_distance_km(origin_lat, origin_lon, p_coords[1], p_coords[0])
                if origin_lat is None or dist <= cls.ORIGIN_PROXIMITY_KM:
                    has_gap = True
                    signals.append({
                        "type": "AIS_TRANSMISSION_GAP",
                        "severity": "MEDIUM",
                        "description": f"AIS blackout / transmission gap of {dt_hours:.1f} hours detected {f'within {dist:.1f} km of origin' if origin_lat else ''}.",
                        "timestamp": t1.isoformat(),
                    })
                    break

        return {
            "has_anomaly": len(signals) > 0,
            "anomaly_count": len(signals),
            "anomaly_signals": signals,
            "max_gap_hours": round(max_gap_hours, 2),
            "average_speed_knots": round(float(sum(speeds)/len(speeds)), 1) if speeds else 0.0,
            "scientific_disclaimer": "Behavioural anomaly signal — not proof of illegal activity or liability.",
        }
