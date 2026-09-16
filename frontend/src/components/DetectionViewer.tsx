import React, { useState } from 'react';
import { 
  Sparkles, 
  Layers, 
  Download, 
  Sliders, 
  CheckCircle2, 
  Activity, 
  ExternalLink,
  Eye
} from 'lucide-react';
import type { SpillEvent } from '../types';

interface DetectionViewerProps {
  spill: SpillEvent;
}

export const DetectionViewer: React.FC<DetectionViewerProps> = ({ spill }) => {
  const [activeTab, setActiveTab] = useState<'heatmap' | 'binary'>('heatmap');
  const [threshold, setThreshold] = useState<number>(0.5);

  const maskUrl = `/api/detection/${spill.id}/mask?format_type=${activeTab}`;
  const geojsonUrl = `/api/detection/${spill.id}/geojson`;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg mb-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              Deep U-Net SAR Detection &amp; Characterization
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Active Inference
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Sensor: {spill.satellite_image?.satellite || 'Sentinel-1A SAR'} &bull; Band: {spill.satellite_image?.polarization || 'VV'} &bull; Architecture: U-Net (v1.0)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={geojsonUrl}
            target="_blank"
            rel="noreferrer"
            download={`spill_${spill.id}_geojson.json`}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition"
          >
            <Download className="w-3.5 h-3.5" />
            Export GeoJSON
          </a>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Slick Surface Area</span>
          <span className="text-lg font-bold text-white tracking-tight">{spill.area_km2.toFixed(2)} <span className="text-xs font-normal text-slate-400">km²</span></span>
        </div>
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Geodesic Perimeter</span>
          <span className="text-lg font-bold text-white tracking-tight">{spill.perimeter_km.toFixed(2)} <span className="text-xs font-normal text-slate-400">km</span></span>
        </div>
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Model Confidence</span>
          <span className="text-lg font-bold text-emerald-400 tracking-tight">{(spill.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Centroid Coordinates</span>
          <span className="text-xs font-mono text-cyan-400 font-medium block mt-1">
            {spill.centroid?.coordinates ? `${spill.centroid.coordinates[1].toFixed(4)}°N, ${spill.centroid.coordinates[0].toFixed(4)}°E` : 'N/A'}
          </span>
        </div>
      </div>

      {/* Interactive Mask Preview & Controls */}
      <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-300">View Mode:</span>
            <div className="inline-flex rounded-md shadow-sm bg-slate-900 border border-slate-800 p-0.5">
              <button
                type="button"
                onClick={() => setActiveTab('heatmap')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  activeTab === 'heatmap' 
                    ? 'bg-indigo-600 text-white shadow' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Probability Heatmap
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('binary')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  activeTab === 'binary' 
                    ? 'bg-indigo-600 text-white shadow' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Binary Segmentation Mask
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-400">Threshold:</span>
              <input
                type="range"
                min="0.2"
                max="0.8"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-24 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <span className="text-xs font-mono text-indigo-400 font-semibold">{threshold.toFixed(2)}</span>
            </div>

            <a
              href={maskUrl}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition"
            >
              <ExternalLink className="w-3 h-3" />
              Full Resolution
            </a>
          </div>
        </div>

        {/* Mask Image Preview Container */}
        <div className="relative aspect-video max-h-72 w-full bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
          <img
            src={maskUrl}
            alt="SAR Oil Spill Probability Mask"
            className="w-full h-full object-contain"
            onError={(e) => {
              // Graceful fallback for synthetic demo spills without cached raster files
              (e.target as HTMLElement).style.display = 'none';
              const parent = (e.target as HTMLElement).parentElement;
              if (parent) {
                const fallback = document.createElement('div');
                fallback.className = 'text-center p-6 text-slate-400 text-xs';
                fallback.innerHTML = `
                  <div class="font-semibold text-slate-300 mb-1">SAR Radar Backscatter Layer Active</div>
                  <div>Polygonized segmentation overlay active on GIS Map (${spill.area_km2.toFixed(2)} km²)</div>
                `;
                parent.appendChild(fallback);
              }
            }}
          />
        </div>
      </div>
    </div>
  );
};
