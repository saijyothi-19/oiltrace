import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { RootLayout } from './layouts/RootLayout';
import { DashboardPage } from './pages/DashboardPage';
import { SpillsPage } from './pages/SpillsPage';
import { SpillDetailPage } from './pages/SpillDetailPage';
import { VesselsPage } from './pages/VesselsPage';
import { VesselDetailPage } from './pages/VesselDetailPage';
import { InvestigationsPage } from './pages/InvestigationsPage';
import { ReportsPage } from './pages/ReportsPage';
import { ReportDetailPage } from './pages/ReportDetailPage';
import { LoginPage } from './pages/LoginPage';
import type { User } from './types';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('oiltrace_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    // Default authenticated analyst for fast local evaluation
    return {
      id: 2,
      name: 'Maritime Analyst',
      email: 'analyst@oiltrace.org',
      role: 'ANALYST',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  });

  const [selectedSpillId, setSelectedSpillId] = useState<number | null>(null);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage setUser={setUser} />} />
      <Route
        path="/"
        element={
          <RootLayout
            user={user}
            setUser={setUser}
            selectedSpillId={selectedSpillId}
            setSelectedSpillId={setSelectedSpillId}
          />
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="spills" element={<SpillsPage />} />
        <Route path="spills/:id" element={<SpillDetailPage />} />
        <Route path="vessels" element={<VesselsPage />} />
        <Route path="vessels/:mmsi" element={<VesselDetailPage />} />
        <Route path="investigations" element={<InvestigationsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="reports/:id" element={<ReportDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
