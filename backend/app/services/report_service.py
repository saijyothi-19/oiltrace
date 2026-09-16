from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.spill import SpillEvent
from app.models.drift import DriftSimulation, SimulationType
from app.models.attribution import VesselCandidate
from app.models.vessel import Vessel
from app.core.config import settings

class ReportService:
    @staticmethod
    def generate_dossier_data(db: Session, spill_id: int) -> Dict[str, Any]:
        spill = db.query(SpillEvent).filter(SpillEvent.id == spill_id).first()
        if not spill:
            raise ValueError(f"Spill #{spill_id} not found.")

        drift_sim = db.query(DriftSimulation).filter(
            DriftSimulation.spill_event_id == spill.id,
            DriftSimulation.simulation_type == SimulationType.BACKWARD
        ).order_by(DriftSimulation.created_at.desc()).first()

        candidates = db.query(VesselCandidate).filter(
            VesselCandidate.spill_event_id == spill.id
        ).order_by(VesselCandidate.overall_score.desc()).all()

        candidates_list = []
        for rank, c in enumerate(candidates, start=1):
            vessel = db.query(Vessel).filter(Vessel.id == c.vessel_id).first()
            candidates_list.append({
                "rank": rank,
                "vessel_id": c.vessel_id,
                "vessel_name": vessel.name if vessel else f"VESSEL-{c.vessel_id}",
                "mmsi": vessel.mmsi if vessel else str(c.vessel_id),
                "ship_type": vessel.ship_type if vessel else "Tanker",
                "flag": vessel.flag if vessel else "Unknown",
                "priority": c.priority.value,
                "overall_score": c.overall_score,
                "scores": {
                    "spatial": c.spatial_score,
                    "temporal": c.temporal_score,
                    "trajectory": c.trajectory_score,
                    "behaviour": c.behaviour_score,
                    "data_quality": c.data_quality_score,
                },
                "evidence_summary": c.explanation_json.get("explanation_points", []),
            })

        env_meta = {}
        if drift_sim and drift_sim.parameters_json:
            env_meta = drift_sim.parameters_json.get("environmental", {})

        return {
            "report_id": f"OILTRACE-DOSSIER-2026-{spill.id:05d}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": spill.status.value,
            "disclaimer": settings.DISCLAIMER_TEXT,
            "spill_incident": {
                "id": spill.id,
                "detected_at": spill.detected_at.isoformat() if spill.detected_at else None,
                "satellite_source": spill.satellite_image.satellite if spill.satellite_image else "Sentinel-1A SAR",
                "polarization": spill.satellite_image.polarization if spill.satellite_image else "VV",
                "area_km2": round(spill.area_km2, 2),
                "perimeter_km": round(spill.perimeter_km, 2),
                "confidence": round(spill.confidence * 100.0, 1),
                "model_version": spill.model_version,
                "centroid": spill.centroid,
            },
            "oceanographic_drift": {
                "simulation_type": drift_sim.simulation_type.value if drift_sim else "N/A",
                "duration_hours": drift_sim.duration_hours if drift_sim else 12.0,
                "estimated_origin_time": drift_sim.start_time.isoformat() if drift_sim else None,
                "particle_count": drift_sim.particle_count if drift_sim else 150,
                "model_confidence": round((drift_sim.confidence if drift_sim else 0.85) * 100.0, 1),
                "environmental_forcing": env_meta,
            },
            "ranked_candidate_vessels": candidates_list,
            "scientific_limitations": [
                "SAR imagery backscatter dampening can be mimicked by look-alike phenomena including calm wind slicks (< 2.5 m/s) and biogenic films.",
                "Backward drift simulations assume constant horizontal turbulent diffusivity and standard 3% wind drag empirical parameters.",
                "AIS transponder signals are susceptible to antenna shading, line-of-sight propagation loss, and RF packet collisions.",
                "Rankings represent probabilistic correlation and do not establish definitive legal causation or liability.",
            ],
        }

    @classmethod
    def generate_html_report(cls, db: Session, spill_id: int) -> str:
        data = cls.generate_dossier_data(db, spill_id)
        spill = data["spill_incident"]
        drift = data["oceanographic_drift"]
        cands = data["ranked_candidate_vessels"]

        candidates_rows = ""
        for c in cands:
            badge_color = "#dc2626" if c["priority"] == "HIGH" else "#d97706" if c["priority"] == "MEDIUM" else "#2563eb"
            evidence_bullets = "".join(f"<li>{e}</li>" for e in c["evidence_summary"][:2])
            candidates_rows += f"""
            <tr>
                <td style="font-weight:bold; color:#0284c7;">#{c['rank']}</td>
                <td style="font-weight:bold;">{c['vessel_name']}</td>
                <td>{c['mmsi']}</td>
                <td>{c['ship_type']}</td>
                <td><span style="background:{badge_color}; color:white; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:bold;">{c['priority']}</span></td>
                <td style="font-weight:bold; font-size:13px;">{c['overall_score']}</td>
                <td style="font-size:11px;"><ul>{evidence_bullets}</ul></td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{data['report_id']} - Marine Oil Spill Attribution Dossier</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; line-height: 1.5; }}
                .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; }}
                h1 {{ font-size: 20px; color: #0f172a; margin: 0; }}
                .meta-box {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; margin-bottom: 20px; font-size: 12px; }}
                .meta-box strong {{ display: block; font-size: 14px; color: #0f172a; }}
                h2 {{ font-size: 14px; color: #0284c7; text-transform: uppercase; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-top: 25px; }}
                table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
                th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
                th {{ background: #f1f5f9; text-transform: uppercase; font-size: 11px; }}
                .disclaimer {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 12px; border-radius: 6px; font-size: 11px; margin-top: 30px; font-weight: 500; }}
                @media print {{ body {{ margin: 15px; }} }}
            </style>
        </head>
        <body>
            <div class="header">
                <div>
                    <div style="font-size: 10px; text-transform: uppercase; font-weight: bold; color: #0284c7;">Government of India &bull; Smart India Hackathon 2026</div>
                    <h1>OILTRACE &bull; Incident Investigation Dossier</h1>
                    <div style="font-size: 12px; color: #64748b;">Ref: {data['report_id']}</div>
                </div>
                <div style="text-align: right; font-size: 11px; color: #64748b;">
                    <div>Generated: {data['generated_at'][:19]} UTC</div>
                    <div>Classification: OFFICIAL USE ONLY</div>
                </div>
            </div>

            <h2>1. Observation & Geometric Characterization</h2>
            <div class="meta-box">
                <div><span>Spill Event:</span><strong>#{spill['id']}</strong></div>
                <div><span>Detection Time:</span><strong>{spill['detected_at'][:19]}</strong></div>
                <div><span>Surface Area:</span><strong>{spill['area_km2']} km&sup2;</strong></div>
                <div><span>AI Confidence:</span><strong>{spill['confidence']}%</strong></div>
            </div>

            <h2>2. Oceanographic Drift Hindcasting</h2>
            <div class="meta-box">
                <div><span>Simulation:</span><strong>{drift['simulation_type']}</strong></div>
                <div><span>Hindcast Window:</span><strong>{drift['duration_hours']} Hours</strong></div>
                <div><span>Estimated Origin Time:</span><strong>{(drift['estimated_origin_time'] or 'T-12h')[:19]}</strong></div>
                <div><span>Model Confidence:</span><strong>{drift['model_confidence']}%</strong></div>
            </div>

            <h2>3. Ranked Candidate Vessels & Attribution Evidence</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Vessel Name</th>
                        <th>MMSI</th>
                        <th>Type</th>
                        <th>Priority</th>
                        <th>Score</th>
                        <th>Observed Evidence</th>
                    </tr>
                </thead>
                <tbody>
                    {candidates_rows}
                </tbody>
            </table>

            <h2>4. Scientific Limitations</h2>
            <ul style="font-size: 11px; color: #64748b;">
                {''.join(f"<li>{lim}</li>" for lim in data['scientific_limitations'])}
            </ul>

            <div class="disclaimer">
                <strong>LEGAL & SCIENTIFIC DISCLAIMER:</strong> {data['disclaimer']}
            </div>
        </body>
        </html>
        """
        return html
