import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';

interface SyntheticBannerProps {
  isSynthetic?: boolean;
}

export const SyntheticBanner: React.FC<SyntheticBannerProps> = ({ isSynthetic = true }) => {
  if (!isSynthetic) return null;

  return (
    <div className="bg-amber-950/70 border-b border-amber-600/40 px-4 py-1.5 flex items-center justify-between text-xs text-amber-200">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="font-semibold tracking-wide uppercase text-[11px] bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-500/30">
          Synthetic Demonstration Data
        </span>
        <span>— Not real-world evidence. Candidate rankings do not establish legal responsibility or causation.</span>
      </div>
      <div className="hidden sm:flex items-center gap-1.5 text-amber-300/80 text-[11px]">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        <span>Decision Support Sandbox (SIH 2026)</span>
      </div>
    </div>
  );
};
