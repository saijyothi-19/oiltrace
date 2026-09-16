import json
from typing import Any, Optional, Dict
from sqlalchemy.types import TypeDecorator, TEXT
from shapely.geometry import shape, mapping
from shapely.geometry.base import BaseGeometry

class GeoJSONGeometry(TypeDecorator):
    """
    Dual-mode spatial type:
    - Stores geometry as GeoJSON text in SQLite or Postgres.
    - Transparently converts to/from Python dict / Shapely geometry objects.
    - PostGIS compatible coordinate reference system: WGS84 (EPSG:4326).
    """
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, BaseGeometry):
            return json.dumps(mapping(value))
        if isinstance(value, dict):
            return json.dumps(value)
        if isinstance(value, str):
            # Validate JSON if string
            try:
                parsed = json.loads(value)
                return json.dumps(parsed)
            except Exception:
                return value
        return str(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None


def to_shapely(geom_data: Any) -> Optional[BaseGeometry]:
    """Helper to convert a dict, JSON string, or GeoJSONGeometry value to Shapely geometry."""
    if geom_data is None:
        return None
    if isinstance(geom_data, BaseGeometry):
        return geom_data
    if isinstance(geom_data, str):
        try:
            geom_data = json.loads(geom_data)
        except Exception:
            return None
    if isinstance(geom_data, dict):
        return shape(geom_data)
    return None
