# OILTRACE — AI-Powered Marine Oil Spill Detection, Drift Reconstruction & Vessel Attribution System

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH%202026-Problem%20SIH26143-0284c7.svg)](https://sih.gov.in)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115-059669.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%20%2B%20MapLibre-6366f1.svg)](https://maplibre.org)
[![PyTorch](https://img.shields.io/badge/Deep%20Learning-U--Net%20SAR-ee4c2c.svg)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **SMART INDIA HACKATHON 2026 — PROBLEM STATEMENT SIH26143**  
> *“Leveraging satellite imagery to determine oil spills at sea along with AIS data correlations to identify vessel responsible for the spill.”*

---

> [!IMPORTANT]
> **SCIENTIFIC & LEGAL DISCLAIMER**  
> **OILTRACE is a decision-support system. Candidate vessel rankings are based on available data and mathematical correlation and do not establish legal responsibility or causation.**  
> The system assists maritime pollution investigators, coast guard authorities, and environmental agencies by narrowing suspect search volumes and ranking candidate vessels. It never establishes definitive guilt or judicial liability.  
> *All synthetic demonstration data provided in this repository is explicitly labeled: "Synthetic demonstration data — not real-world evidence."*

---

## 1. Overview

**OILTRACE** bridges the critical operational gap between satellite remote sensing of offshore oil slicks and maritime vessel traffic monitoring. When an oil spill is identified on satellite Synthetic Aperture Radar (SAR), hours or days have often elapsed since discharge. Marine currents and surface winds advect and disperse the slick far from the release coordinates. 

OILTRACE automatically:
1. Segments low-backscatter oil slicks from satellite SAR imagery using deep learning.
2. Derives geodesic surface area ($\text{km}^2$), perimeter ($\text{km}$), and centroid coordinates.
3. Simulates backward Lagrangian drift advection to reconstruct the historical origin release zone and time window.
4. Spatially and temporally correlates historical Automatic Identification System (AIS) transponder tracks.
5. Scores intersecting vessels across 5 evidentiary dimensions to produce an explainable, ranked candidate list.

---

## 2. End-to-End System Architecture

```
Sentinel-1 (C-Band SAR IW)
          ↓
SAR Preprocessing (Radiometric Calibration + 5×5 Lee Speckle Filter + Normalization)
          ↓
AI Detection (Deep Convolutional U-Net Semantic Segmentation + Lookalike Penalty)
          ↓
Spill Characterization (WGS84 Geodesic Area km², True Perimeter km, Centroid [lon, lat])
          ↓
Drift / Hindcasting (2D Lagrangian Particle Model + Inverted Time + Windage & Coriolis)
          ↓
Probable Origin Reconstruction (95% Confidence Origin Uncertainty Polygon + Release Window)
          ↓
AIS Correlation (Spatial Filtering < 50 km + Temporal Window Sync + Trajectory Extraction)
          ↓
Candidate Vessel Attribution (5-Criteria Scoring: Spatial, Temporal, Trajectory, Behavior, Data Quality)
          ↓
Interactive Web GIS Dashboard (MapLibre GL + OpenStreetMap / Ocean Bathymetry + Incident Dossiers)
```

---

## 3. Key Features

- **SAR Oil Spill Detection**: Radiometric calibration to $\sigma^0$ (dB), adaptive Lee filter, and U-Net architecture segmenting dark ocean slicks while penalizing lookalikes (natural films, low wind $< 2.5\text{ m/s}$).
- **Copernicus CDSE Sentinel-1 Integration**: Direct OData catalog spatial-temporal search and OAuth2 download pipeline for Sentinel-1 C-SAR Level-1 GRD acquisitions directly from the European Space Agency Copernicus Data Space Ecosystem.
- **Real Environmental Forcing Engine**: Multi-provider cascading ocean currents ($u, v\text{ m/s}$) and 10m wind vectors via Open-Meteo Marine (live operational open API) and Copernicus Marine Service (CMEMS), with deterministic Arabian Sea monsoon climatology for offline hackathon judging.
- **Geospatial Characterization & Spill Age**: Automated vector polygonization (Shapely), Douglas-Peucker simplification, true ellipsoidal geodesic surface area computation, slick elongation ratios, and scientifically cautious Fay-regime spill age estimation bounds.
- **Lagrangian Drift Hindcasting**: Reverse Monte Carlo particle simulator ($N=150$) incorporating 100% surface currents, 3% wind drag with Coriolis deflection, and Gaussian turbulent diffusion ($\sigma = \sqrt{2 K_h \Delta t}$) generating origin uncertainty probability polygons.
- **Forward Drift Prediction**: Forward advection trajectory modeling to project coastal impact zones and facilitate containment barrier deployment.
- **AIS Ingestion & Anomaly Detection**: Ingestion for NOAA MarineCadastre standard CSV and live transponder telemetry, coupled with rule-based detection for sudden deceleration ($>35\%$), loitering, sharp course alterations ($>45^\circ$), and suspicious AIS blackout gaps near origin zones.
- **5-Criteria Explainable Attribution**:
  $$S_{\text{total}} = 0.35 S_{\text{spatial}} + 0.30 S_{\text{temporal}} + 0.20 S_{\text{trajectory}} + 0.10 S_{\text{behaviour}} + 0.05 S_{\text{data\_quality}}$$
  Classifies candidates into **HIGH**, **MEDIUM**, and **LOW** priority with transparent evidence checklists and explainable matrix view.
- **Scientific Honesty & Mode Badging**: Complete visual mode badges (`🟢 REAL DATA`, `🟡 DEMO DATA`, `🟢 REAL MODEL`, `🟡 DEMO ENGINE`) backed by `/api/system/provenance` and documented in [docs/REAL_DATA_SETUP.md](docs/REAL_DATA_SETUP.md).
- **Interactive Web GIS Operations Dashboard**: MapLibre GL canvas with zero-API-key basemaps (OpenStreetMap Standard & Esri World Ocean Bathymetry) and 8 analytical vector layers.
- **Incident Investigation Workflow**: Case management lifecycle (`NEW` $\to$ `UNDER REVIEW` $\to$ `HIGH PRIORITY` $\to$ `RESOLVED` / `CLOSED`) with investigator notes.
- **Formal Audit Reporting**: Print-ready and exportable incident dossiers in both JSON and print-formatted CSS for administrative enforcement.

---

## 4. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack React Query, Lucide Icons |
| **Mapping / GIS** | MapLibre GL JS (v4.7.1), GeoJSON (RFC 7946), OpenStreetMap, Esri Ocean Bathymetry |
| **Backend API** | FastAPI (Python 3.10+ / 3.14), Uvicorn, Pydantic v2 |
| **AI / Deep Learning** | PyTorch, Convolutional U-Net, OpenCV, NumPy |
| **Geospatial & Remote Sensing** | Shapely, Rasterio, GeoPandas, PyProj (WGS84 EPSG:4326) |
| **Database** | PostgreSQL + PostGIS (Production) / SQLite with GeoJSON spatial decorator (Development) |
| **Drift & Oceanography** | Numerical Lagrangian particle advection emulator, ERA5 / CMEMS climatological forcing |
| **Deployment** | Docker, Docker Compose, Nginx |

---

## 5. Project Directory Structure

```
oiltrace/
│
├── backend/                 # FastAPI REST application
│   ├── alembic/             # Database migration configurations
│   ├── app/
│   │   ├── ais/             # AIS trajectory reconstruction & kinematic filtering
│   │   ├── api/             # REST endpoint routers (spills, drift, attribution, etc.)
│   │   ├── attribution/     # 5-factor scoring engine and explainability logic
│   │   ├── core/            # Configuration, JWT auth, security, lifespans
│   │   ├── db/              # SQLAlchemy session & GeoJSON spatial decorator
│   │   ├── drift/           # Lagrangian numerical drift simulator
│   │   ├── geospatial/      # Shapely polygonization & geodesic area calculations
│   │   ├── models/          # Declarative database entities
│   │   ├── schemas/         # Pydantic validation schemas
│   │   └── services/        # Satellite, AIS, environmental, and report services
│   ├── tests/               # Pytest suite (32 unit & integration tests)
│   └── requirements.txt     # Python backend dependencies
│
├── frontend/                # React 18 + TypeScript + Vite SPA
│   ├── public/              # Static public assets
│   ├── src/
│   │   ├── components/      # UI components (Navbar, Sidebar, Panels, Modals)
│   │   ├── layouts/         # RootLayout with persistent banner & navigation
│   │   ├── maps/            # MapLibre GL canvas & zero-key basemap provider factory
│   │   ├── pages/           # Dashboard, Spills, Vessels, Investigations, Reports
│   │   ├── services/        # Axios API client services
│   │   └── types/           # TypeScript interfaces and domain models
│   ├── package.json
│   └── vite.config.ts
│
├── ml/                      # Machine Learning Subsystem
│   ├── datasets/            # PyTorch dataset loaders & synthetic SAR generator
│   ├── evaluation/          # IoU, Dice, Precision, Recall, F1 metric evaluators
│   ├── inference/           # Sliding-window inference with Hann window blending
│   ├── models/              # Convolutional U-Net PyTorch architecture
│   ├── preprocessing/       # Radiometric calibration & 5x5 Lee speckle filter
│   └── training/            # Training loop, config, and atomic checkpoint manager
│
├── drift/                   # Standalone oceanographic drift reference modules
├── data/                    # Data directory (structured subfolders, see data/README.md)
├── docs/                    # Technical architecture & scientific documentation
├── reports/                 # Output directory for exported incident dossiers
├── scripts/                 # Utility scripts (e.g., load_demo.py)
├── notebooks/               # Jupyter research and prototyping notebooks
├── docker-compose.yml       # Production multi-container orchestration
├── .gitignore               # Strict version control exclusion rules
├── .env.example             # Clean environment template without secrets
├── README.md                # Project documentation
└── LICENSE                  # MIT License
```

---

## 6. Installation & Setup

### Prerequisites
- **Python**: 3.10, 3.11, 3.12, or 3.14
- **Node.js**: LTS v18+ or v20+ with `npm`
- **Git**

### Step 1: Clone the Repository
```bash
git clone https://github.com/<USERNAME>/oiltrace.git
cd oiltrace
```

### Step 2: Environment Configuration
Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
*(Optional: For frontend specific overrides, copy `frontend/.env.example` to `frontend/.env`).*

Configure your local `.env`:
- `SECRET_KEY`: Set a secure random string (e.g., `openssl rand -hex 32`).
- `DATABASE_URL`: Defaults to `sqlite:///./oiltrace.db` for zero-configuration local development. For PostgreSQL with PostGIS, set:
  `postgresql+psycopg2://<user>:<password>@localhost:5432/oiltrace_db`

---

## 7. Running the Application

### Option A: Local Development

#### 1. Start the Backend API
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Start the Frontend Dashboard
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** in your browser.

---

### Option B: Docker Compose (Full Stack)
```bash
docker-compose up --build
```
- Frontend Web UI: [http://localhost:5173](http://localhost:5173)
- Backend REST API: [http://localhost:8000](http://localhost:8000)
- OpenAPI Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 8. Demonstration Scenario

The application includes an instant demonstration loader for hackathon evaluation:
1. Open the dashboard at [http://localhost:5173](http://localhost:5173).
2. Click the **"Load Demo Investigation"** button in the top navigation bar (or run `python scripts/load_demo.py`).
3. The platform seeds:
   - **Sentinel-1A SAR Scene** off Mumbai / Arabian Sea corridor.
   - **$14.20\text{ km}^2$ Slick Polygon** with 93.5% confidence.
   - **Backward Lagrangian Hindcast** ($N=120$ particles) reconstructing an 8-hour origin release ellipse.
   - **5 Candidate Vessels**:
     - *MT ARABIAN PRIDE* (Crude Tanker) — **Score: 91.4 (HIGH)**, intersects origin with a $14.2 \to 7.8\text{ kn}$ speed drop.
     - *MV HIMALAYA TRADER* (Bulk Carrier) — **Score: 64.2 (MEDIUM)**, passed 12 km north.
     - *MT AL-BAHR* (Chemical Tanker) — **Score: 78.5 (HIGH)**, flagged for a 3-hour AIS transponder gap near the origin.
     - *MSC INDUS* (Container Ship) — **Score: 18.4 (LOW)**, temporal transit offset $> 5\text{ hours}$.
     - *FV SAGAR KANYA* (Trawler) — **Score: 32.1 (LOW)**, near spill now, but far away during release.

---

## 9. Testing & Quality Assurance

OILTRACE contains an automated test suite with 100% pass rate:

```bash
# Backend pytest suite (32 unit & integration tests)
cd backend
python -m pytest tests/ -v

# Frontend TypeScript and production bundle compilation
cd frontend
npm run build
```

---

## 10. Operational Limitations

1. **SAR Look-alikes**: Natural phenomena (biogenic surface films, grease ice, low-wind shadows $< 2.5\text{ m/s}$) can produce radar backscatter dampening mimicking crude slicks. Human-in-the-loop analyst verification (`ACCEPT` / `REJECT`) is mandatory.
2. **AIS Transponder Blackouts**: Vessels involved in deliberate discharge may disable Class A AIS transponders. OILTRACE flags suspicious temporal gaps near origin zones, but cannot track vessels without active signals or secondary optical/radar tracking.
3. **Oceanographic Uncertainty**: Real-time ocean currents and windage involve turbulent dispersion. The backward hindcast generates a probabilistic uncertainty ellipse rather than an exact coordinate point.
4. **Data Availability**: Satellite revisits occur at discrete orbital intervals (1–6 days depending on latitude and constellation).

---

## 11. Scientific Disclaimer

> **“OILTRACE is a decision-support system. Candidate vessel rankings are based on available data and mathematical correlation and do not establish legal responsibility or causation.”**

---

## 12. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.  
Developed for **Smart India Hackathon 2026** (Problem Statement SIH26143).
