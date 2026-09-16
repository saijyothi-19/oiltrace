import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Flame, 
  Compass, 
  Wind, 
  Ship, 
  FileText, 
  RotateCcw, 
  ArrowLeft,
  CheckCircle2,
  Clock,
  Sparkles,
  X
} from 'lucide-react';
import { SpillMap } from '../maps/SpillMap';
import { SpillInfoPanel } from '../components/SpillInfoPanel';
import { CandidateRankingPanel } from '../components/CandidateRankingPanel';
import { DetectionViewer } from '../components/DetectionViewer';
import { spillApi } from '../services/spillApi';
import { driftApi } from '../services/driftApi';
import { vesselApi } from '../services/aisApi';
import { attributionApi } from '../services/attributionApi';
import type { SpillStatus, VesselCandidate } from '../types';

export const SpillDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const spillId = Number(id);

  const [selectedVesselMmsi, setSelectedVesselMmsi] = useState<string | null>(null);
  const [showAiViewer, setShowAiViewer] = useState<boolean>(false);

  // Fetch Spill
  const { data: spill, isLoading: loadingSpill } = useQuery({
    queryKey: ['spill', spillId],
    queryFn: () => spillApi.getById(spillId),
    enabled: !!spillId,
  });

  // Fetch Drift
  const { data: driftSim } = useQuery({
    queryKey: ['drift', spillId],
    queryFn: () => driftApi.getById(spillId),
    enabled: !!spillId,
  });

  // Fetch Candidates
  const { data: candidates = [], isLoading: loadingCandidates } = useQuery({
    queryKey: ['candidates', spillId],
    queryFn: () => attributionApi.getCandidates(spillId),
    enabled: !!spillId,
  });

  // Fetch Vessels
  const { data: vessels = [] } = useQuery({
    queryKey: ['vessels'],
    queryFn: () => vesselApi.getAll(),
  });

  // Run Backward Hindcast Mutation
  const hindcastMutation = useMutation({
    mutationFn: () => driftApi.runBackward({ spill_event_id: spillId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drift', spillId] });
      queryClient.invalidateQueries({ queryKey: ['candidates', spillId] });
    },
  });

  // Run Attribution Mutation
  const attributionMutation = useMutation({
    mutationFn: () => attributionApi.analyze(spillId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates', spillId] });
    },
  });

  // Status Update Mutation
  const updateStatusMutation = useMutation({
    mutationFn: (status: SpillStatus) => spillApi.update(spillId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['spill', spillId] });
    },
  });

  if (loadingSpill) {
    return (
      <div className="h-full flex items-center justify-center font-mono text-xs text-slate-400">
        Loading spill investigation data #{spillId}...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full overflow-hidden select-none bg-navy-950">
      {/* Subheader Toolbar */}
      <div className="bg-navy-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/spills')}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Back to All Spills"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            <h2 className="font-mono font-bold text-sm text-white">
              INVESTIGATION CONSOLE: SPILL #{spillId}
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
              {spill?.status}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => hindcastMutation.mutate()}
            disabled={hindcastMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-orange-600/80 hover:bg-orange-500 text-white text-xs font-medium border border-orange-400/30 transition-colors disabled:opacity-50"
          >
            <Wind className={`w-3.5 h-3.5 ${hindcastMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{hindcastMutation.isPending ? 'Simulating...' : 'Run Backward Hindcast'}</span>
          </button>

          <button
            onClick={() => attributionMutation.mutate()}
            disabled={attributionMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-600/80 hover:bg-cyan-500 text-white text-xs font-medium border border-cyan-400/30 transition-colors disabled:opacity-50"
          >
            <Ship className={`w-3.5 h-3.5 ${attributionMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{attributionMutation.isPending ? 'Scoring...' : 'Run Vessel Attribution'}</span>
          </button>

          <button
            onClick={() => setShowAiViewer(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs font-medium border border-indigo-400/30 transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-200" />
            <span>AI SAR Analysis</span>
          </button>

          <button
            onClick={() => navigate(`/reports/${spillId}`)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            <span>Generate Report</span>
          </button>
        </div>
      </div>

      {/* AI SAR Detection Modal */}
      {showAiViewer && spill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-950">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2 font-mono">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                SAR DETECTION &amp; CHARACTERIZATION CONSOLE (SPILL #{spillId})
              </h3>
              <button
                onClick={() => setShowAiViewer(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto">
              <DetectionViewer spill={spill} />
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace: Split View */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map Centerpiece */}
        <div className="flex-1 relative h-full">
          <SpillMap
            selectedSpill={spill}
            driftSimulation={driftSim}
            vessels={vessels}
            candidates={candidates}
            selectedVesselMmsi={selectedVesselMmsi}
            onSelectVessel={(mmsi) => setSelectedVesselMmsi(mmsi)}
          />

          {/* Timeline Bar Overlay at bottom */}
          <div className="absolute bottom-4 left-4 z-10 bg-navy-900/90 border border-slate-800 p-2.5 rounded-lg shadow-xl backdrop-blur font-mono text-[11px] hidden lg:flex items-center gap-4 text-slate-300">
            <span className="text-slate-500 font-semibold uppercase text-[10px] flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-cyan-400" /> Investigation Timeline:
            </span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                Estimated Origin: <strong>{driftSim ? new Date(driftSim.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'T - 12h'}</strong>
              </span>
              <span className="text-slate-600">&rarr;</span>
              <span className="flex items-center gap-1 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                AIS Transits: <strong>Synchronized</strong>
              </span>
              <span className="text-slate-600">&rarr;</span>
              <span className="flex items-center gap-1 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                Detection: <strong>{spill ? new Date(spill.detected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'T0'}</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Right Details & Attribution Column */}
        <div className="w-96 flex flex-col h-full bg-navy-900 border-l border-slate-800 shrink-0 overflow-hidden">
          <div className="p-3 border-b border-slate-800">
            <SpillInfoPanel
              spill={spill || null}
              onStatusUpdate={(status) => updateStatusMutation.mutate(status)}
              onRunAttribution={() => attributionMutation.mutate()}
              onGenerateReport={() => navigate(`/reports/${spillId}`)}
              isUpdating={updateStatusMutation.isPending}
            />
          </div>

          <div className="flex-1 overflow-hidden">
            <CandidateRankingPanel
              candidates={candidates}
              selectedMmsi={selectedVesselMmsi}
              onSelectCandidate={(c) => setSelectedVesselMmsi(c.vessel?.mmsi || String(c.vessel_id))}
              isLoading={loadingCandidates || attributionMutation.isPending}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
