import re
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

class AisRecordCleaner:
    """
    Cleans, validates, and normalizes raw AIS transponder records according to
    IMO/ITU maritime standards.
    """
    MAX_COMMERCIAL_SPEED_KNOTS = 50.0  # Physically impossible commercial ship speed threshold
    VALID_MMSI_REGEX = re.compile(r"^\d{9}$")

    @classmethod
    def clean_record(cls, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # 1. MMSI Validation
        raw_mmsi = str(row.get("mmsi", row.get("MMSI", ""))).strip()
        if not cls.VALID_MMSI_REGEX.match(raw_mmsi):
            return None

        # 2. Coordinates Validation
        try:
            lat = float(row.get("latitude", row.get("lat", row.get("LAT", row.get("Latitude", 0)))))
            lon = float(row.get("longitude", row.get("lon", row.get("LON", row.get("Longitude", 0)))))
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return None
            if lat == 0.0 and lon == 0.0:  # Null island transponder error
                return None
        except (ValueError, TypeError):
            return None

        # 3. Timestamp Validation
        raw_ts = row.get("timestamp", row.get("time", row.get("BaseDateTime", row.get("TIMESTAMP", None))))
        if not raw_ts:
            return None

        ts: datetime
        if isinstance(raw_ts, datetime):
            ts = raw_ts
        elif isinstance(raw_ts, (int, float)):
            ts = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
        elif isinstance(raw_ts, str):
            clean_str = raw_ts.strip().replace("Z", "+00:00")
            try:
                ts = datetime.fromisoformat(clean_str)
            except ValueError:
                # Try common formats
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                    try:
                        ts = datetime.strptime(clean_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
        else:
            return None

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # 4. Speed Validation (Speed Over Ground - SOG in knots)
        raw_sog = row.get("speed", row.get("sog", row.get("SOG", 0.0)))
        speed = 0.0
        try:
            speed = float(raw_sog) if raw_sog is not None else 0.0
            if speed < 0.0 or speed > cls.MAX_COMMERCIAL_SPEED_KNOTS:
                return None
        except (ValueError, TypeError):
            speed = 0.0

        # 5. Course (COG) & Heading
        raw_cog = row.get("course", row.get("cog", row.get("COG", 0.0)))
        course = 0.0
        try:
            course = float(raw_cog) % 360.0 if raw_cog is not None else 0.0
        except (ValueError, TypeError):
            course = 0.0

        raw_heading = row.get("heading", row.get("Heading", course))
        heading = course
        try:
            heading = float(raw_heading) % 360.0 if raw_heading is not None else course
        except (ValueError, TypeError):
            heading = course

        # 6. Metadata
        vessel_name = str(row.get("name", row.get("vessel_name", row.get("VesselName", f"VESSEL-{raw_mmsi}")))).strip()
        ship_type = str(row.get("ship_type", row.get("vessel_type", row.get("VesselType", "Tanker")))).strip()

        return {
            "mmsi": raw_mmsi,
            "name": vessel_name or f"VESSEL-{raw_mmsi}",
            "ship_type": ship_type or "Tanker",
            "timestamp": ts,
            "lat": lat,
            "lon": lon,
            "speed": speed,
            "course": course,
            "heading": heading,
            "navigation_status": str(row.get("navigation_status", row.get("Status", "Under way using engine"))),
        }
