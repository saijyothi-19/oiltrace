import api from './api';
import type { SpillEvent } from '../types';

export interface DetectionRequest {
  satellite_image_id: number;
  threshold?: number;
  min_area_km2?: number;
  filter_lookalikes?: boolean;
}

export const detectionApi = {
  run: async (payload: DetectionRequest): Promise<SpillEvent> => {
    const { data } = await api.post<SpillEvent>('/api/detection/run', payload);
    return data;
  },
  getById: async (id: number): Promise<any> => {
    const { data } = await api.get(`/api/detection/${id}`);
    return data;
  },
  getResult: async (id: number): Promise<any> => {
    const { data } = await api.get(`/api/detection/${id}/result`);
    return data;
  },
};
