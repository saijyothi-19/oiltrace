import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Flame, 
  Ship, 
  FolderKanban, 
  FileText, 
  Radio, 
  Compass
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../services/attributionApi';

export const Sidebar: React.FC = () => {
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: systemApi.getStatus,
    refetchInterval: 15000,
  });

  const navItems = [
    { to: '/', label: 'GIS Dashboard', icon: LayoutDashboard },
    { to: '/spills', label: 'Spill Events', icon: Flame },
    { to: '/vessels', label: 'AIS & Vessels', icon: Ship },
    { to: '/investigations', label: 'Investigations', icon: FolderKanban },
    { to: '/reports', label: 'Reports', icon: FileText },
  ];

  return (
    <aside className="w-64 bg-navy-900 border-r border-slate-800 flex flex-col justify-between shrink-0 h-[calc(100vh-85px)] select-none">
      {/* Primary navigation */}
      <div className="p-3 space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
          Operational Workspace
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 border-l-2 border-cyan-400 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Telemetry / Live statistics widget */}
      <div className="p-3 m-3 bg-slate-900/80 rounded-lg border border-slate-800/80 text-xs">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 font-semibold">
            <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
            LIVE METRICS
          </span>
          <span className="text-[10px] text-slate-500 font-mono">WGS84</span>
        </div>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between items-center text-slate-400">
            <span>Detected Spills:</span>
            <span className="font-mono font-bold text-amber-400">{status?.active_spills_count ?? 0}</span>
          </div>
          <div className="flex justify-between items-center text-slate-400">
            <span>Open Cases:</span>
            <span className="font-mono font-bold text-cyan-400">{status?.active_investigations_count ?? 0}</span>
          </div>
          <div className="flex justify-between items-center text-slate-400">
            <span>AIS Vessels:</span>
            <span className="font-mono font-bold text-emerald-400">{status?.total_vessels_tracked ?? 0}</span>
          </div>
        </div>

        <div className="mt-3 pt-2 border-t border-slate-800 text-[10px] text-slate-500 font-mono flex items-center justify-between">
          <span>ACCEL: {status?.ml_device?.toUpperCase() || 'CPU'}</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <Compass className="w-3 h-3" />
            POSTGIS
          </span>
        </div>
      </div>
    </aside>
  );
};
