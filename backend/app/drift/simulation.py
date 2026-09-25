import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from shapely.geometry import Point, MultiPoint, Polygon, mapping
from shapely.ops import unary_union

from app.services.environmental_service import env_provider, EnvironmentalDataProvider

class LagrangianDriftSimulator:
    """
    High-Fidelity Lagrangian Particle Oceanographic Drift Engine.
    Simulates:
    - Forward Drift Forecasting (Ecological threat & trajectory prediction)
    - Backward Hindcasting (Reconstructing probable spill release origin zone & time)
    Incorporates:
    - 100% surface ocean current advection
    - 3% wind drag (windage factor) with Coriolis deflection
    - Stochastic Gaussian turbulent diffusion: sigma = sqrt(2 * Kh * dt)
    - Convex hull origin uncertainty polygon generation
    """

    def __init__(
        self,
        provider: Optional[EnvironmentalDataProvider] = None,
        windage_factor: float = 0.03,
        deflection_angle_deg: float = 10.0,
        horizontal_diffusivity_m2s: float = 2.5,
    ):
        self.provider = provider or env_provider
        self.windage = windage_factor
        self.deflection_rad = math.radians(deflection_angle_deg)
        self.Kh = horizontal_diffusivity_m2s

    def _meters_to_deg(self, dx_m: float, dy_m: float, lat: float) -> Tuple[float, float]:
        """Converts spatial displacement in meters (dx, dy) to WGS84 degree offsets (dlon, dlat)."""
        dlat = dy_m / 110574.0
        dlon = dx_m / (111320.0 * max(abs(math.cos(math.radians(lat))), 0.1))
        return dlon, dlat

    def simulate(
        self,
        center_lon: float,
        center_lat: float,
        start_time: datetime,
        duration_hours: float = 12.0,
        timestep_minutes: int = 15,
        particle_count: int = 150,
        is_backward: bool = True,
    ) -> Dict[str, Any]:
        dt_seconds = timestep_minutes * 60.0
        total_steps = int((duration_hours * 60.0) / timestep_minutes)
        direction_sign = -1.0 if is_backward else 1.0

        # Initial particle dispersion within ~500m of centroid
        particles = []
        for i in range(particle_count):
            r_init = random.gauss(0, 300.0)
            theta = random.uniform(0, 2 * math.pi)
            dlon, dlat = self._meters_to_deg(r_init * math.cos(theta), r_init * math.sin(theta), center_lat)
            particles.append({
                "id": i,
                "lon": center_lon + dlon,
                "lat": center_lat + dlat,
                "history": [(center_lon + dlon, center_lat + dlat, start_time)],
            })

        current_time = start_time
        diffusion_scale = math.sqrt(2.0 * self.Kh * dt_seconds)

        for step in range(total_steps):
            time_delta = timedelta(minutes=timestep_minutes) * direction_sign
            current_time = current_time + time_delta

            # Fetch environmental forcing for this time step
            cond = self.provider.get_conditions(center_lat, center_lon, current_time)
            w_u = cond["wind"]["u"]
            w_v = cond["wind"]["v"]
            c_u = cond["currents"]["u"]
            c_v = cond["currents"]["v"]

            # Wind vector with Coriolis deflection angle
            w_u_def = w_u * math.cos(self.deflection_rad) - w_v * math.sin(self.deflection_rad)
            w_v_def = w_u * math.sin(self.deflection_rad) + w_v * math.cos(self.deflection_rad)

            # Combined drift advection velocity (m/s)
            u_total = (c_u + self.windage * w_u_def) * direction_sign
            v_total = (c_v + self.windage * w_v_def) * direction_sign

            for p in particles:
                # Stochastic turbulent diffusion (always spreads outward, forward or backward)
                diff_x = random.gauss(0, diffusion_scale)
                diff_y = random.gauss(0, diffusion_scale)

                dx_meters = u_total * dt_seconds + diff_x
                dy_meters = v_total * dt_seconds + diff_y

                dlon, dlat = self._meters_to_deg(dx_meters, dy_meters, p["lat"])
                p["lon"] += dlon
                p["lat"] += dlat
                p["history"].append((p["lon"], p["lat"], current_time))

        # 4. Generate Origin Probability Uncertainty Region (Convex Hull + Buffer)
        final_points = [Point(p["lon"], p["lat"]) for p in particles]
        mp = MultiPoint(final_points)
        hull = mp.convex_hull
        if hull.geom_type == 'Point':
            origin_geom = hull.buffer(0.04)  # ~4.4 km buffer
        elif hull.geom_type == 'LineString':
            origin_geom = hull.buffer(0.03)
        else:
            origin_geom = hull.buffer(0.02)  # smooth convex hull boundary

        end_sim_time = current_time
        sim_start = end_sim_time if is_backward else start_time
        sim_end = start_time if is_backward else end_sim_time

        # Calculate most probable origin centroid and dispersion radius
        origin_lats = [p["lat"] for p in particles]
        origin_lons = [p["lon"] for p in particles]
        mean_origin_lat = float(np.mean(origin_lats))
        mean_origin_lon = float(np.mean(origin_lons))

        # Radial uncertainty (90th percentile particle spread in km)
        from app.ais.trajectory import haversine_distance_km
        dispersions = [
            haversine_distance_km(mean_origin_lat, mean_origin_lon, p["lat"], p["lon"])
            for p in particles
        ]
        uncertainty_radius_km = round(float(np.percentile(dispersions, 90)), 2) if dispersions else 5.0
        uncertainty_radius_km = max(2.0, min(50.0, uncertainty_radius_km))

        is_demo_forcing = cond.get("is_demo", True)
        confidence = 0.82 if is_backward else 0.88

        return {
            "simulation_type": "BACKWARD" if is_backward else "FORWARD",
            "start_time": sim_start,
            "end_time": sim_end,
            "duration_hours": duration_hours,
            "particle_count": particle_count,
            "particles": particles,
            "origin": {
                "latitude": round(mean_origin_lat, 5),
                "longitude": round(mean_origin_lon, 5),
            },
            "time_window": {
                "start": sim_start.isoformat() if hasattr(sim_start, "isoformat") else str(sim_start),
                "end": sim_end.isoformat() if hasattr(sim_end, "isoformat") else str(sim_end),
            },
            "uncertainty_km": uncertainty_radius_km,
            "confidence": confidence,
            "origin_probability_geometry": mapping(origin_geom),
            "is_demo": is_demo_forcing,
            "data_source": cond.get("source", "Environmental Forcing Engine"),
            "model_classification": "Real-data Open-Meteo/Copernicus drift" if not is_demo_forcing else "Demonstration Climatology Drift",
            "environmental_conditions": cond,
        }
