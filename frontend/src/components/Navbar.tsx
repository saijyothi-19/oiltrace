import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Waves, Sparkles, User as UserIcon, LogOut, Activity } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { systemApi } from '../services/attributionApi';
import type { User } from '../types';

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
  onSelectSpill?: (spillId: number) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onLogout, onSelectSpill }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const loadDemoMutation = useMutation({
    mutationFn: systemApi.loadDemo,
    onSuccess: (data) => {
      queryClient.invalidateQueries();
      if (data.spill_id) {
        if (onSelectSpill) {
          onSelectSpill(data.spill_id);
        }
        navigate(`/spills/${data.spill_id}`);
      }
    },
  });

  return (
    <header className="bg-navy-900/90 backdrop-blur border-b border-slate-800 px-4 py-2.5 flex items-center justify-between z-30">
      {/* Brand */}
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
        <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-sm shadow-cyan-500/20">
          <Waves className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5 font-mono">
              OILTRACE
              <span className="text-[10px] uppercase font-sans tracking-wider bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded font-semibold">
                AI / SAR / AIS
              </span>
            </h1>
          </div>
          <p className="text-[11px] text-slate-400 leading-none">
            Marine Oil Spill Detection & Attribution System
          </p>
        </div>
      </div>

      {/* Center status */}
      <div className="hidden md:flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/60 px-3 py-1 rounded-full text-slate-300 font-mono">
          <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
          <span>SYS STATUS: <strong className="text-emerald-400">ONLINE</strong></span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* One-Click Load Demo Button */}
        <button
          onClick={() => loadDemoMutation.mutate()}
          disabled={loadDemoMutation.isPending}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-medium shadow-md shadow-cyan-500/20 transition-all border border-cyan-400/30 disabled:opacity-50"
          title="Load demonstration scenario with Sentinel-1 SAR scene, spill detection, hindcast drift, and AIS vessels"
        >
          <Sparkles className={`w-3.5 h-3.5 text-yellow-300 ${loadDemoMutation.isPending ? 'animate-spin' : ''}`} />
          <span>{loadDemoMutation.isPending ? 'Loading Case...' : 'Load Demo Investigation'}</span>
        </button>

        {/* User profile / Logout */}
        {user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-slate-700/60">
            <div className="flex items-center gap-1.5 text-xs text-slate-300">
              <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                <UserIcon className="w-3.5 h-3.5" />
              </div>
              <div className="hidden lg:block text-left leading-tight">
                <div className="font-semibold text-slate-200">{user.name}</div>
                <div className="text-[10px] text-cyan-400 font-mono">{user.role}</div>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 rounded-md text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded border border-slate-700 text-slate-200 transition-colors"
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
};
