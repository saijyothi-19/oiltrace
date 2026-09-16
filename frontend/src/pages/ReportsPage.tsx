import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileText, ArrowUpRight, Flame, Calendar, CheckCircle2 } from 'lucide-react';
import { spillApi } from '../services/spillApi';

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();

  const { data: spills = [], isLoading } = useQuery({
    queryKey: ['spills'],
    queryFn: () => spillApi.getAll(),
  });

  return (
    <div className="h-full flex flex-col p-6 overflow-y-auto select-none bg-navy-950">
      <div className="mb-6">
        <h1 className="text-xl font-mono font-bold text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-cyan-400" />
          INCIDENT INVESTIGATION REPORTS ARCHIVE
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Exportable and printable maritime decision-support dossiers with full audit trails
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-xs text-slate-400 font-mono">
          Loading report catalog...
        </div>
      ) : spills.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center p-8 bg-navy-900/60 rounded-xl border border-slate-800">
          <FileText className="w-12 h-12 text-slate-600 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Reports Available</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            Load demo data or run satellite detection to generate investigative reports.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {spills.map((spill) => (
            <div
              key={spill.id}
              onClick={() => navigate(`/reports/${spill.id}`)}
              className="bg-navy-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-cyan-500/50 rounded-xl p-4 transition-all cursor-pointer shadow-lg group font-mono"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="text-sm font-bold text-white flex items-center gap-2">
                  <Flame className="w-4 h-4 text-red-500" />
                  <span>Dossier #{spill.id.toString().padStart(5, '0')}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                  {spill.status}
                </span>
              </div>

              <p className="text-xs text-slate-400 mb-3">
                Spill Event #{spill.id} &bull; Area {spill.area_km2.toFixed(2)} km&sup2; &bull; Confidence {(spill.confidence * 100).toFixed(0)}%
              </p>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-3 border-t border-slate-800">
                <div className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(spill.detected_at).toLocaleDateString()}</span>
                </div>
                <span className="text-cyan-400 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                  View Dossier <ArrowUpRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
