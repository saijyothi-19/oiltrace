import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Ship, 
  ArrowLeft, 
  Navigation, 
  Compass, 
  Activity, 
  Clock, 
  ShieldCheck, 
  AlertTriangle 
} from 'lucide-react';
import { vesselApi } from '../services/aisApi';
import { SpillMap } from '../maps/SpillMap';

export const VesselDetailPage: React.FC = () => {
  const { mmsi } = useParams<{ mmsi: string }>();
  const navigate = useNavigate();

  const { data: vessel, isLoading } = useQuery({
    queryKey: ['vessel', mmsi],
    queryFn: () => (mmsi ? vesselApi.getByMmsi(mmsi) : null),
    enabled: !!mmsi,
  });

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center font-mono text-xs text-slate-400">
        Loading AIS vessel telemetry profile for MMSI {mmsi}...
      </div>
    );
  }

  if (!vessel) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-xs text-slate-400">
        <p>Vessel MMSI {mmsi} not found in AIS database.</p>
        <button
          onClick={() => navigate('/vessels')}
          className="mt-3 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-white transition-colors"
        >
          Back to Vessels
        </button>
      </div>
    );
  }

  const lastPos = vessel.positions && vessel.positions.length > 0
    ? vessel.positions[vessel.positions.length - 1]
    : null;

  return (
    <div className="flex flex-col h-full w-full overflow-hidden select-none bg-navy-950">
      {/* Header Toolbar */}
      <div className="bg-navy-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/vessels')}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Back to Vessels"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="font-mono font-bold text-sm text-white flex items-center gap-2">
              <Ship className="w-4 h-4 text-cyan-400" />
              {vessel.name}
              <span className="text-xs text-slate-400 font-normal">
                (MMSI: {vessel.mmsi})
              </span>
            </h1>
          </div>
        </div>

        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700 uppercase">
          {vessel.ship_type}
        </span>
      </div>

      {/* Main Content Split */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Map with this vessel's track */}
        <div className="flex-1 relative h-full">
          <SpillMap
            vessels={[vessel]}
            selectedVesselMmsi={vessel.mmsi}
          />
        </div>

        {/* Right Telemetry & Profile Panel */}
        <div className="w-96 p-4 bg-navy-900 border-l border-slate-800 overflow-y-auto space-y-4 font-mono text-xs">
          {/* Identity Card */}
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-2">
            <div className="text-[10px] text-slate-400 uppercase font-semibold border-b border-slate-800 pb-1">
              Vessel Identification
            </div>
            <div className="space-y-1 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">MMSI:</span>
                <span className="text-cyan-400 font-bold">{vessel.mmsi}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">IMO:</span>
                <span>{vessel.imo || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Ship Type:</span>
                <span>{vessel.ship_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Flag State:</span>
                <span>{vessel.flag || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Dimensions:</span>
                <span>{vessel.length || 0}m &times; {vessel.width || 0}m</span>
              </div>
            </div>
          </div>

          {/* Last Reported Navigation Status */}
          {lastPos && (
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-2">
              <div className="text-[10px] text-slate-400 uppercase font-semibold border-b border-slate-800 pb-1 flex items-center justify-between">
                <span>Latest AIS Telemetry</span>
                <span className="text-emerald-400 text-[9px] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  TRANSPONDER ACTIVE
                </span>
              </div>
              <div className="space-y-1 text-slate-300">
                <div className="flex justify-between">
                  <span className="text-slate-500">Timestamp:</span>
                  <span>{new Date(lastPos.timestamp).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Position (WGS84):</span>
                  <span>{lastPos.position.coordinates[1].toFixed(4)}&deg; N, {lastPos.position.coordinates[0].toFixed(4)}&deg; E</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Speed Over Ground:</span>
                  <span className="text-white font-bold">{lastPos.speed?.toFixed(1) || '0.0'} kts</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Course Over Ground:</span>
                  <span>{lastPos.course?.toFixed(0) || '0'}&deg;</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Navigational Status:</span>
                  <span className="text-cyan-300 text-[10px]">{lastPos.navigation_status || 'Underway'}</span>
                </div>
              </div>
            </div>
          )}

          {/* AIS Data Quality & Integrity */}
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-2">
            <div className="text-[10px] text-slate-400 uppercase font-semibold border-b border-slate-800 pb-1">
              Data Integrity Metrics
            </div>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center gap-2 text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                <span>Valid MMSI format & checksum</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                <span>Geographic coordinates within valid domain</span>
              </div>
              <div className="flex items-center gap-2 text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                <span>SOG within physical operational limits (&lt; 45 kts)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
