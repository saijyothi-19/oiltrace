import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Ship, Search, Navigation, Compass, ArrowUpRight, Activity } from 'lucide-react';
import { vesselApi } from '../services/aisApi';
import type { Vessel } from '../types';

export const VesselsPage: React.FC = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const { data: vessels = [], isLoading } = useQuery({
    queryKey: ['vessels'],
    queryFn: () => vesselApi.getAll(),
  });

  const filteredVessels = vessels.filter((v) => {
    return (
      v.name.toLowerCase().includes(search.toLowerCase()) ||
      v.mmsi.includes(search) ||
      (v.ship_type || '').toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <div className="h-full flex flex-col p-6 overflow-y-auto select-none bg-navy-950">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-mono font-bold text-white flex items-center gap-2">
            <Ship className="w-5 h-5 text-cyan-400" />
            AUTOMATIC IDENTIFICATION SYSTEM (AIS) REGISTRY
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Historical maritime transponder tracks, velocity profiles, and attribution analysis
          </p>
        </div>

        {/* Search */}
        <div className="relative w-72">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search MMSI, vessel name, or type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-navy-900 border border-slate-700/80 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>
      </div>

      {/* Vessels Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-xs text-slate-400 font-mono">
          Loading AIS vessel transponder records...
        </div>
      ) : filteredVessels.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center p-8 bg-navy-900/60 rounded-xl border border-slate-800">
          <Ship className="w-12 h-12 text-slate-600 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Vessels Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            No AIS vessels match your query. Click "Load Demo Investigation" to populate candidate vessel tracks.
          </p>
        </div>
      ) : (
        <div className="bg-navy-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-3">Vessel Name</th>
                <th className="px-4 py-3">MMSI</th>
                <th className="px-4 py-3">Ship Type</th>
                <th className="px-4 py-3">Flag</th>
                <th className="px-4 py-3">Waypoints</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-200">
              {filteredVessels.map((vessel) => (
                <tr
                  key={vessel.id}
                  onClick={() => navigate(`/vessels/${vessel.mmsi}`)}
                  className="hover:bg-slate-800/60 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 font-semibold text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                    {vessel.name}
                  </td>
                  <td className="px-4 py-3 text-cyan-300">{vessel.mmsi}</td>
                  <td className="px-4 py-3 text-slate-400">{vessel.ship_type}</td>
                  <td className="px-4 py-3 text-slate-400">{vessel.flag || 'Unknown'}</td>
                  <td className="px-4 py-3 text-slate-400">{vessel.positions?.length || 0}</td>
                  <td className="px-4 py-3 text-right">
                    <button className="text-cyan-400 hover:text-cyan-300 text-[11px] inline-flex items-center gap-1">
                      <span>Track Profile</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
