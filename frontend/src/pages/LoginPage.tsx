import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Waves, Lock, Mail, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { authApi } from '../services/authApi';
import type { User } from '../types';

interface LoginPageProps {
  setUser: (user: User) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ setUser }) => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('analyst@oiltrace.org');
  const [password, setPassword] = useState('AnalystPass2026!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await authApi.login(email, password);
      localStorage.setItem('oiltrace_token', resp.access_token);
      localStorage.setItem('oiltrace_user', JSON.stringify(resp.user));
      setUser(resp.user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoCredentials = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="min-h-screen w-screen flex flex-col items-center justify-center bg-navy-950 px-4 relative overflow-hidden">
      {/* Background ambient radial glow */}
      <div className="absolute w-[600px] h-[600px] bg-cyan-900/10 rounded-full blur-3xl pointer-events-none -top-40 -left-40"></div>
      <div className="absolute w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-3xl pointer-events-none -bottom-40 -right-40"></div>

      <div className="w-full max-w-md bg-navy-900/90 border border-slate-800 rounded-xl p-8 shadow-2xl backdrop-blur relative z-10">
        {/* Brand */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-3 shadow-lg shadow-cyan-500/20">
            <Waves className="w-7 h-7" />
          </div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-white flex items-center gap-2">
            OILTRACE
            <span className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded font-sans border border-cyan-500/30">
              SIH 2026
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Marine Oil Spill Detection & Attribution Decision Support System
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-950/80 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Analyst Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@oiltrace.org"
                className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Access Credential (Password)
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-900/90 border border-slate-700/80 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors font-mono"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20 transition-all border border-cyan-400/30 disabled:opacity-50"
          >
            {loading ? 'Authenticating...' : 'Sign In to Console'}
          </button>
        </form>

        {/* Quick Demo Accounts */}
        <div className="mt-6 pt-4 border-t border-slate-800">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
            One-Click Demo Roles
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => setDemoCredentials('analyst@oiltrace.org', 'AnalystPass2026!')}
              className="px-2 py-1.5 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-[11px] text-cyan-300 text-center transition-colors"
            >
              Analyst
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('admin@oiltrace.org', 'AdminPass2026!')}
              className="px-2 py-1.5 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-[11px] text-amber-300 text-center transition-colors"
            >
              Lead (Admin)
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('viewer@oiltrace.org', 'ViewerPass2026!')}
              className="px-2 py-1.5 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-[11px] text-slate-300 text-center transition-colors"
            >
              Viewer
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-[10px] text-slate-500">
          OILTRACE v1.0.0 — SIH 2026 Decision Support Prototype
        </div>
      </div>
    </div>
  );
};
