import React from 'react';
import { 
  Flame, 
  Satellite, 
  Ruler, 
  Maximize, 
  Calendar, 
  Check, 
  X, 
  RotateCcw, 
  FileText,
  AlertCircle
} from 'lucide-react';
import type { SpillEvent, SpillStatus } from '../types';

interface SpillInfoPanelProps {
  spill: SpillEvent | null;
  onStatusUpdate?: (status: SpillStatus) => void;
  onRunAttribution?: () => void;
  onGenerateReport?: () => void;
  isUpdating?: boolean;
}

export const SpillInfoPanel: React.FC<SpillInfoPanelProps> = ({
  spill,
  onStatusUpdate,
  onRunAttribution,
  onGenerateReport,
  isUpdating = false,
}) => {
  if (!spill) {
    return (
      <div className="p-4 bg-navy-900/90 border border-slate-800 rounded-lg text-xs text-slate-400 text-center select-none">
        <Flame className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p>No oil spill event selected.</p>
        <p className="text-[11px] text-slate-500 mt-1">Select a spill event or click "Load Demo Investigation".</p>
      </div>
    );
  }

  const getStatusColor = (status: SpillStatus) => {
    switch (status) {
      case 'DETECTED':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'ACCEPTED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'REJECTED':
        return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'REVIEW REQUIRED':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="bg-navy-900/95 border border-slate-800 rounded-lg p-4 shadow-xl backdrop-blur select-none space-y-4">
      {/* Spill Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
            <h3 className="font-mono font-bold text-sm text-white">
              SPILL EVENT #{spill.id}
            </h3>
          </div>
          <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getStatusColor(spill.status)}`}>
            {spill.status}
          </span>
        </div>

        <div className="text-right">
          <div className="text-[10px] text-slate-400 uppercase font-mono">Confidence</div>
          <div className="text-base font-extrabold font-mono text-cyan-400">
            {(spill.confidence * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Maximize className="w-3 h-3 text-cyan-400" />
            Spill Area
          </div>
          <div className="text-sm font-bold text-white mt-0.5">
            {spill.area_km2.toFixed(2)} <span className="text-xs font-normal text-slate-400">km&sup2;</span>
          </div>
        </div>

        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Ruler className="w-3 h-3 text-cyan-400" />
            Perimeter
          </div>
          <div className="text-sm font-bold text-white mt-0.5">
            {spill.perimeter_km.toFixed(2)} <span className="text-xs font-normal text-slate-400">km</span>
          </div>
        </div>

        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Satellite className="w-3 h-3 text-cyan-400" />
            Sensor / Satellite
          </div>
          <div className="text-xs font-semibold text-slate-200 mt-0.5 truncate">
            {spill.satellite_image?.satellite || 'Sentinel-1A SAR'}
          </div>
        </div>

        <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-cyan-400" />
            Detection Time
          </div>
          <div className="text-[11px] font-semibold text-slate-200 mt-0.5">
            {new Date(spill.detected_at).toLocaleDateString()} {new Date(spill.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>

      {/* Human-In-The-Loop Actions (Section 25) */}
      <div className="pt-3 border-t border-slate-800">
        <div className="text-[10px] font-mono uppercase text-slate-400 mb-2 font-semibold flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-cyan-400" />
          Analyst Review Action
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onStatusUpdate && onStatusUpdate('ACCEPTED')}
            disabled={isUpdating || spill.status === 'ACCEPTED'}
            className="flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-emerald-600/80 hover:bg-emerald-500 text-white text-xs font-semibold shadow transition-all border border-emerald-400/30 disabled:opacity-40"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Accept Detection</span>
          </button>

          <button
            onClick={() => onStatusUpdate && onStatusUpdate('REJECTED')}
            disabled={isUpdating || spill.status === 'REJECTED'}
            className="flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-red-600/80 hover:bg-red-500 text-white text-xs font-semibold shadow transition-all border border-red-400/30 disabled:opacity-40"
          >
            <X className="w-3.5 h-3.5" />
            <span>Reject Detection</span>
          </button>
        </div>
      </div>

      {/* Investigation Controls */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {onRunAttribution && (
          <button
            onClick={onRunAttribution}
            className="py-1.5 px-3 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition-colors border border-cyan-400/30 text-center"
          >
            Run Attribution
          </button>
        )}
        {onGenerateReport && (
          <button
            onClick={onGenerateReport}
            className="flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors border border-slate-700"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Report</span>
          </button>
        )}
      </div>
    </div>
  );
};
