import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore, useAuthStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';
import { GameRenderer } from './GameRenderer';

// Rough visual coordinates for the NP graph
const CITY_COORDS: Record<string, { x: number, y: number }> = {
  "StPaul": { x: 500, y: 300 },
  "Duluth": { x: 550, y: 200 },
  "Fargo": { x: 400, y: 250 },
  "Bismarck": { x: 300, y: 250 },
  "Billings": { x: 200, y: 250 },
  "Helena": { x: 150, y: 200 },
  "Spokane": { x: 100, y: 150 },
  "Seattle": { x: 50, y: 200 }
};

export const NorthernPacificBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { user } = useAuthStore();
  const { sendMove } = useWebSocket(id || '', false);

  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  if (!gameState) return null;

  const handleCityClick = (city: string) => {
    setSelectedCity(city);
  };

  const handleInvest = () => {
    if (selectedCity) {
      sendMove('invest', { city: selectedCity });
      setSelectedCity(null);
    }
  };

  const handleMoveTrain = () => {
    if (selectedCity) {
      sendMove('move_train', { city: selectedCity });
      setSelectedCity(null);
    }
  };

  const isMyTurn = gameState.current_player === user?.id;

  // Build Generic Nodes/Edges
  const graphEdges: any[] = [];
  const graphNodes: any[] = [];

  if (gameState.graph) {
    Object.entries(gameState.graph).forEach(([city, neighbors]) => {
      neighbors.forEach(neighbor => {
        if (city < neighbor) {
          const start = CITY_COORDS[city];
          const end = CITY_COORDS[neighbor];
          if (start && end) {
            graphEdges.push({ start, end });
          }
        }
      });
    });
  }

  Object.entries(CITY_COORDS).forEach(([city, coords]) => {
    const isInvested = !!(gameState.investments && gameState.investments[city]);
    const isSelected = selectedCity === city;
    const hasTrain = gameState.train_pos === city;

    graphNodes.push({
      id: city,
      x: coords.x,
      y: coords.y,
      color: isInvested ? '#4f46e5' : '#fff',
      stroke: isSelected ? '#ef4444' : '#333',
      hasTrain,
      isInvested
    });
  });

  return (
    <div className="flex flex-col items-center p-8">
      <h2 className="text-2xl font-bold mb-4">Northern Pacific: {id}</h2>

      {gameState.game_over && (
        <div className="bg-red-100 text-red-800 p-4 mb-4 rounded border border-red-300">
          Game Over! Train reached Seattle.
        </div>
      )}

      <div className="flex gap-4 w-full max-w-4xl">
        <GameRenderer
          boardType="graph"
          graphEdges={graphEdges}
          graphNodes={graphNodes}
          onNodeClick={handleCityClick}
        />

        <div className="w-64 flex flex-col gap-4">
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Controls</h3>
            <p className="text-sm mb-4">
              Turn: <span className={isMyTurn ? "font-bold text-green-600" : ""}>{gameState.current_player}</span>
            </p>
            {selectedCity ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm">Selected: {selectedCity}</p>
                <button
                  onClick={handleInvest}
                  disabled={!isMyTurn || gameState.game_over}
                  className="bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  Invest
                </button>
                <button
                  onClick={handleMoveTrain}
                  disabled={!isMyTurn || gameState.game_over}
                  className="bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700 disabled:opacity-50"
                >
                  Move Train Here
                </button>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Select a city on the map.</p>
            )}
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Balances</h3>
            {gameState.balances && Object.entries(gameState.balances).map(([pid, bal]) => (
              <div key={pid} className="flex justify-between text-sm">
                <span>{pid.slice(0, 8)}...</span>
                <span className="font-bold">${bal}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
