import api from './api';
import type { Vessel, AisPosition } from '../types';

export const aisApi = {
  importData: async (formData: FormData): Promise<{ imported_records: number; vessels_updated: number }> => {
    const { data } = await api.post('/api/ais/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  getNearby: async (params: { lat: number; lon: number; radius_km: number; start_time?: string; end_time?: string }): Promise<Vessel[]> => {
    const { data } = await api.get<Vessel[]>('/api/ais/nearby', { params });
    return data;
  },
};

export const vesselApi = {
  getAll: async (): Promise<Vessel[]> => {
    const { data } = await api.get<Vessel[]>('/api/ais/vessels');
    return data;
  },
  getByMmsi: async (mmsi: string): Promise<Vessel> => {
    const { data } = await api.get<Vessel>(`/api/ais/vessel/${mmsi}`);
    return data;
  },
  getTrack: async (mmsi: string, start_time?: string, end_time?: string): Promise<AisPosition[]> => {
    const params: Record<string, string> = {};
    if (start_time) params.start_time = start_time;
    if (end_time) params.end_time = end_time;
    const { data } = await api.get<AisPosition[]>(`/api/ais/vessel/${mmsi}/track`, { params });
    return data;
  },
};
