import api from './api';
import type { DriftSimulation } from '../types';

export interface DriftSimulationRequest {
  spill_event_id: number;
  duration_hours?: number;
  particle_count?: number;
  timestep_minutes?: number;
  windage_factor?: number;
}

export const driftApi = {
  runBackward: async (payload: DriftSimulationRequest): Promise<DriftSimulation> => {
    const { data } = await api.post<DriftSimulation>('/api/drift/backward', payload);
    return data;
  },
  runForward: async (payload: DriftSimulationRequest): Promise<DriftSimulation> => {
    const { data } = await api.post<DriftSimulation>('/api/drift/forward', payload);
    return data;
  },
  getById: async (id: number): Promise<DriftSimulation> => {
    const { data } = await api.get<DriftSimulation>(`/api/drift/${id}`);
    return data;
  },
  getTrajectory: async (id: number): Promise<any> => {
    const { data } = await api.get(`/api/drift/${id}/trajectory`);
    return data;
  },
};
