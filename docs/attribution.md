# Vessel Attribution Methodology & Explainable Scoring Framework

**Project**: OILTRACE — AI-Powered Marine Oil Spill Detection, Drift Reconstruction & Vessel Attribution System  
**Hackathon**: Smart India Hackathon 2026 (Problem Statement SIH26143)

---

## 1. Legal & Scientific Premise

> **CRITICAL LEGAL NOTICE**:  
> OILTRACE is an analytical decision-support tool. It computes probabilistic correlations between maritime surveillance datasets. The system **NEVER** establishes or claims definitive legal responsibility, criminal liability, or maritime fault. All rankings represent relative likelihood based on available evidence.

---

## 2. Mathematical Scoring Formulation

The composite attribution score $S_{total} \in [0, 100]$ evaluates how closely a vessel's recorded position, timing, kinematics, and operational patterns coincide with the reconstructed oil spill origin.

$$S_{total} = w_s S_{spatial} + w_t S_{temporal} + w_{tr} S_{trajectory} + w_b S_{behaviour} + w_{dq} S_{data\_quality}$$

Where the weights satisfy $\sum w_i = 1.0$:
- $w_s = 0.35$ (Spatial Proximity: 35%)
- $w_t = 0.30$ (Temporal Coincidence: 30%)
- $w_{tr} = 0.20$ (Trajectory & Heading Alignment: 20%)
- $w_b = 0.10$ (Behavioral & Kinematic Anomaly: 10%)
- $w_{dq} = 0.05$ (Data Quality & Transponder Continuity: 5%)

---

## 3. Sub-Criteria Mathematical Models

### 3.1 Spatial Score ($S_{spatial}$, Weight: 35%)
Evaluates the minimum geodesic distance $d_{min}$ between the vessel's recorded waypoints and the backward-hindcast spill origin polygon:

$$S_{spatial} = 
\begin{cases}
98.0, & \text{if vessel waypoint falls within origin uncertainty polygon} \\
\max\left(0, 95.0 \cdot \left(1 - \frac{d_{min}}{R_{max}}\right)\right), & \text{otherwise}
\end{cases}$$

Where $R_{max}$ is the search radius (default: $50.0 \text{ km}$).

### 3.2 Temporal Score ($S_{temporal}$, Weight: 30%)
Evaluates the absolute time offset $\Delta t$ between the vessel's closest point of approach (CPA) and the estimated origin release time $t_{origin}$:

$$\Delta t = |t_{vessel\_cpa} - t_{origin}|$$

$$S_{temporal} = \max\left(0, 100.0 \cdot \left(1 - \frac{\Delta t}{T_{window}}\right)\right)$$

Where $T_{window}$ is the temporal search window (default: $12.0 \text{ hours}$).

### 3.3 Trajectory & Heading Score ($S_{trajectory}$, Weight: 20%)
Measures the directional alignment between the vessel's Course Over Ground (COG) and the bearing vector pointing directly to the origin centroid:

$$\Delta \theta = |(\text{COG} - \text{Bearing}_{origin} + 180^\circ) \pmod{360^\circ} - 180^\circ|$$

$$S_{trajectory} = 
\begin{cases}
92.0, & \text{if intersects origin or } d_{min} < 5.0 \text{ km} \\
\max\left(78.0, 85.0 \cdot \left(1 - \frac{\Delta \theta}{180^\circ}\right)\right), & \text{if } d_{min} < 15.0 \text{ km} \\
\max\left(0, 85.0 \cdot \left(1 - \frac{\Delta \theta}{180^\circ}\right)\right), & \text{otherwise}
\end{cases}$$

### 3.4 Behavioral Anomaly Score ($S_{behaviour}$, Weight: 10%)
Detects suspicious or non-standard commercial transit behaviors:
- **Sudden Speed Drop**: While underway at open sea ($> 8 \text{ knots}$), dropping speed by $\ge 35\%$ or slowing to $< 4 \text{ knots}$ near the origin.
- **Zigzag / Loitering**: Non-linear deviation from standard shipping corridors.

$$S_{behaviour} = 
\begin{cases}
90.0, & \text{if significant speed drop or anomalous loitering detected} \\
50.0, & \text{standard steady-speed transit}
\end{cases}$$

### 3.5 Data Quality & Transponder Continuity ($S_{data\_quality}$, Weight: 5%)
Monitors the continuity of AIS transponder signals. A sudden cessation of AIS transmissions ("dark ship" behavior or transmission gap $> 1.5 \text{ hours}$) in the vicinity of the spill origin raises an alert:

$$S_{data\_quality} = 
\begin{cases}
60.0, & \text{if suspicious AIS gap }> 1.5 \text{ h within } 25 \text{ km of origin} \\
92.0, & \text{normal continuous AIS broadcast}
\end{cases}$$

---

## 4. Priority Classification

| Overall Score Range | Priority Tier | Operational Recommendation |
| :--- | :--- | :--- |
| **Score $\ge 75.0$** | <span style="color:red; font-weight:bold;">HIGH / CRITICAL</span> | Immediate analyst review, coastal patrol dispatch, flag state inquiry. |
| **$50.0 \le \text{Score} < 75.0$** | <span style="color:orange; font-weight:bold;">MEDIUM</span> | Secondary correlation, port state control inspection upon arrival. |
| **$\text{Score} < 50.0$** | <span style="color:blue; font-weight:bold;">LOW</span> | Peripheral transit, low correlation, archival retention. |

---

## 5. Explainable Evidence Output

For every candidate, the engine outputs human-readable evidence summaries, including:
1. Exact distance from reconstructed origin at estimated release time.
2. Temporal offset from release window.
3. Track intersection status with the 95% confidence origin polygon.
4. Kinematic analysis (speed changes, heading deviations).
5. Signal integrity status (continuous reception vs AIS gap).
