import math
import numpy as np
import cv2
from typing import Dict, Any, List, Optional, Tuple
from shapely.geometry import Polygon, MultiPolygon, Point, box, mapping
from shapely.ops import unary_union

class SpillCharacterizationEngine:
    """
    Geospatial characterization engine converting raster segmentation masks
    into georeferenced WGS84 GeoJSON polygons with precise physical metrics:
    - Geodesic Area (km²)
    - Perimeter (km)
    - Centroid (lat, lon)
    - Bounding Box
    - Aggregated Detection Confidence
    """

    @staticmethod
    def pixel_to_geo(
        px: float,
        py: float,
        bounds: Tuple[float, float, float, float],
        img_width: int,
        img_height: int
    ) -> Tuple[float, float]:
        """Maps raster (x, y) coordinates to WGS84 (lon, lat) using linear affine interpolation."""
        min_lon, min_lat, max_lon, max_lat = bounds
        lon = min_lon + (px / max(img_width, 1)) * (max_lon - min_lon)
        lat = max_lat - (py / max(img_height, 1)) * (max_lat - min_lat)
        return lon, lat

    @classmethod
    def polygonize_and_characterize(
        cls,
        binary_mask: np.ndarray,
        probability_map: np.ndarray,
        bounds: Tuple[float, float, float, float] = (72.0, 18.5, 73.0, 19.5),
        min_area_km2: float = 0.01
    ) -> Optional[Dict[str, Any]]:
        h, w = binary_mask.shape[:2]
        min_lon, min_lat, max_lon, max_lat = bounds

        # Physical scale approximation at average scene latitude
        center_lat = (min_lat + max_lat) / 2.0
        km_per_deg_lat = 110.574
        km_per_deg_lon = 111.320 * math.cos(math.radians(center_lat))

        scene_width_km = abs(max_lon - min_lon) * km_per_deg_lon
        scene_height_km = abs(max_lat - min_lat) * km_per_deg_lat
        pixel_area_km2 = (scene_width_km * scene_height_km) / max(w * h, 1)

        # 1. Morphological cleanup: remove single-pixel speckle noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)

        # 2. Find connected component contours
        contours, hierarchy = cv2.findContours(
            cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        valid_polygons: List[Polygon] = []
        confidences: List[float] = []

        for cnt in contours:
            if len(cnt) < 4:
                continue

            # Calculate polygon pixel area
            cnt_pixel_area = cv2.contourArea(cnt)
            cnt_km2 = cnt_pixel_area * pixel_area_km2
            if cnt_km2 < min_area_km2:
                continue

            # Convert contour vertices to WGS84 coordinates
            geo_coords = []
            for pt in cnt.squeeze():
                if pt.ndim != 1:
                    continue
                px, py = float(pt[0]), float(pt[1])
                lon, lat = cls.pixel_to_geo(px, py, bounds, w, h)
                geo_coords.append((lon, lat))

            if len(geo_coords) >= 3:
                # Close the polygon ring
                if geo_coords[0] != geo_coords[-1]:
                    geo_coords.append(geo_coords[0])

                poly = Polygon(geo_coords)
                if poly.is_valid and not poly.is_empty:
                    valid_polygons.append(poly)

                    # Extract mean probability within this contour
                    mask_sub = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(mask_sub, [cnt], -1, 1, -1)
                    mean_conf = float(np.mean(probability_map[mask_sub > 0])) if np.sum(mask_sub) > 0 else 0.8
                    confidences.append(mean_conf)

        if not valid_polygons:
            return None

        # Combine polygons if multiple components detected
        unified_geom = unary_union(valid_polygons) if len(valid_polygons) > 1 else valid_polygons[0]

        # 3. Calculate geodesic area and perimeter
        total_area_km2 = float(np.sum(binary_mask) * pixel_area_km2)
        total_perimeter_km = 0.0

        # Approximate perimeter via contour arc lengths
        for cnt in contours:
            if cv2.contourArea(cnt) * pixel_area_km2 >= min_area_km2:
                arc_len = cv2.arcLength(cnt, closed=True)
                # Average pixel size in km
                px_scale_km = (scene_width_km / w + scene_height_km / h) / 2.0
                total_perimeter_km += arc_len * px_scale_km

        # Centroid & Bounding box
        centroid_pt = unified_geom.centroid
        min_x, min_y, max_x, max_y = unified_geom.bounds
        bbox_geom = box(min_x, min_y, max_x, max_y)

        overall_confidence = float(np.mean(confidences)) if confidences else 0.85
        overall_confidence = max(0.50, min(0.99, overall_confidence))

        return {
            "spill_detected": True,
            "confidence": round(overall_confidence, 3),
            "area_km2": round(total_area_km2, 3),
            "perimeter_km": round(total_perimeter_km, 3),
            "centroid": {"type": "Point", "coordinates": [round(centroid_pt.x, 5), round(centroid_pt.y, 5)]},
            "bounding_box": mapping(bbox_geom),
            "geometry": mapping(unified_geom),
        }

    @staticmethod
    def to_geojson_feature(char_result: Dict[str, Any], extra_properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Formats characterization result into an RFC 7946 compliant GeoJSON Feature.
        """
        props = {
            "spill_detected": char_result.get("spill_detected", False),
            "confidence": char_result.get("confidence", 0.0),
            "area_km2": char_result.get("area_km2", 0.0),
            "perimeter_km": char_result.get("perimeter_km", 0.0),
            "centroid": char_result.get("centroid", {}),
            "bounding_box": char_result.get("bounding_box", {}),
        }
        if extra_properties:
            props.update(extra_properties)

        return {
            "type": "Feature",
            "geometry": char_result.get("geometry"),
            "properties": props,
        }

    @staticmethod
    def generate_mask_png(
        binary_mask: np.ndarray,
        output_path: Optional[str] = None,
        color_rgba: Tuple[int, int, int, int] = (220, 38, 38, 180)
    ) -> np.ndarray:
        """
        Creates a transparent RGBA image with colored fill over detected spill pixels.
        """
        h, w = binary_mask.shape[:2]
        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        active = binary_mask > 0
        rgba[active, 0] = color_rgba[0]  # R
        rgba[active, 1] = color_rgba[1]  # G
        rgba[active, 2] = color_rgba[2]  # B
        rgba[active, 3] = color_rgba[3]  # Alpha

        if output_path:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # OpenCV expects BGRA order
            bgra = cv2.merge([rgba[:, :, 2], rgba[:, :, 1], rgba[:, :, 0], rgba[:, :, 3]])
            cv2.imwrite(output_path, bgra)

        return rgba

