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
  search: async (params: { satellite?: string; start_date?: string; end_date?: string }): Promise<SatelliteImage[]> => {
    const { data } = await api.get<SatelliteImage[]>('/api/satellite/search', { params });
    return data;
  },
};
