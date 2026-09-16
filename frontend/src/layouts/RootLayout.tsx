import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Sidebar } from '../components/Sidebar';
import { SyntheticBanner } from '../components/SyntheticBanner';
import type { User } from '../types';

interface RootLayoutProps {
  user: User | null;
  setUser: (user: User | null) => void;
  selectedSpillId: number | null;
  setSelectedSpillId: (id: number | null) => void;
}

export const RootLayout: React.FC<RootLayoutProps> = ({
  user,
  setUser,
  selectedSpillId,
  setSelectedSpillId,
}) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('oiltrace_token');
    localStorage.removeItem('oiltrace_user');
    setUser(null);
    navigate('/login');
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-navy-950">
      {/* Synthetic Disclaimer Banner */}
      <SyntheticBanner />

      {/* Top Navigation */}
      <Navbar
        user={user}
        onLogout={handleLogout}
        onSelectSpill={(id) => setSelectedSpillId(id)}
      />

      {/* Main App Workspace */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 relative overflow-hidden bg-navy-900/40">
          <Outlet context={{ selectedSpillId, setSelectedSpillId }} />
        </main>
      </div>
    </div>
  );
};
