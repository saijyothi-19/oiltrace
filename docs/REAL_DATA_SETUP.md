# OILTRACE — Real-World Data Integration & Calibration Guide (SIH26143)

This guide documents the procedures for connecting **OILTRACE** to operational European Space Agency (Copernicus CDSE), Copernicus Marine (CMEMS), Open-Meteo Marine, and NOAA MarineCadastre AIS services.

---

## 1. Scientific Integrity & Provenance Architecture

In compliance with the **Smart India Hackathon SIH26143** evaluation criteria, OILTRACE maintains strict distinction between operational satellite observations, live oceanographic forecasts, and validated synthetic demonstration records:

- `🟢 REAL DATA`: Sourced directly via authenticated or public endpoints from Copernicus CDSE, CMEMS, Open-Meteo, or NOAA MarineCadastre.
- `🟡 DEMO DATA`: Deterministic climatological or synthetic records for offline testing and hackathon judging environments without live network.
- `🟢 REAL MODEL`: Deep Convolutional U-Net weights trained on verified Sentinel-1 SAR oil slick annotations.
- `🟡 DEMO ENGINE`: Adaptive radiometric contrast segmentation fallback when GPU/weights are unavailable.

At every step, the system communicates data provenance via the `/api/system/provenance` endpoint and the top-level **Data Provenance & Operational Mode Bar** on the dashboard.

---

## 2. Satellite SAR Imagery Integration (Copernicus CDSE)

### 2.1 Public Catalog Search (Zero Credentials Required)
OILTRACE queries the official **European Space Agency Copernicus Data Space Ecosystem (CDSE)** OData API:
- **OData Catalog URL**: `https://catalogue.dataspace.copernicus.eu/odata/v1/Products`
- **Supported Sensor**: Sentinel-1 C-Band Synthetic Aperture Radar (C-SAR)
- **Acquisition Modes**: Interferometric Wide Swath (IW), Extra Wide Swath (EW)
- **Product Type**: Level-1 Ground Range Detected (GRD) with VV and VH dual-polarization

Public metadata searches (filtering by geographical bounding box, acquisition date, polarization, and orbit direction) do **not** require API keys.

### 2.2 Direct Scene Download Authentication
To download full Level-1 `.SAFE.zip` archives (typically ~1 GB per scene) for radiometric preprocessing:

1. Register a free account at [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/).
2. Navigate to your user settings and generate an **OAuth2 Client ID** and **Client Secret**.
3. Add the credentials to your `.env` file:
   ```env
   COPERNICUS_CLIENT_ID="your-client-id"
   COPERNICUS_CLIENT_SECRET="your-client-secret"
   COPERNICUS_API_URL="https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
   COPERNICUS_TOKEN_URL="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
   ```
4. Query acquisitions or latest passes via:
   - `GET /api/satellite/cdse/search?min_lon=72.0&min_lat=18.0&max_lon=73.5&max_lat=19.5`
   - `GET /api/satellite/latest?latitude=18.9&longitude=72.8&radius_km=50`

---

## 3. Environmental Oceanographic & Atmospheric Forcing

Lagrangian drift simulation and reverse hindcasting require two primary environmental forcing fields:
1. **Surface Ocean Currents**: Eastward ($u$) and Northward ($v$) velocities in $\text{m/s}$.
2. **10-Meter Surface Wind Fields**: Wind speed ($\text{m/s}$) and direction (degrees true).

OILTRACE implements a multi-provider fallback engine (`CompositeEnvironmentalProvider`):

