import React from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  MapPin, 
  Compass, 
  Activity, 
  ExternalLink,
  Info
} from 'lucide-react';
import type { VesselCandidate, PriorityLevel } from '../types';

interface CandidateRankingPanelProps {
  candidates: VesselCandidate[];
  selectedMmsi: string | null;
  onSelectCandidate: (candidate: VesselCandidate) => void;
  isLoading?: boolean;
}

export const CandidateRankingPanel: React.FC<CandidateRankingPanelProps> = ({
  candidates,
  selectedMmsi,
  onSelectCandidate,
  isLoading = false,
}) => {
  const getPriorityBadge = (priority: PriorityLevel) => {
    switch (priority) {
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse">
            HIGH PRIORITY
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
            MEDIUM PRIORITY
          </span>
        );
      case 'LOW':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/40">
            LOW PRIORITY
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full bg-navy-900/90 border-l border-slate-800 backdrop-blur select-none">
      {/* Panel Header */}
      <div className="p-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs font-bold font-mono tracking-tight text-white uppercase">
              Candidate Vessel Attribution
            </h2>
          </div>
          <p className="text-[10px] text-slate-400">
            Ranked correlation with estimated spill origin
          </p>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
          {candidates.length} Analyzed
        </span>
      </div>

      {/* Candidates List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-400 text-xs">
            <Activity className="w-6 h-6 animate-spin text-cyan-400 mb-2" />
            <span>Computing trajectory correlation...</span>
          </div>
        ) : candidates.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-500 text-xs text-center px-4">
            <Info className="w-6 h-6 mb-2 text-slate-600" />
            <span>No candidate vessels found in spatial-temporal origin window.</span>
          </div>
        ) : (
          candidates.map((candidate, idx) => {
            const isSelected = selectedMmsi === (candidate.vessel?.mmsi || String(candidate.vessel_id));
            const vesselName = candidate.vessel?.name || `MMSI: ${candidate.vessel_id}`;
            const mmsi = candidate.vessel?.mmsi || String(candidate.vessel_id);
            const explanation = candidate.explanation_json;

            return (
              <div
                key={candidate.id}
                onClick={() => onSelectCandidate(candidate)}
                className={`p-3 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/95 border-cyan-500/80 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/40'
                    : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/60 hover:border-slate-700'
                }`}
              >
                {/* Header: Rank + Name + Score + Priority */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded flex items-center justify-center font-mono text-[11px] font-bold bg-slate-800 text-cyan-400 border border-slate-700">
                      #{idx + 1}
                    </span>
                    <div>
                      <div className="font-semibold text-xs text-white leading-tight">
                        {vesselName}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        MMSI {mmsi} &bull; {candidate.vessel?.ship_type || 'Vessel'}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="font-mono text-sm font-extrabold text-cyan-300">
                      {candidate.overall_score.toFixed(1)}
                    </div>
                    {getPriorityBadge(candidate.priority)}
                  </div>
                </div>

                {/* Score component breakdown bars */}
                <div className="grid grid-cols-5 gap-1.5 pt-2 pb-1 border-t border-slate-800/80 text-[9px] font-mono text-slate-400">
                  <div title="Spatial proximity score (35%)">
                    <div>SPT {candidate.spatial_score.toFixed(0)}%</div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
                      <div className="h-full bg-cyan-400" style={{ width: `${candidate.spatial_score}%` }}></div>
                    </div>
                  </div>
                  <div title="Temporal synchronization score (30%)">
                    <div>TMP {candidate.temporal_score.toFixed(0)}%</div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
                      <div className="h-full bg-emerald-400" style={{ width: `${candidate.temporal_score}%` }}></div>
                    </div>
                  </div>
                  <div title="Trajectory heading alignment score (20%)">
                    <div>TRJ {candidate.trajectory_score.toFixed(0)}%</div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
                      <div className="h-full bg-blue-400" style={{ width: `${candidate.trajectory_score}%` }}></div>
                    </div>
                  </div>
                  <div title="Behavioral anomaly score (10%)">
                    <div>BHV {candidate.behaviour_score.toFixed(0)}%</div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
                      <div className="h-full bg-amber-400" style={{ width: `${candidate.behaviour_score}%` }}></div>
                    </div>
                  </div>
                  <div title="AIS data quality & gap score (5%)">
                    <div>AIS {candidate.data_quality_score.toFixed(0)}%</div>
                    <div className="h-1 bg-slate-800 rounded-full overflow-hidden mt-0.5">
                      <div className="h-full bg-purple-400" style={{ width: `${candidate.data_quality_score}%` }}></div>
                    </div>
                  </div>
                </div>

                {/* Expanded Details when selected */}
                {isSelected && explanation && (
                  <div className="mt-3 pt-2.5 border-t border-slate-800 text-xs space-y-2 animate-fadeIn">
                    <div className="text-[10px] font-mono font-semibold text-cyan-400 uppercase tracking-wider">
                      Observed Evidence Checklist:
                    </div>
                    <div className="space-y-1 text-[11px]">
                      {explanation.explanation_points?.map((pt, i) => (
                        <div key={i} className="flex items-start gap-1.5 text-slate-300">
                          <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                          <span>{pt}</span>
                        </div>
                      ))}
                      {explanation.ais_gap_detected && (
                        <div className="flex items-start gap-1.5 text-amber-300">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                          <span>AIS transponder gap / blackout detected near origin region.</span>
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-2 text-[10px] font-mono text-slate-400 bg-slate-900/80 p-2 rounded border border-slate-800">
                      <div>
                        Distance to Origin: <strong className="text-white">{explanation.spatial_distance_km?.toFixed(1) || '0.0'} km</strong>
                      </div>
                      <div>
                        Time Offset: <strong className="text-white">{explanation.temporal_delta_hours?.toFixed(1) || '0.0'} hrs</strong>
                      </div>
                      <div>
                        Heading Alignment: <strong className="text-white">{explanation.trajectory_heading_match_deg?.toFixed(0) || '0'}&deg;</strong>
                      </div>
                      <div>
                        Operating Speed: <strong className="text-white">{explanation.speed_knots?.toFixed(1) || '0.0'} kts</strong>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Scientific disclaimer footer */}
      <div className="p-2.5 bg-slate-950/80 border-t border-slate-800 text-[10px] text-slate-500 leading-tight">
        <strong>Decision Support Only:</strong> Evidence scores reflect mathematical correlation and do not constitute proof of liability.
      </div>
    </div>
  );
};
