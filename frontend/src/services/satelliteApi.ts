import api from './api';
import type { SatelliteImage } from '../types';

export const satelliteApi = {
  getAll: async (): Promise<SatelliteImage[]> => {
    const { data } = await api.get<SatelliteImage[]>('/api/satellite');
    return data;
  },
  getById: async (id: number): Promise<SatelliteImage> => {
    const { data } = await api.get<SatelliteImage>(`/api/satellite/${id}`);
    return data;
  },
  upload: async (formData: FormData): Promise<SatelliteImage> => {
    const { data } = await api.post<SatelliteImage>('/api/satellite/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  search: async (params: { satellite?: string; start_date?: string; end_date?: string; live_cdse?: boolean; min_lon?: number; min_lat?: number; max_lon?: number; max_lat?: number }): Promise<any> => {
    const { data } = await api.get('/api/satellite/search', { params });
    return data;
  },
  getLatest: async (params?: { latitude?: number; longitude?: number; radius_km?: number }): Promise<any> => {
    const { data } = await api.get('/api/satellite/latest', { params: params || {} });
    return data;
  },
  searchCdse: async (params: { min_lon: number; min_lat: number; max_lon: number; max_lat: number; limit?: number }): Promise<any> => {
    const { data } = await api.get('/api/satellite/cdse/search', { params });
    return data;
  },
};

