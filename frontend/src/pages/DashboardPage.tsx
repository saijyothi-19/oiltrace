import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useOutletContext, useNavigate } from 'react-router-dom';
import { SpillMap } from '../maps/SpillMap';
import { SpillInfoPanel } from '../components/SpillInfoPanel';
import { CandidateRankingPanel } from '../components/CandidateRankingPanel';
import { spillApi } from '../services/spillApi';
import { driftApi } from '../services/driftApi';
import { vesselApi } from '../services/aisApi';
import { attributionApi } from '../services/attributionApi';
import type { SpillStatus, VesselCandidate } from '../types';

interface ContextType {
  selectedSpillId: number | null;
  setSelectedSpillId: (id: number | null) => void;
}

export const DashboardPage: React.FC = () => {
  const { selectedSpillId, setSelectedSpillId } = useOutletContext<ContextType>();
  const [selectedVesselMmsi, setSelectedVesselMmsi] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 1. Fetch All Spills
  const { data: spills = [] } = useQuery({
    queryKey: ['spills'],
    queryFn: () => spillApi.getAll(),
  });

  // Auto select first spill if none selected
  const activeSpillId = selectedSpillId || (spills.length > 0 ? spills[0].id : null);

  // 2. Fetch Selected Spill Details
  const { data: activeSpill } = useQuery({
    queryKey: ['spill', activeSpillId],
    queryFn: () => (activeSpillId ? spillApi.getById(activeSpillId) : null),
    enabled: !!activeSpillId,
  });

  // 3. Fetch Drift Simulation for this spill
  const { data: driftSim } = useQuery({
    queryKey: ['drift', activeSpillId],
    queryFn: () => (activeSpillId ? driftApi.getById(activeSpillId) : null),
    enabled: !!activeSpillId,
  });

  // 4. Fetch Candidates for this spill
  const { data: candidates = [], isLoading: loadingCandidates } = useQuery({
    queryKey: ['candidates', activeSpillId],
    queryFn: () => (activeSpillId ? attributionApi.getCandidates(activeSpillId) : []),
    enabled: !!activeSpillId,
  });

  // 5. Fetch Vessels
  const { data: vessels = [] } = useQuery({
    queryKey: ['vessels'],
    queryFn: () => vesselApi.getAll(),
  });

  // Human in the loop status update mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: SpillStatus }) =>
      spillApi.update(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['spills'] });
      queryClient.invalidateQueries({ queryKey: ['spill', activeSpillId] });
    },
  });

  // Run Attribution Mutation
  const attributionMutation = useMutation({
    mutationFn: (spillId: number) => attributionApi.analyze(spillId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['candidates', activeSpillId] });
    },
  });

  const handleSelectCandidate = (candidate: VesselCandidate) => {
    const mmsi = candidate.vessel?.mmsi || String(candidate.vessel_id);
    setSelectedVesselMmsi(mmsi);
  };

  return (
    <div className="flex h-full w-full overflow-hidden relative">
      {/* Center: Large Interactive MapLibre Centerpiece */}
      <div className="flex-1 relative h-full">
        <SpillMap
          selectedSpill={activeSpill}
          driftSimulation={driftSim}
          vessels={vessels}
          candidates={candidates}
          selectedVesselMmsi={selectedVesselMmsi}
          onSelectVessel={(mmsi) => setSelectedVesselMmsi(mmsi)}
          onSelectSpill={(id) => setSelectedSpillId(id)}
        />
      </div>

      {/* Right Column: Spill Details & Candidate Ranking Panel */}
      <div className="w-96 flex flex-col h-full bg-navy-900 border-l border-slate-800 shrink-0 overflow-hidden">
        {/* Top Section: Spill Information & Analyst Validation */}
        <div className="p-3 border-b border-slate-800">
          <SpillInfoPanel
            spill={activeSpill || null}
            onStatusUpdate={(status) => {
              if (activeSpillId) {
                updateStatusMutation.mutate({ id: activeSpillId, status });
              }
            }}
            onRunAttribution={() => {
              if (activeSpillId) {
                attributionMutation.mutate(activeSpillId);
              }
            }}
            onGenerateReport={() => {
              if (activeSpillId) {
                navigate(`/reports/${activeSpillId}`);
              }
            }}
            isUpdating={updateStatusMutation.isPending}
          />
        </div>

        {/* Bottom Section: Ranked Candidates & Explainability */}
        <div className="flex-1 overflow-hidden">
          <CandidateRankingPanel
            candidates={candidates}
            selectedMmsi={selectedVesselMmsi}
            onSelectCandidate={handleSelectCandidate}
            isLoading={loadingCandidates || attributionMutation.isPending}
          />
        </div>
      </div>
    </div>
  );
};
