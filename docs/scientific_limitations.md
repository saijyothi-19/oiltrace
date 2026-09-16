# Scientific Limitations, Uncertainty & Evidentiary Boundaries

**Project**: OILTRACE — AI-Powered Marine Oil Spill Detection, Drift Reconstruction & Vessel Attribution System  
**Hackathon**: Smart India Hackathon 2026 (Problem Statement SIH26143)

---

## 1. Executive Summary

Decision-support systems in operational maritime surveillance operate in complex physical environments where sensor coverage, meteorological dynamics, and physical oceanography introduce inherent uncertainties. 

This document outlines the fundamental scientific, environmental, and observational boundaries of the OILTRACE platform.

---

## 2. SAR Imaging & Remote Sensing Limitations

### 2.1 The Physics of Radar Backscatter Dampening
Synthetic Aperture Radar (SAR) detects marine oil slicks indirectly:
- Radar waves backscatter off capillary waves (wavelengths $\lambda \approx 1-10 \text{ cm}$) on the ocean surface (Bragg scattering).
- Oil films possess higher surface tension, dampening capillary waves and flattening the sea surface.
- The smoothed sea surface reflects radar energy away from the sensor like a mirror, appearing as a **dark patch** in calibrated radar amplitude images.

### 2.2 Natural Look-Alikes
Dark patches can be produced by non-petroleum phenomena:
1. **Low-Wind Areas ($< 2.5 \text{ m/s}$)**: In calm sea states, capillary waves cannot form even on clean water, producing extensive dark areas indistinguishable from crude oil without contextual meteorological data.
2. **Biogenic Slicks & Algal Blooms**: Organic secretions from plankton, fish oils, and algal blooms dampen capillary waves identically to petroleum hydrocarbons.
3. **Internal Waves & Upwelling**: Subsurface internal gravity waves modulate surface roughness, creating alternating bright and dark striations.
4. **Rain Cells & Atmospheric Attenuation**: Heavy tropical convective downpours dampen capillary waves and scatter C-band radar pulses.
5. **Ship Wakes**: The turbulent water behind large vessels can produce linear dark trails that persist for several nautical miles.

---

## 3. Hydrodynamic & Lagrangian Drift Uncertainties

### 3.1 Empirical Parameters
The Lagrangian particle drift model uses standard maritime search-and-rescue empirical coefficients:
- **Windage Factor ($C_w \approx 3\%$):** Assumes typical crude oil surface slick properties. Weathered emulsified slicks ("chocolate mousse") experience different wind drag profiles.
- **Coriolis Deflection Angle ($\approx 10^\circ$):** Represents an empirical approximation of Ekman spiral wind-driven currents in surface boundary layers.

### 3.2 Spatio-Temporal Resolution of Environmental Forcing
- Real ocean currents (e.g., Copernicus Marine Service / INCOIS models) are typically resolved on grids of $0.083^\circ$ (~9 km) with 1-3 hour updates.
- Micro-scale coastal bathymetry, tidal rips, internal bores, and sub-mesoscale eddies ($< 2 \text{ km}$) may not be fully resolved in global reanalysis datasets.

### 3.3 Weathering & Evaporation Dynamics
- Crude oils undergo natural evaporation, emulsification, photo-oxidation, dissolution, and biodegradation.
- Highly volatile light condensates evaporate rapidly within 6-24 hours, reducing observable surface footprint over time.

---

## 4. Automatic Identification System (AIS) Vulnerabilities

### 4.1 RF Propagation & Satellite Reception Gaps
- Terrestrial VHF AIS signals have a line-of-sight horizon limit of approximately $20-40 \text{ nautical miles}$.
- Satellite-based AIS (S-AIS) receivers in Low Earth Orbit (LEO) experience signal attenuation, high-density RF packet collisions (especially in choke points like the Malacca Strait or Gulf of Kutch), and multi-hour revisit latency.

### 4.2 Intentional Non-Compliance & "Dark Ships"
- Vessels engaged in illicit discharge or sanction evasion may disable their Class A transponders.
- Non-SOLAS vessels (small artisanal fishing boats, small tugs) are not legally mandated to carry Class A AIS transponders.

### 4.3 Spoofing & Multipath Errors
- GNSS spoofing, MMSI duplication, and false navigation status flags can occur in unauthenticated open-broadcast AIS networks.

---

## 5. Decision-Support vs Courtroom Admissibility

1. **Investigative Triangulation:** OILTRACE outputs must serve as actionable leads for maritime law enforcement (triggering Coast Guard flyovers, patrol vessel interceptions, and port state control inspections).
2. **Physical Sampling Requirement:** Definitive legal prosecution under MARPOL Annex I or national environmental legislation requires physical forensic chemical fingerprinting (e.g., Gas Chromatography-Mass Spectrometry / GC-MS biomarkers comparing ship bunker/bilge samples with the sea surface slick).
