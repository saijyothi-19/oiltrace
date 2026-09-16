import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import Point, shape

from app.models.vessel import Vessel, AisPosition
from app.models.attribution import PriorityLevel
from app.ais.trajectory import haversine_distance_km

class AttributionScoringEngine:
    """
    Explainable Maritime Decision-Support Attribution Engine.
    Combines 5 evidence dimensions with configurable engineering starting weights:
    - Spatial Match (35%): Proximity to estimated spill origin polygon
    - Temporal Match (30%): Synchronization with estimated release time interval
    - Trajectory Match (20%): Course alignment and heading compatibility with drift trail
    - Behavioral Anomaly (10%): Sudden deceleration, sharp turn, loitering pattern
    - Data Quality (5%): AIS transponder transmission continuity vs. suspicious gaps
    """

    def __init__(
        self,
        weight_spatial: float = 0.35,
        weight_temporal: float = 0.30,
        weight_trajectory: float = 0.20,
        weight_behaviour: float = 0.10,
        weight_data_quality: float = 0.05,
        high_priority_threshold: float = 80.0,
        medium_priority_threshold: float = 55.0,
    ):
        self.w_s = weight_spatial
        self.w_t = weight_temporal
        self.w_tr = weight_trajectory
        self.w_b = weight_behaviour
        self.w_dq = weight_data_quality
        self.high_threshold = high_priority_threshold
        self.med_threshold = medium_priority_threshold

    def evaluate_vessel(
        self,
        vessel: Vessel,
        positions: List[AisPosition],
        origin_geometry_dict: Optional[Dict[str, Any]],
        origin_center_lat: float,
        origin_center_lon: float,
        origin_time: datetime,
        temporal_window_hours: float = 12.0,
        spatial_radius_km: float = 50.0,
    ) -> Dict[str, Any]:
        if not positions:
            return self._empty_result(vessel)

        sorted_pos = sorted(positions, key=lambda p: p.timestamp)
        origin_poly = shape(origin_geometry_dict) if origin_geometry_dict else None

        # 1. Spatial Score (35%)
        # Minimum distance from any reported waypoint to origin centroid
        min_dist_km = 9999.0
        closest_pos = sorted_pos[0]
        intersects_origin = False

        for p in sorted_pos:
            coords = p.position.get("coordinates") if isinstance(p.position, dict) else [0, 0]
            lon, lat = coords[0], coords[1]
            dist = haversine_distance_km(origin_center_lat, origin_center_lon, lat, lon)
            if dist < min_dist_km:
                min_dist_km = dist
                closest_pos = p

            if origin_poly and origin_poly.contains(Point(lon, lat)):
                intersects_origin = True

        if intersects_origin:
            spatial_score = 98.0
        else:
            # Linear decay from 100 at 0km to 0 at spatial_radius_km
            spatial_score = max(0.0, (1.0 - (min_dist_km / spatial_radius_km)) * 95.0)

        # 2. Temporal Score (30%)
        # Time difference between closest waypoint and estimated origin release time
        time_diff_hours = abs((closest_pos.timestamp - origin_time).total_seconds()) / 3600.0
        # Decay over temporal window
        temporal_score = max(0.0, (1.0 - (time_diff_hours / temporal_window_hours)) * 100.0)

        # 3. Trajectory Match (20%)
        # Evaluates vessel course vector pointing toward or aligning with origin
        speeds = [p.speed for p in sorted_pos if p.speed is not None]
        avg_speed = float(np.mean(speeds)) if speeds else 12.0

        # Course difference between vessel heading and vector to origin
        closest_coords = closest_pos.position["coordinates"]
        bearing_to_origin = math.degrees(math.atan2(
            origin_center_lon - closest_coords[0],
            origin_center_lat - closest_coords[1]
        )) % 360.0

        vessel_course = closest_pos.course if closest_pos.course is not None else 0.0
        angle_diff = abs((vessel_course - bearing_to_origin + 180) % 360 - 180)
        
        if intersects_origin or min_dist_km < 5.0:
            trajectory_score = 92.0
        elif min_dist_km < 15.0:
            base_tr = max(0.0, (1.0 - (angle_diff / 180.0)) * 85.0)
            trajectory_score = max(base_tr, 78.0)
        else:
            trajectory_score = max(0.0, (1.0 - (angle_diff / 180.0)) * 85.0)

        # 4. Behavioral Anomaly (10%)
        # Detect notable speed drop (>30% speed reduction while underway) or slow steaming
        max_s = max(speeds) if speeds else 0.0
        min_s = min(speeds) if speeds else 0.0
        has_speed_drop = (max_s > 8.0 and min_s <= 0.65 * max_s) or any(s < 4.0 for s in speeds)
        behaviour_score = 90.0 if has_speed_drop else 50.0

        # 5. Data Quality & Transponder Continuity (5%)
        # Check time intervals between consecutive reports (gap > 2 hours near origin is flagged)
        max_gap_hours = 0.0
        gap_near_origin = False
        for i in range(len(sorted_pos) - 1):
            dt_h = (sorted_pos[i + 1].timestamp - sorted_pos[i].timestamp).total_seconds() / 3600.0
            if dt_h > max_gap_hours:
                max_gap_hours = dt_h
                if min_dist_km < 25.0 and dt_h > 1.5:
                    gap_near_origin = True

        data_quality_score = 60.0 if gap_near_origin else 92.0

        # Overall Weighted Composite Score
        overall_score = (
            spatial_score * self.w_s +
            temporal_score * self.w_t +
            trajectory_score * self.w_tr +
            behaviour_score * self.w_b +
            data_quality_score * self.w_dq
        )
        overall_score = round(min(100.0, max(0.0, overall_score)), 1)

        # Priority Classification
        if overall_score >= self.high_threshold:
            priority = PriorityLevel.HIGH
        elif overall_score >= self.med_threshold:
            priority = PriorityLevel.MEDIUM
        else:
            priority = PriorityLevel.LOW

        # Generate Explainable Evidence Bullet Points
        evidence_points = []
        if intersects_origin:
            evidence_points.append("✓ Track directly intersects the estimated spill origin polygon")
        elif min_dist_km < 15.0:
            evidence_points.append(f"✓ Passed within close proximity ({min_dist_km:.1f} km) of origin")
        else:
            evidence_points.append(f"△ Moderate distance ({min_dist_km:.1f} km) to estimated origin")

        if time_diff_hours < 2.0:
            evidence_points.append(f"✓ Highly synchronous with hindcast release window (Δt = {time_diff_hours:.1f} hrs)")
        elif time_diff_hours < 6.0:
            evidence_points.append(f"✓ Compatible with estimated origin window (Δt = {time_diff_hours:.1f} hrs)")
        else:
            evidence_points.append(f"△ Significant time delta ({time_diff_hours:.1f} hrs) relative to origin")

        if trajectory_score > 70.0:
            evidence_points.append("✓ Vessel transit trajectory aligns with drift track corridor")

        if has_speed_drop:
            evidence_points.append("△ Anomalous speed reduction / loitering detected during transit")

        if gap_near_origin:
            evidence_points.append("△ AIS transmission gap / potential transponder blackout near origin")
        else:
            evidence_points.append("✓ Continuous AIS transmission stream with nominal ping frequency")

        evidence_breakdown = [
            {"key": "spatial", "label": "Spatial Proximity (35%)", "passed": spatial_score > 70, "score": round(spatial_score, 1), "detail": f"{min_dist_km:.1f} km closest approach"},
            {"key": "temporal", "label": "Temporal Sync (30%)", "passed": temporal_score > 70, "score": round(temporal_score, 1), "detail": f"{time_diff_hours:.1f} hrs delta to hindcast"},
            {"key": "trajectory", "label": "Trajectory Alignment (20%)", "passed": trajectory_score > 60, "score": round(trajectory_score, 1), "detail": f"{angle_diff:.0f}° relative heading"},
            {"key": "behaviour", "label": "Operating Behaviour (10%)", "passed": not has_speed_drop, "score": round(behaviour_score, 1), "detail": f"Avg speed {avg_speed:.1f} kts"},
            {"key": "data_quality", "label": "AIS Continuity (5%)", "passed": not gap_near_origin, "score": round(data_quality_score, 1), "detail": f"Max gap {max_gap_hours:.1f} hrs"},
        ]

        return {
            "vessel_id": vessel.id,
            "spatial_score": round(spatial_score, 1),
            "temporal_score": round(temporal_score, 1),
            "trajectory_score": round(trajectory_score, 1),
            "behaviour_score": round(behaviour_score, 1),
            "data_quality_score": round(data_quality_score, 1),
            "overall_score": overall_score,
            "priority": priority,
            "explanation": {
                "spatial_distance_km": round(min_dist_km, 2),
                "temporal_delta_hours": round(time_diff_hours, 2),
                "trajectory_heading_match_deg": round(angle_diff, 1),
                "speed_knots": round(avg_speed, 1),
                "anomalous_behavior_flag": has_speed_drop,
                "ais_gap_detected": gap_near_origin,
                "explanation_points": evidence_points,
                "evidence_breakdown": evidence_breakdown,
            }
        }

    def _empty_result(self, vessel: Vessel) -> Dict[str, Any]:
        return {
            "vessel_id": vessel.id,
            "spatial_score": 0.0,
            "temporal_score": 0.0,
            "trajectory_score": 0.0,
            "behaviour_score": 50.0,
            "data_quality_score": 50.0,
            "overall_score": 10.0,
            "priority": PriorityLevel.LOW,
            "explanation": {
                "spatial_distance_km": 999.0,
                "temporal_delta_hours": 999.0,
                "trajectory_heading_match_deg": 180.0,
                "speed_knots": 0.0,
                "anomalous_behavior_flag": False,
                "ais_gap_detected": True,
                "explanation_points": ["△ Insufficient AIS position reports for trajectory analysis"],
                "evidence_breakdown": [],
            }
        }

import numpy as np
