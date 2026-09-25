import api from './api';
import type { VesselCandidate, Investigation, SystemStatus } from '../types';

export const attributionApi = {
  analyze: async (spillId: number, params?: { spatial_radius_km?: number; temporal_window_hours?: number }): Promise<VesselCandidate[]> => {
    const { data } = await api.post<VesselCandidate[]>(`/api/attribution/analyze/${spillId}`, params || {});
    return data;
  },
  getCandidates: async (spillId: number): Promise<VesselCandidate[]> => {
    const { data } = await api.get<VesselCandidate[]>(`/api/attribution/${spillId}/candidates`);
    return data;
  },
  getCandidateById: async (spillId: number, candidateId: number): Promise<VesselCandidate> => {
    const { data } = await api.get<VesselCandidate>(`/api/attribution/${spillId}/candidate/${candidateId}`);
    return data;
  },
};

export const investigationApi = {
  getAll: async (): Promise<Investigation[]> => {
    const { data } = await api.get<Investigation[]>('/api/investigations');
    return data;
  },
  getById: async (id: number): Promise<Investigation> => {
    const { data } = await api.get<Investigation>(`/api/investigations/${id}`);
    return data;
  },
  create: async (payload: { spill_event_id: number; status?: string; notes?: string }): Promise<Investigation> => {
    const { data } = await api.post<Investigation>('/api/investigations', payload);
    return data;
  },
  update: async (id: number, payload: { status?: string; notes?: string; assigned_to?: number }): Promise<Investigation> => {
    const { data } = await api.patch<Investigation>(`/api/investigations/${id}`, payload);
    return data;
  },
};

export const reportApi = {
  generate: async (spillId: number): Promise<any> => {
    const { data } = await api.post(`/api/reports/${spillId}`);
    return data;
  },
  getById: async (id: number): Promise<any> => {
    const { data } = await api.get(`/api/reports/${id}`);
    return data;
  },
};

export const systemApi = {
  getStatus: async (): Promise<SystemStatus> => {
    const { data } = await api.get<SystemStatus>('/api/system/status');
    return data;
  },
  getProvenance: async (): Promise<any> => {
    const { data } = await api.get('/api/system/provenance');
    return data;
  },
  loadDemo: async (): Promise<{ success: boolean; spill_id: number; message: string }> => {
    const { data } = await api.post('/api/demo/load');
    return data;
  },
};
