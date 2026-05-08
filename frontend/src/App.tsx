import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Auth } from './components/Auth';
import { Lobby } from './components/Lobby';
import { GameBoard } from './components/GameBoard';
import { NorthernPacificBoard } from './components/NorthernPacificBoard';
import { PrussianRailsBoard } from './components/PrussianRailsBoard';
import { NotificationPreferences } from './components/NotificationPreferences';
import { NotificationBell } from './components/NotificationBell';
import { useAuthStore, useGameStore } from './store';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAuthStore();
  return token ? <>{children}</> : <Navigate to="/login" />;
};

import { useParams } from 'react-router-dom';
import { useWebSocket } from './hooks/useWebSocket';

const GameRouter = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();

  useWebSocket(id || '');

  if (!gameState) {
    return <div className="p-8 text-center text-xl">Loading Game State...</div>;
  }

  if (gameState.train_pos !== undefined) {
    return <NorthernPacificBoard />;
  }
  if (gameState.game_type === 'prussian_rails') {
    return <PrussianRailsBoard />;
  }
  return <GameBoard />;
};

const NavBar: React.FC = () => {
  const { token, user, logout } = useAuthStore();
  if (!token) return null;

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 px-6 py-2 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <a href="/lobby" className="font-bold text-lg text-gray-800 no-underline">CubeRail</a>
        <a href="/lobby" className="text-sm text-gray-600 hover:text-gray-900 no-underline">Lobby</a>
        <a href="/notifications/preferences" className="text-sm text-gray-600 hover:text-gray-900 no-underline">Settings</a>
      </div>
      <div className="flex items-center gap-3">
        <NotificationBell />
        <span className="text-sm text-gray-600">{user?.username || ''}</span>
        <button onClick={logout} className="text-sm text-red-600 hover:underline cursor-pointer">Logout</button>
      </div>
    </nav>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        <NavBar />
        <Routes>
          <Route path="/login" element={<Auth />} />
          <Route
            path="/lobby"
            element={
              <PrivateRoute>
                <Lobby />
              </PrivateRoute>
            }
          />
          <Route
            path="/notifications/preferences"
            element={
              <PrivateRoute>
                <NotificationPreferences />
              </PrivateRoute>
            }
          />
          <Route
            path="/game/:id"
            element={
              <PrivateRoute>
                <GameRouter />
              </PrivateRoute>
            }
          />
          <Route path="/" element={<Navigate to="/lobby" />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default App;
