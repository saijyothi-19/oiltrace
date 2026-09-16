import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  FileText, 
  Printer, 
  ArrowLeft, 
  ShieldAlert, 
  Calendar, 
  Maximize, 
  Satellite, 
  Wind, 
  Ship, 
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { reportApi } from '../services/attributionApi';
import { spillApi } from '../services/spillApi';
import { driftApi } from '../services/driftApi';
import { attributionApi } from '../services/attributionApi';

export const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const spillId = Number(id);

  const { data: spill, isLoading: loadingSpill } = useQuery({
    queryKey: ['spill', spillId],
    queryFn: () => spillApi.getById(spillId),
    enabled: !!spillId,
  });

  const { data: driftSim } = useQuery({
    queryKey: ['drift', spillId],
    queryFn: () => driftApi.getById(spillId),
    enabled: !!spillId,
  });

  const { data: candidates = [] } = useQuery({
    queryKey: ['candidates', spillId],
    queryFn: () => attributionApi.getCandidates(spillId),
    enabled: !!spillId,
  });

  const handlePrint = () => {
    window.print();
  };

  if (loadingSpill) {
    return (
      <div className="h-full flex items-center justify-center font-mono text-xs text-slate-400">
        Generating incident investigation report...
      </div>
    );
  }

  if (!spill) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-xs text-slate-400">
        <p>Spill incident record #{spillId} not found.</p>
        <button
          onClick={() => navigate('/spills')}
          className="mt-3 px-3 py-1.5 rounded bg-slate-800 text-white"
        >
          Back to Spills
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-navy-950 overflow-y-auto p-6 select-text">
      {/* Toolbar (Hidden when printing) */}
      <div className="max-w-4xl mx-auto w-full mb-6 flex items-center justify-between print:hidden">
        <button
          onClick={() => navigate(`/spills/${spillId}`)}
          className="flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Investigation Console</span>
        </button>

        <button
          onClick={handlePrint}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold font-mono shadow-lg shadow-cyan-500/20 transition-all border border-cyan-400/30"
        >
          <Printer className="w-4 h-4" />
          <span>Print / Export PDF</span>
        </button>
      </div>

      {/* Official Report Container */}
      <div className="max-w-4xl mx-auto w-full bg-slate-900 border border-slate-700 rounded-xl p-8 shadow-2xl space-y-6 font-mono text-xs text-slate-300 print:bg-white print:text-black print:border-none print:p-0">
        {/* Report Header */}
        <div className="border-b border-slate-700 pb-4 flex items-start justify-between">
          <div>
            <div className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest print:text-blue-700">
              Government of India &bull; Maritime Decision Support Dossier
            </div>
            <h1 className="text-xl font-bold text-white mt-1 print:text-black">
              MARINE OIL SPILL INVESTIGATION REPORT
            </h1>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Case Ref: OILTRACE-INCIDENT-{spill.id.toString().padStart(6, '0')}
            </div>
          </div>
          <div className="text-right text-[11px] text-slate-400">
            <div>Generated: {new Date().toISOString()}</div>
            <div>Classification: OFFICIAL / FOR INVESTIGATIVE USE ONLY</div>
          </div>
        </div>

        {/* Section 1: Incident Summary */}
        <div className="space-y-2">
          <h2 className="text-xs font-bold text-cyan-300 uppercase tracking-wider border-b border-slate-800 pb-1">
            1. Detection & Satellite Observation Metadata
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-950/60 p-3 rounded border border-slate-800 text-[11px]">
            <div>
              <span className="text-slate-500 block">Spill Event ID:</span>
              <strong className="text-white">#{spill.id}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Detection Time:</span>
              <strong className="text-white">{new Date(spill.detected_at).toUTCString()}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Satellite Source:</span>
              <strong className="text-white">{spill.satellite_image?.satellite || 'Sentinel-1A C-SAR'}</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Polarization:</span>
              <strong className="text-white">{spill.satellite_image?.polarization || 'VV (Co-Polarized)'}</strong>
            </div>
          </div>
        </div>

        {/* Section 2: Spill Characterization */}
        <div className="space-y-2">
          <h2 className="text-xs font-bold text-cyan-300 uppercase tracking-wider border-b border-slate-800 pb-1">
            2. Spill Geometric Characterization & AI Confidence
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-950/60 p-3 rounded border border-slate-800 text-[11px]">
            <div>
              <span className="text-slate-500 block">Calculated Area:</span>
              <strong className="text-white">{spill.area_km2.toFixed(2)} km&sup2;</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Calculated Perimeter:</span>
              <strong className="text-white">{spill.perimeter_km.toFixed(2)} km</strong>
            </div>
            <div>
              <span className="text-slate-500 block">AI Model Confidence:</span>
              <strong className="text-cyan-400 font-bold">{(spill.confidence * 100).toFixed(1)}%</strong>
            </div>
            <div>
              <span className="text-slate-500 block">Segmentation Architecture:</span>
              <strong className="text-white">{spill.model_version}</strong>
            </div>
          </div>
        </div>

        {/* Section 3: Drift Reconstruction & Estimated Origin */}
        <div className="space-y-2">
          <h2 className="text-xs font-bold text-cyan-300 uppercase tracking-wider border-b border-slate-800 pb-1">
            3. Oceanographic Drift Reconstruction & Estimated Origin Window
          </h2>
          <div className="bg-slate-950/60 p-3 rounded border border-slate-800 space-y-2 text-[11px]">
            <p>
              Lagrangian backward trajectory hindcasting was conducted over a duration of{' '}
              <strong>{driftSim?.duration_hours || 12} hours</strong> using environmental forcing from{' '}
              <strong>ERA5 surface winds</strong> (windage coefficient 3.0%, 10&deg; Coriolis deflection) and{' '}
              <strong>Copernicus Marine surface currents</strong>.
            </p>
            <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800 text-[10px]">
              <div>
                Estimated Release Time: <strong className="text-white">{driftSim?.start_time ? new Date(driftSim.start_time).toUTCString() : 'T - 12h'}</strong>
              </div>
              <div>
                Particle Ensemble: <strong className="text-white">{driftSim?.particle_count || 150} stochastic drifters</strong>
              </div>
              <div>
                Hindcast Model Confidence: <strong className="text-white">{((driftSim?.confidence || 0.85) * 100).toFixed(0)}%</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Ranked Candidate Vessels & Evidence */}
        <div className="space-y-2">
          <h2 className="text-xs font-bold text-cyan-300 uppercase tracking-wider border-b border-slate-800 pb-1">
            4. Ranked Candidate Vessels & Explainable Attribution Evidence
          </h2>
          <p className="text-[11px] text-slate-400">
            The candidate attribution engine analyzed spatial proximity, release time synchronization, trajectory heading alignment, speed anomalies, and AIS transponder continuity:
          </p>

          <table className="w-full text-left text-[11px] border border-slate-800 rounded">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[9px]">
              <tr>
                <th className="p-2">Rank</th>
                <th className="p-2">Vessel Name</th>
                <th className="p-2">MMSI</th>
                <th className="p-2">Type</th>
                <th className="p-2">Priority</th>
                <th className="p-2">Overall Score</th>
                <th className="p-2">Observed Evidence Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {candidates.map((c, i) => (
                <tr key={c.id} className="text-slate-200">
                  <td className="p-2 font-bold text-cyan-400">#{i + 1}</td>
                  <td className="p-2 font-semibold text-white">{c.vessel?.name || `MMSI: ${c.vessel_id}`}</td>
                  <td className="p-2 text-cyan-300">{c.vessel?.mmsi || c.vessel_id}</td>
                  <td className="p-2 text-slate-400">{c.vessel?.ship_type || 'Tanker'}</td>
                  <td className="p-2">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      c.priority === 'HIGH' ? 'text-red-400 bg-red-500/20' :
                      c.priority === 'MEDIUM' ? 'text-amber-400 bg-amber-500/20' :
                      'text-blue-400 bg-blue-500/20'
                    }`}>
                      {c.priority}
                    </span>
                  </td>
                  <td className="p-2 font-bold font-mono text-cyan-300">{c.overall_score.toFixed(1)}/100</td>
                  <td className="p-2 text-[10px] text-slate-300 max-w-xs">
                    {c.explanation_json.explanation_points?.join('; ') || 'Candidate transit identified.'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Section 5: Scientific Limitations & Methodological Assumptions */}
        <div className="space-y-1.5 text-[10px] text-slate-400 border-t border-slate-800 pt-3">
          <div className="font-bold text-slate-300 uppercase">5. Scientific Limitations & Assumptions</div>
          <ul className="list-disc pl-4 space-y-0.5">
            <li>SAR imagery detects surface roughness modulation. Low-wind zones (&lt; 2 m/s), biogenic slicks, and internal waves can present look-alike dark regions.</li>
            <li>Lagrangian particle drift assumes representative windage factors (3.0%) and does not fully resolve sub-mesoscale ocean turbulence.</li>
            <li>AIS transmissions may suffer from satellite coverage gaps, RF collisions, or intentional non-reporting. Missing AIS does not imply criminal intent.</li>
          </ul>
        </div>

        {/* Section 6: Mandatory Statutory Disclaimer */}
        <div className="p-3 rounded bg-amber-950/40 border border-amber-500/40 text-amber-200 text-[10px] leading-relaxed">
          <strong>LEGAL DISCLAIMER:</strong> This report provides analytical decision support based on available satellite, environmental and AIS data. Candidate rankings do not establish legal responsibility or causation.
        </div>
      </div>
    </div>
  );
};
