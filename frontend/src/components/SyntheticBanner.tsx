import React, { useState } from 'react';
import { ShieldCheck, Info, Layers, ExternalLink } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../services/attributionApi';
import { DataProvenanceModal } from './DataProvenanceModal';

interface SyntheticBannerProps {
  isSynthetic?: boolean;
}

export const SyntheticBanner: React.FC<SyntheticBannerProps> = () => {
  const [modalOpen, setModalOpen] = useState(false);

  const { data: provenance } = useQuery({
    queryKey: ['system-provenance'],
    queryFn: systemApi.getProvenance,
    refetchInterval: 30000,
  });

  const layers = provenance?.provenance_layers || {};
  const sat = layers.satellite || { is_demo: false, mode_badge: 'OPEN CDSE' };
  const env = layers.environment || { is_demo: false, mode_badge: 'LIVE OPERATIONAL' };
  const ais = layers.ais || { is_demo: true, mode_badge: 'DEMO DATA' };
  const ml = layers.ml_model || { is_demo: true, mode_badge: 'DEMO ENGINE' };

  return (
    <>
      <div className="bg-slate-900 border-b border-slate-800 px-4 py-1.5 flex flex-wrap items-center justify-between text-xs text-slate-300 select-none z-20">
        {/* Left: Provenance Layer Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-slate-400 mr-1">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>DATA PROVENANCE:</span>
          </div>

          {/* 1. Satellite Badge */}
          <div 
            onClick={() => setModalOpen(true)}
            title="Copernicus Data Space Ecosystem (Sentinel-1)"
            className={`cursor-pointer px-2 py-0.5 rounded text-[10px] font-bold font-mono transition-all flex items-center gap-1 border ${
              !sat.is_demo 
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25' 
                : 'bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25'
            }`}
          >
            <span>{!sat.is_demo ? '🟢' : '🟡'}</span>
            <span>SATELLITE: {!sat.is_demo ? (sat.mode_badge || 'REAL') : 'DEMO'}</span>
          </div>

          {/* 2. Environment Badge */}
          <div 
            onClick={() => setModalOpen(true)}
            title="Copernicus Marine / Open-Meteo live API"
            className={`cursor-pointer px-2 py-0.5 rounded text-[10px] font-bold font-mono transition-all flex items-center gap-1 border ${
              !env.is_demo 
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25' 
                : 'bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25'
            }`}
          >
            <span>{!env.is_demo ? '🟢' : '🟡'}</span>
            <span>MET/OCEAN: {!env.is_demo ? 'REAL DATA' : 'DEMO'}</span>
          </div>

          {/* 3. AIS Badge */}
          <div 
            onClick={() => setModalOpen(true)}
            title="NOAA MarineCadastre / Danish Maritime Ingested AIS"
            className={`cursor-pointer px-2 py-0.5 rounded text-[10px] font-bold font-mono transition-all flex items-center gap-1 border ${
              !ais.is_demo 
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25' 
                : 'bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25'
            }`}
          >
            <span>{!ais.is_demo ? '🟢' : '🟡'}</span>
            <span>AIS: {!ais.is_demo ? 'REAL' : 'DEMO'}</span>
          </div>

          {/* 4. ML Model Badge */}
          <div 
            onClick={() => setModalOpen(true)}
            title="PyTorch U-Net Model vs. Analytical Radiometric Contrast Fallback"
            className={`cursor-pointer px-2 py-0.5 rounded text-[10px] font-bold font-mono transition-all flex items-center gap-1 border ${
              !ml.is_demo 
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25' 
                : 'bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25'
            }`}
          >
            <span>{!ml.is_demo ? '🟢' : '🟡'}</span>
            <span>ML: {!ml.is_demo ? 'REAL UNET' : 'DEMO ENGINE'}</span>
          </div>
        </div>

        {/* Right: Integrity & Action */}
        <div className="flex items-center gap-3 mt-1 sm:mt-0">
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors underline underline-offset-2"
          >
            <Info className="w-3.5 h-3.5" />
            <span>Inspect Provenance</span>
          </button>
          <div className="hidden md:flex items-center gap-1 text-[11px] text-slate-400 font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>SIH26143 Decision Support Standard</span>
          </div>
        </div>
      </div>

      {/* Modal */}
      <DataProvenanceModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        provenanceData={provenance}
      />
    </>
  );
};

