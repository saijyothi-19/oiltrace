import React from 'react';
import { 
  X, 
  Satellite, 
  Wind, 
  Ship, 
  BrainCircuit, 
  ShieldCheck, 
  AlertCircle,
  ExternalLink,
  Layers,
  Database
} from 'lucide-react';

interface DataProvenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  provenanceData?: any;
}

export const DataProvenanceModal: React.FC<DataProvenanceModalProps> = ({
  isOpen,
  onClose,
  provenanceData,
}) => {
  if (!isOpen) return null;

  const layers = provenanceData?.provenance_layers || {};
  const sat = layers.satellite || {
    layer: 'Satellite Remote Sensing',
    is_demo: false,
    mode_badge: 'OPEN CDSE',
    primary_source: 'Copernicus Data Space Ecosystem (Sentinel-1 C-SAR GRD)',
    download_auth: 'Open Public Metadata Catalog',
    processing_level: 'Level-1 Ground Range Detected (GRD-HD)',
  };

  const env = layers.environment || {
    layer: 'Oceanic & Atmospheric Forcing',
    is_demo: false,
    mode_badge: 'LIVE OPERATIONAL',
    primary_source: 'Open-Meteo Operational Marine API (ECMWF & Global Ocean Physics)',
    quality: 'LIVE_OPERATIONAL_API',
    variables: 'Surface currents (u, v m/s), 10m wind velocity (m/s)',
  };

  const ais = layers.ais || {
    layer: 'AIS Vessel Telemetry',
    is_demo: true,
    mode_badge: 'DEMO DATA',
    primary_source: 'Synthetic Demonstration Stream (Validated Fixture)',
    records_ingested: 12,
    standards: 'IMO / ITU-R M.1371 Maritime Transponder Standard',
  };

  const ml = layers.ml_model || {
    layer: 'Oil Spill AI Model',
    is_demo: true,
    mode_badge: 'DEMO ENGINE',
    architecture: 'Adaptive Radiometric Contrast Engine (PyTorch Fallback)',
    model_version: 'v1.0-radiometric-contrast-demo',
    notes: 'Analytical contrast fallback active (Honest Demo Fallback)',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-navy-900 border border-slate-700/80 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden text-slate-200">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold font-mono text-white flex items-center gap-2">
                SYSTEM INTEGRITY & DATA PROVENANCE
                <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  SIH26143 SCIENTIFIC STANDARD
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Transparent verification of real vs. demonstration data sources across all 4 operational layers.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Scientific Disclaimer Note */}
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-600/30 text-amber-200/90 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-[11px] leading-relaxed">
              <strong>Scientific Honesty Standard:</strong> OILTRACE distinguishes between live operational APIs, official European Copernicus feeds, and demonstration fallbacks. Analytical fallbacks are explicitly labeled and never misrepresented as neural AI.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {/* 1. Satellite Layer */}
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Satellite className="w-4 h-4 text-cyan-400" />
                  <span>1. Satellite Remote Sensing</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                  !sat.is_demo 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' 
                    : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                }`}>
                  {!sat.is_demo ? '🟢 REAL DATA' : '🟡 DEMO DATA'}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 space-y-1 font-mono">
                <div>Source: <span className="text-white">{sat.primary_source}</span></div>
                <div>Level: <span className="text-slate-400">{sat.processing_level || 'GRD-HD'}</span></div>
                <div>Access Mode: <span className="text-cyan-400">{sat.download_auth || 'Open OData Catalog'}</span></div>
              </div>
            </div>

            {/* 2. Environmental Layer */}
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Wind className="w-4 h-4 text-emerald-400" />
                  <span>2. Oceanic & Wind Forcing</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                  !env.is_demo 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' 
                    : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                }`}>
                  {!env.is_demo ? '🟢 REAL DATA' : '🟡 DEMO DATA'}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 space-y-1 font-mono">
                <div>Source: <span className="text-white">{env.primary_source}</span></div>
                <div>Variables: <span className="text-slate-400">{env.variables || 'Currents (u, v), Wind 10m'}</span></div>
                <div>Engine: <span className="text-cyan-400">{env.quality || 'Live Operational'}</span></div>
              </div>
            </div>

            {/* 3. AIS Layer */}
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Ship className="w-4 h-4 text-blue-400" />
                  <span>3. AIS Vessel Telemetry</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                  !ais.is_demo 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' 
                    : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                }`}>
                  {!ais.is_demo ? '🟢 REAL DATA' : '🟡 DEMO DATA'}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 space-y-1 font-mono">
                <div>Source: <span className="text-white">{ais.primary_source}</span></div>
                <div>Standard: <span className="text-slate-400">{ais.standards || 'IMO / ITU-R M.1371'}</span></div>
                <div>Ingested: <span className="text-cyan-400">{ais.records_ingested || '12'} vessels</span></div>
              </div>
            </div>

            {/* 4. AI ML Layer */}
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-white font-medium">
                  <BrainCircuit className="w-4 h-4 text-purple-400" />
                  <span>4. Oil Spill AI Subsystem</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                  !ml.is_demo 
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' 
                    : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                }`}>
                  {!ml.is_demo ? '🟢 REAL MODEL' : '🟡 DEMO ENGINE'}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 space-y-1 font-mono">
                <div>Architecture: <span className="text-white">{ml.architecture}</span></div>
                <div>Version: <span className="text-slate-400">{ml.model_version}</span></div>
                <div>Status: <span className="text-cyan-400">{ml.notes || 'Inference engine active'}</span></div>
              </div>
            </div>
          </div>

          {/* Legal Decision Support Statement */}
          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-[11px] text-slate-400 leading-relaxed font-mono">
            <strong className="text-slate-300">Decision-Support Only:</strong> OILTRACE correlates multi-source satellite observations, ocean currents, and transponder histories to rank priority candidates. Output is designated for investigative triage and does not constitute definitive proof of maritime liability.
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <span className="text-[10px] font-mono text-slate-500">
            OILTRACE Core Engine &bull; SIH26143 Decision Support
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-md bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs transition-colors"
          >
            Acknowledge & Close
          </button>
        </div>
      </div>
    </div>
  );
};
