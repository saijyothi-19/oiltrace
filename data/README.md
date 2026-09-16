# OILTRACE — Data Directory Structure & Ingestion Guide

This directory manages datasets for satellite remote sensing, AIS transponder records, meteorological/oceanographic forcing, and synthetic AI training/evaluation data.

---

## 1. Directory Structure

```
data/
├── raw/                     # Unprocessed input downloads (GeoTIFFs, raw AIS NMEA/CSV) [Git-ignored]
├── processed/               # Radiometrically calibrated and tiled rasters [Git-ignored]
├── satellite/               # User-uploaded or operational Sentinel-1 SAR scenes [Git-ignored]
├── ais/                     # Operational AIS vessel trajectory archives [Git-ignored]
├── environmental/           # ERA5 Reanalysis / CMEMS NetCDF/GRIB oceanographic grids [Git-ignored]
├── demo/                    # Small demonstration fixtures and thumbnails [Committed]
└── synthetic/               # Curated synthetic SAR scenes and masks for testing [Committed]
    └── oil_spill_training/
        ├── images/          # 256x256 simulated SAR amplitude arrays (.npy, .png)
        ├── masks/           # Binary ground-truth segmentation masks (.png)
        └── dataset_summary.json
```

---

## 2. Ingestion & Data Sources

### A. Satellite SAR Imagery (`data/satellite/` or `data/raw/`)
* **Expected Format**: Sentinel-1 Level-1 Ground Range Detected (GRD) C-Band SAR products (Interferometric Wide swath mode, VV/VH polarization) in GeoTIFF or standard raster format (`.tif`, `.tiff`, `.png`).
* **Source**:
  * Free Copernicus Data Space Ecosystem: [https://dataspace.copernicus.eu/](https://dataspace.copernicus.eu/)
  * Alaska Satellite Facility (ASF) Vertex: [https://search.asf.alaska.edu/](https://search.asf.alaska.edu/)
* **Naming Convention**: `S1A_IW_GRDH_1SDV_<TIMESTAMP>_<ORBIT>_<ID>.SAFE`
* **Real vs. Synthetic**:
  * Real satellite imagery placed in `data/satellite/` is automatically processed by the pipeline.
  * Synthetic benchmark data is provided under `data/synthetic/oil_spill_training/` for local unit testing and algorithm validation.

### B. AIS Vessel Telemetry (`data/ais/`)
* **Expected Format**: CSV or JSON format.
* **Schema**:
  * `mmsi`: 9-digit Maritime Mobile Service Identity (string/integer)
  * `timestamp`: ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`)
  * `latitude`: WGS84 decimal degrees ($-90.0$ to $90.0$)
  * `longitude`: WGS84 decimal degrees ($-180.0$ to $180.0$)
  * `speed`: Speed Over Ground in knots (float, optional)
  * `course`: Course Over Ground in degrees $0-360^\circ$ (float, optional)
  * `heading`: True heading in degrees $0-360^\circ$ (float, optional)
  * `vessel_name`, `ship_type`, `flag`: Static metadata (optional)
* **How to Obtain**:
  * NOAA MarineCadastre (Open Access): [https://marinecadastre.gov/ais/](https://marinecadastre.gov/ais/)
  * Danish Maritime Authority: [https://dma.dk/](https://dma.dk/)
  * Ingestion Endpoint: Use the Web UI at `/vessels` or `POST /api/ais/import`.

### C. Environmental Forcing (`data/environmental/`)
* **Expected Format**: Gridded surface wind (10m $u, v$) and surface ocean currents ($u, v$).
* **Source**:
  * ECMWF ERA5 Atmospheric Reanalysis: [https://cds.climate.copernicus.eu/](https://cds.climate.copernicus.eu/)
  * Copernicus Marine Service (CMEMS Global Ocean Physics Analysis): [https://marine.copernicus.eu/](https://marine.copernicus.eu/)
* **Fallback**: When live NetCDF/GRIB files are not placed in `data/environmental/`, the system automatically activates the validated seasonal climatological oceanographic engine (`SyntheticEnvironmentalProvider`) representing Arabian Sea / Indian Ocean monsoon currents and winds.

---

## 3. Large File Handling Policy

* In compliance with version control best practices, large multi-gigabyte GeoTIFFs, live AIS feeds, and model weights are **excluded from Git** via `.gitignore`.
* The repository maintains small synthetic test fixtures and `.gitkeep` directory anchors so that all paths resolve seamlessly on fresh clones.
