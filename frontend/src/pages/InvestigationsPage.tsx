import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FolderKanban, ArrowUpRight, Flame, Clock, User as UserIcon, CheckCircle2 } from 'lucide-react';
import { investigationApi } from '../services/attributionApi';
import type { Investigation, InvestigationStatus } from '../types';

export const InvestigationsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedCase, setSelectedCase] = useState<Investigation | null>(null);
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState<InvestigationStatus>('UNDER REVIEW');

  const { data: investigations = [], isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => investigationApi.getAll(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: any }) =>
      investigationApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
      setSelectedCase(null);
    },
  });

  const handleOpenModal = (inv: Investigation) => {
    setSelectedCase(inv);
    setNotes(inv.notes || '');
    setStatus(inv.status);
  };

  const handleSave = () => {
    if (selectedCase) {
      updateMutation.mutate({
        id: selectedCase.id,
        payload: { status, notes },
      });
    }
  };

  const getStatusBadge = (st: InvestigationStatus) => {
    switch (st) {
      case 'NEW':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'UNDER REVIEW':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'HIGH PRIORITY':
        return 'bg-red-500/20 text-red-300 border-red-500/30 animate-pulse';
      case 'RESOLVED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'CLOSED':
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="h-full flex flex-col p-6 overflow-y-auto select-none bg-navy-950">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-mono font-bold text-white flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-cyan-400" />
            OIL SPILL INCIDENT INVESTIGATIONS
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Analyst case management, evidence dossiers, and case status audits
          </p>
        </div>
      </div>

      {/* Case List Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-xs text-slate-400 font-mono">
          Loading investigation case files...
        </div>
      ) : investigations.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center p-8 bg-navy-900/60 rounded-xl border border-slate-800">
          <FolderKanban className="w-12 h-12 text-slate-600 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Open Cases</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            Cases are created automatically when spills are detected or demo cases are loaded.
          </p>
        </div>
      ) : (
        <div className="bg-navy-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Spill Event</th>
                <th className="px-4 py-3">Assigned Lead</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last Updated</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-200">
              {investigations.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 font-semibold text-cyan-300">
                    CASE-2026-{inv.id.toString().padStart(4, '0')}
                  </td>
                  <td className="px-4 py-3 text-white flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5 text-red-500" />
                    Spill #{inv.spill_event_id}
                  </td>
                  <td className="px-4 py-3 text-slate-400 flex items-center gap-1.5">
                    <UserIcon className="w-3.5 h-3.5 text-slate-500" />
                    {inv.assignee?.name || 'Maritime Analyst'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusBadge(inv.status)}`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {new Date(inv.updated_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <button
                      onClick={() => handleOpenModal(inv)}
                      className="text-cyan-400 hover:text-cyan-300 text-[11px] underline"
                    >
                      Update Case
                    </button>
                    <button
                      onClick={() => navigate(`/spills/${inv.spill_event_id}`)}
                      className="text-slate-400 hover:text-white text-[11px] inline-flex items-center gap-0.5"
                    >
                      <span>Console</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Case Management Modal */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-navy-900 border border-slate-700 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-sm text-white">
                Update Case #CASE-2026-{selectedCase.id.toString().padStart(4, '0')}
              </h3>
              <button
                onClick={() => setSelectedCase(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Investigation Status:
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as InvestigationStatus)}
                className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="NEW">NEW</option>
                <option value="UNDER REVIEW">UNDER REVIEW</option>
                <option value="HIGH PRIORITY">HIGH PRIORITY</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="CLOSED">CLOSED</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Analyst Investigation Notes & Evidence Log:
              </label>
              <textarea
                rows={4}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Document observed vessel trajectory anomalies, hindcast correlation notes, and decision support findings..."
                className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedCase(null)}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow transition-colors disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Case File'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
