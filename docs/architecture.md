# OILTRACE System Architecture & Technical Specification

**Project**: OILTRACE — AI-Powered Marine Oil Spill Detection, Drift Reconstruction & Vessel Attribution System  
**Hackathon**: Smart India Hackathon 2026 (Problem Statement SIH26143)  
**Classification**: Scientific Decision-Support System (Prototype)

---

## 1. High-Level Architectural Overview

OILTRACE is engineered as a decoupled, asynchronous, geospatial decision-support platform designed for maritime enforcement agencies (e.g., Indian Coast Guard, State Maritime Boards, Directorate General of Shipping).

```
   +-------------------------------------------------------------------------+
   |                       USER / ANALYST LAYER                              |
   |   React 18 + Vite SPA | MapLibre GL Interactive GIS | Tailwind CSS      |
   +-------------------------------------------------------------------------+
                                      |
                             REST APIs / JSON / GeoJSON
                                      v
   +-------------------------------------------------------------------------+
   |                         FASTAPI CORE BACKEND                            |
   |  - Auth & RBAC (Admin, Analyst, Viewer) with JWT & PBKDF2-SHA256        |
   |  - Spatial REST Endpoints (AIS, SAR, Spills, Drift, Candidates)         |
   |  - Incident Dossier Engine (JSON metadata & Printable HTML Reports)     |
   +-------------------------------------------------------------------------+
          |                       |                           |
          v                       v                           v
   +--------------+      +------------------+       +------------------+
   |  ML / VISION |      |  HYDRODYNAMIC    |       |  SPATIO-TEMPORAL |
   |  INFERENCE   |      |  DRIFT SIMULATOR |       |  CORRELATION     |
   +--------------+      +------------------+       +------------------+
   | - Sentinel-1 |      | - Lagrangian     |       | - AIS Cleaner &  |
   |   SAR Lee    |      |   Particle Model |         Trajectory Interp|
   |   Despeckle  |      | - 100% Ocean     |       | - 5-Criteria     |
   | - PyTorch    |      |   Currents       |         Explainable      |
   |   U-Net Segm.|      | - 3% Windage     |         Scoring Engine   |
   | - Lookalike  |      |   with Coriolis  |       | - Dynamic Radius |
   |   Filtering  |      | - Hindcasting    |         & Time Windows   |
   +--------------+      +------------------+       +------------------+
          |                       |                           |
          +-----------------------+---------------------------+
                                  |
                                  v
   +-------------------------------------------------------------------------+
   |                        PERSISTENCE & STORAGE                            |
   |  - Hybrid Geo-Abstraction: PostGIS (Production) / SQLite GeoJSON (Dev)  |
   |  - Alembic Version-Controlled Database Migrations                       |
   |  - Local File Storage: GeoTIFFs, NetCDF/GRIB, AIS CSVs, PDF/HTML Dossiers|
   +-------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Satellite Ingestion & SAR Image Processing
- **Sensors Supported**: Sentinel-1A/1B C-band SAR (Interferometric Wide Swath - IW, Ground Range Detected - GRD).
- **Polarizations**: VV (primary ocean surface roughness channel), VH (cross-polarization).
- **Preprocessing Pipeline**:
  1. Radiometric calibration to radar backscatter intensity $\sigma^0$ in decibels (dB).
  2. Lee speckle filtering ($5 \times 5$ window) to suppress multiplicative coherent radar noise while preserving edges.
  3. Min-Max normalization to standard radiometric dynamic ranges $[-28 \text{ dB}, -5 \text{ dB}]$.
  4. Tiling to $256 \times 256$ or $512 \times 512$ chips with $32$-pixel overlap for boundary continuity.
  5. Contrast adaptive segmentation fallback for non-GPU or bleeding-edge runtimes.

### 2.2 Deep Semantic Segmentation & Spill Characterization
- **Model**: PyTorch U-Net architecture with 4 encoder-decoder stages, double convolution blocks, batch normalization, ReLU, and skip connections.
- **Characterization Engine**:
  - Polygonization of binary threshold masks via OpenCV contour detection with Douglas-Peucker simplification.
  - Coordinate re-projection from pixel space to WGS84 GeoJSON (`EPSG:4326`).
  - Geodesic spatial metrics: True surface area ($km^2$), perimeter ($km$), and center of mass centroid coordinates.
- **Lookalike Discrimination**:
  - Rejection filters for low-wind natural slicks ($< 2.5 \text{ m/s}$ surface wind), biogenic organic films, and ship wake dampening.

### 2.3 Lagrangian Particle Drift & Hindcasting Engine
- **Methodology**: Monte Carlo Lagrangian particle tracking with $N \in [100, 1000]$ discrete particles initialized across the detected spill polygon.
- **Physical Forcing Equations**:
  $$\vec{V}_{particle} = \vec{U}_{current} + C_w \cdot \mathbf{R}(\theta) \vec{W}_{wind} + \vec{U}_{diffusion}'$$
  - $\vec{U}_{current}$: Surface ocean currents ($100\%$ velocity advection).
  - $C_w$: Wind drag coefficient ($3.0\%$).
  - $\mathbf{R}(\theta)$: Coriolis deflection matrix ($\theta \approx 10^\circ$ clockwise in the Northern Hemisphere).
  - $\vec{U}_{diffusion}'$: Horizontal turbulent diffusion modeled by random walk scaled by turbulent diffusivity coefficient $D_h \approx 1.0 \text{ m}^2/\text{s}$.
- **Backward Hindcasting**:
  - Inverts time velocity vectors ($\Delta t < 0$) to trace the spill's trajectory back in time from SAR acquisition to the release event.
  - Computes the convex hull and 2D standard deviation ellipse of backward particle dispersion to define the **Origin Uncertainty Polygon**.

### 2.4 AIS Ingestion & Trajectory Interpolation
- **Input Formats**: NMEA 0183 standard messages (Types 1, 2, 3, 5, 18, 19) and structured CSV feeds.
- **Cleaning & Quality Control**:
  - MMSI validation (valid 9-digit format, Maritime Identification Digits checks).
  - Geographic bounds validation (latitude $[-90, 90]$, longitude $[-180, 180]$, non-zero Null Island filter).
  - Physical kinematic plausibility (rejection of commercial ship speeds $> 50 \text{ knots}$).
- **Trajectory Processing**:
  - Piecewise linear interpolation between AIS pings with Haversine great-circle distance.
  - Heading and course-over-ground vector matching against origin geometry.

### 2.5 Explainable Attribution Scoring Engine
Evaluates every vessel operating within the spatial-temporal search window against the reconstructed origin:
$$S_{total} = 0.35 S_{spatial} + 0.30 S_{temporal} + 0.20 S_{trajectory} + 0.10 S_{behaviour} + 0.05 S_{data\_quality}$$

---

## 3. Database Schema Architecture

The database layer utilizes SQLAlchemy 2.0 ORM with a custom dual-dialect abstraction layer (`app.db.spatial.Geometry`):
- In **PostGIS / PostgreSQL**, geometry columns map directly to native `geometry(Polygon, 4326)` and `geometry(Point, 4326)` types with spatial index R-Trees.
- In **SQLite / Dev**, geometry columns map transparently to JSON text fields storing standard GeoJSON dictionaries, enabling zero-install local development and cross-platform automated testing.

### Key Entities:
1. `users`: Authentication, credentials (PBKDF2-SHA256), roles (`ADMIN`, `ANALYST`, `VIEWER`).
2. `satellite_images`: Product identifiers, sensor type, orbit, bounding boxes, raw file paths.
3. `spill_events`: Detected spills, surface area, perimeter, centroid, status, GeoJSON geometries.
4. `spill_detections`: Fine-grained detection runs, confidence scores, thresholding parameters.
5. `drift_simulations`: Forward and backward simulation records, duration, timestep, environmental parameters.
6. `drift_particles`: Individual particle tracking coordinates across time steps.
7. `vessels`: Vessel registry (MMSI, IMO, vessel name, flag state, ship type, dimensions).
8. `ais_positions`: Raw and interpolated position reports (coordinates, SOG, COG, heading, timestamp).
9. `vessel_candidates`: Scored candidate rankings, sub-criteria breakdowns, evidence summaries.
10. `investigations`: Formal case management records, status, assigned analysts, chronological notes.
