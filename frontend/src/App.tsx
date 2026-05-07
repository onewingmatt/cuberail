import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Auth } from './components/Auth';
import { Lobby } from './components/Lobby';
import { GameBoard } from './components/GameBoard';
import { NorthernPacificBoard } from './components/NorthernPacificBoard';
import { useAuthStore, useGameStore } from './store';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAuthStore();
  return token ? <>{children}</> : <Navigate to="/login" />;
};

const GameRouter = () => {
  const { gameState } = useGameStore();
  // We can determine which board to show based on state shape
  // If state has 'train_pos', it's NP. Else simple rail.
  if (gameState && gameState.train_pos !== undefined) {
    return <NorthernPacificBoard />;
  }
  return <GameBoard />;
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
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
