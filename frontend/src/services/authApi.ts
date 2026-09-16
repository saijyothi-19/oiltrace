import api from './api';
import type { AuthResponse, User } from '../types';

export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const { data } = await api.post<AuthResponse>('/api/auth/login', { email, password });
    return data;
  },
  register: async (payload: { name: string; email: string; password: string; role?: string }): Promise<User> => {
    const { data } = await api.post<User>('/api/auth/register', payload);
    return data;
  },
  getMe: async (): Promise<User> => {
    const { data } = await api.get<User>('/api/auth/me');
    return data;
  },
};