### 3.1 Copernicus Marine Service (CMEMS)
Provides global ocean physics analysis and reanalysis (GLOBAL_ANALYSISFORECAST_PHY_001_024 at 1/12° resolution):
1. Register at [marine.copernicus.eu](https://marine.copernicus.eu/).
2. Configure credentials in `.env`:
   ```env
   COPERNICUS_MARINE_USERNAME="your-cmems-username"
   COPERNICUS_MARINE_PASSWORD="your-cmems-password"
   ```

### 3.2 Open-Meteo Marine Operational API (Zero Credentials Required)
When CMEMS credentials are not supplied, OILTRACE automatically falls back to Open-Meteo's open-access operational oceanographic API:
- **Marine API**: `https://marine-api.open-meteo.com/v1/marine` (current velocity, direction, wave height)
- **Atmospheric API**: `https://api.open-meteo.com/v1/forecast` (ECMWF IFS 10m wind fields)
- **Status**: Live, real-world operational data with zero API key requirement.

### 3.3 Climatological Monsoon Fallback (Offline Hackathon Mode)
If internet connectivity is interrupted during judging, OILTRACE activates the deterministic Arabian Sea/Indian Ocean monsoon climatology engine (`SyntheticEnvironmentalProvider`), preserving full pipeline functionality without crashing.

---

## 4. Automatic Identification System (AIS) Telemetry

### 4.1 Supported AIS Ingestion Formats
- **Standard CSV**: NOAA MarineCadastre format (`MMSI`, `BaseDateTime`, `LAT`, `LON`, `SOG`, `COG`, `Heading`, `VesselName`, `VesselType`).
- **Standard GeoJSON**: FeatureCollection of points with properties.
- **Custom Vessel CSV**: Operator or Coast Guard exported positions.

### 4.2 Ingesting Real AIS Data
To ingest real AIS records into the local database:
```bash
# Via cURL or Postman
curl -X POST "http://localhost:8000/api/ais/import/marinecadastre" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@AIS_2026_09_sample.csv"
```
Or use the **Upload AIS Data** modal directly from the OILTRACE Web Dashboard.

### 4.3 Trajectory Anomaly Detection
OILTRACE automatically inspects ingested vessel paths using `VesselBehaviourAnomalyDetector`:
- **Sudden Deceleration**: $>35\%$ reduction from cruising speed ($>8\text{ kts}$).
- **Loitering / Drifting**: Speed $<3.5\text{ kts}$ with circular headings.
- **Sharp Course Alteration**: $>45^\circ$ course deviation within the origin uncertainty zone.
- **AIS Transmission Gaps**: $>1.5\text{ hour}$ silence near the estimated spill release time.

---

## 5. Machine Learning U-Net Training Pipeline

### 5.1 Dataset Directory Structure
Place paired SAR imagery and segmentation masks into:
```
data/dataset/
├── train/
│   ├── images/   # Grayscale normalized or dual-pol SAR (.tif / .npy / .png)
│   └── masks/    # Binary ground truth (0 = water/lookalike, 1 = oil spill)
└── val/
    ├── images/
    └── masks/
```

### 5.2 Training Command
Execute the training pipeline with early stopping and Dice loss optimization:
```bash
cd backend
python ../ml/training/train_unet.py \
    --data-dir ../data/dataset \
    --epochs 50 \
    --batch-size 8 \
    --learning-rate 1e-4 \
    --save-path ../data/models/best_model.pt
```

### 5.3 Model Loading
When `best_model.pt` is present in `data/models/`, the system automatically loads the deep learning model and upgrades its provenance status to `🟢 REAL MODEL`. When no checkpoint is present, the system transparently utilizes the analytical contrast engine (`🟡 DEMO ENGINE`) with clear diagnostic notices.

---

## 6. Verification Checklist for Evaluators

1. Check system provenance: `curl http://localhost:8000/api/system/provenance`
2. Test real Copernicus CDSE search: `curl "http://localhost:8000/api/satellite/cdse/search?min_lon=72.0&min_lat=18.0&max_lon=73.5&max_lat=19.5&limit=5"`
3. Test live ocean currents: `curl "http://localhost:8000/api/environment/current?latitude=18.9&longitude=72.8"`
4. Run backward hindcasting: `curl -X POST "http://localhost:8000/api/drift/hindcast" -H "Content-Type: application/json" -d '{"spill_event_id": 1, "duration_hours": 6.0}'`
5. Inspect attribution ranking: `curl -X POST "http://localhost:8000/api/attribution/run" -H "Content-Type: application/json" -d '{"spill_event_id": 1}'`
