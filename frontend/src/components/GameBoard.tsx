import React from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';
import { GameRenderer } from './GameRenderer';

export const GameBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { sendMove } = useWebSocket(id || '', false);

  const handleHexClick = (q: number, r: number) => {
    sendMove('place_track', { hex: `${q},${r}`, company: 'Red' });
  };

  const hexes: any[] = [];
  for (let q = 0; q < 5; q++) {
    for (let r = 0; r < 5; r++) {
      const isOccupied = gameState?.board?.[`${q},${r}`];
      const color = isOccupied ? (isOccupied === 'Red' ? '#ffcccc' : '#ccc') : 'transparent';
      hexes.push({
        id: `${q},${r}`,
        q,
        r,
        color
      });
    }
  }

  return (
    <div className="flex flex-col items-center p-8">
      <h2 className="text-2xl font-bold mb-4">Game: {id}</h2>

      <div className="flex gap-4 w-full max-w-4xl">
        <GameRenderer
          boardType="hex"
          hexes={hexes}
          onHexClick={handleHexClick}
        />

        <div className="w-64 bg-white p-4 rounded shadow">
          <h3 className="font-bold text-lg mb-2">Game State Debug</h3>
          <pre className="bg-gray-100 p-2 text-xs overflow-auto h-64">
            {JSON.stringify(gameState || { status: 'waiting for state...' }, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};
