import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { Flame, Calendar, Maximize, Ruler, ArrowUpRight, Search, Filter, Upload, Sparkles, X, Loader2 } from 'lucide-react';
import { spillApi } from '../services/spillApi';
import type { SpillStatus, SpillEvent } from '../types';

interface ContextType {
  selectedSpillId: number | null;
  setSelectedSpillId: (id: number | null) => void;
}

export const SpillsPage: React.FC = () => {
  const navigate = useNavigate();
  const { setSelectedSpillId } = useOutletContext<ContextType>();
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadThreshold, setUploadThreshold] = useState<number>(0.5);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: spills = [], isLoading, refetch } = useQuery({
    queryKey: ['spills'],
    queryFn: () => spillApi.getAll(),
  });

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('threshold', uploadThreshold.toString());
    formData.append('min_area_km2', '0.01');
    formData.append('min_lon', '72.0');
    formData.append('min_lat', '18.5');
    formData.append('max_lon', '73.0');
    formData.append('max_lat', '19.5');
    formData.append('filter_lookalikes', 'true');

    try {
      const response = await fetch('/api/detection/upload-and-detect', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.error?.message || errJson?.detail || 'Detection failed.');
      }

      const createdSpill = await response.json();
      setShowUploadModal(false);
      setUploadFile(null);
      await refetch();
      setSelectedSpillId(createdSpill.id);
      navigate(`/spills/${createdSpill.id}`);
    } catch (err: any) {
      setUploadError(err.message || 'Error processing SAR image.');
    } finally {
      setIsUploading(false);
    }
  };

  const filteredSpills = spills.filter((s) => {
    const matchesStatus = filterStatus === 'ALL' || s.status === filterStatus;
    const matchesSearch = s.id.toString().includes(search) || 
      (s.satellite_image?.satellite || '').toLowerCase().includes(search.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const handleOpenSpill = (spill: SpillEvent) => {
    setSelectedSpillId(spill.id);
    navigate(`/spills/${spill.id}`);
  };

  return (
    <div className="h-full flex flex-col p-6 overflow-y-auto select-none bg-navy-950">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-mono font-bold text-white flex items-center gap-2">
            <Flame className="w-5 h-5 text-red-500" />
            DETECTED MARINE OIL SPILLS
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Satellite SAR detections, characterization metrics, and analysis status
          </p>
        </div>

        {/* Action Controls & Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md transition"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload SAR &amp; Detect
          </button>

          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search spill ID or satellite..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-navy-900 border border-slate-700/80 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-navy-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          >
            <option value="ALL">All Statuses</option>
            <option value="DETECTED">DETECTED</option>
            <option value="ACCEPTED">ACCEPTED</option>
            <option value="REVIEW REQUIRED">REVIEW REQUIRED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </div>
      </div>

      {/* Upload & Detect Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2 font-mono">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Upload SAR Scene &amp; Run AI Segmentation
              </h3>
              <button
                onClick={() => { setShowUploadModal(false); setUploadError(null); }}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  SAR Raster File (.tif, .png, .npy, .jpg, .webp)
                </label>
                <input
                  type="file"
                  accept=".tif,.tiff,.png,.npy,.jpg,.jpeg,.webp"
                  required
                  onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer bg-slate-950 border border-slate-800 rounded-lg p-2"
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-slate-300 mb-1">
                  <span>Segmentation Probability Threshold</span>
                  <span className="font-mono text-indigo-400 font-semibold">{uploadThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.2"
                  max="0.8"
                  step="0.05"
                  value={uploadThreshold}
                  onChange={(e) => setUploadThreshold(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
              </div>

              <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-400">
                <span className="text-slate-300 font-medium block mb-1">Default Scene Bounds:</span>
                Offshore Mumbai Corridor (18.5°N–19.5°N, 72.0°E–73.0°E). Preprocessing applies Sigma-0 calibration, Lee speckle filtering, and U-Net inference.
              </div>

              {uploadError && (
                <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 text-xs rounded-lg">
                  {uploadError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || isUploading}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg shadow-md transition"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Processing SAR Scene...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Execute Detection</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Grid of Spill Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-xs text-slate-400 font-mono">
          Loading spill detections from PostGIS...
        </div>
      ) : filteredSpills.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-center p-8 bg-navy-900/60 rounded-xl border border-slate-800">
          <Flame className="w-12 h-12 text-slate-600 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Spills Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm">
            No oil spill events match your filter. Click "Load Demo Investigation" in the top bar to populate demonstration data.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSpills.map((spill) => (
            <div
              key={spill.id}
              onClick={() => handleOpenSpill(spill)}
              className="bg-navy-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-cyan-500/50 rounded-xl p-4 transition-all cursor-pointer shadow-lg group relative overflow-hidden"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 group-hover:animate-ping" />
                  <span className="font-mono font-bold text-sm text-white">
                    SPILL #{spill.id}
                  </span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                  {spill.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono mb-4">
                <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                  <div className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Maximize className="w-3 h-3 text-cyan-400" />
                    Area
                  </div>
                  <div className="font-bold text-white mt-0.5">
                    {spill.area_km2.toFixed(2)} km&sup2;
                  </div>
                </div>

                <div className="bg-slate-950/60 p-2 rounded border border-slate-800/80">
                  <div className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Ruler className="w-3 h-3 text-cyan-400" />
                    Perimeter
                  </div>
                  <div className="font-bold text-white mt-0.5">
                    {spill.perimeter_km.toFixed(2)} km
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-3">
                <div className="flex items-center gap-1.5 font-mono">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  <span>{new Date(spill.detected_at).toLocaleDateString()}</span>
                </div>
                <div className="text-cyan-400 font-mono font-semibold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                  <span>Open Investigation</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
