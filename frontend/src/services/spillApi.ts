import api from './api';
import type { SpillEvent, SpillStatus } from '../types';

export const spillApi = {
  getAll: async (status?: SpillStatus): Promise<SpillEvent[]> => {
    const params = status ? { status } : {};
    const { data } = await api.get<SpillEvent[]>('/api/spills', { params });
    return data;
  },
  getById: async (id: number): Promise<SpillEvent> => {
    const { data } = await api.get<SpillEvent>(`/api/spills/${id}`);
    return data;
  },
  create: async (payload: Partial<SpillEvent>): Promise<SpillEvent> => {
    const { data } = await api.post<SpillEvent>('/api/spills', payload);
    return data;
  },
  update: async (id: number, payload: Partial<SpillEvent>): Promise<SpillEvent> => {
    const { data } = await api.patch<SpillEvent>(`/api/spills/${id}`, payload);
    return data;
  },
  delete: async (id: number): Promise<{ success: boolean }> => {
    const { data } = await api.delete<{ success: boolean }>(`/api/spills/${id}`);
    return data;
  },
};
