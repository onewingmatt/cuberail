import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';

const HEX_RADIUS = 30;
const HEX_WIDTH = Math.sqrt(3) * HEX_RADIUS;
const HEX_HEIGHT = 2 * HEX_RADIUS;

export const GameBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { sendMove } = useWebSocket(id || '');

  const handleHexClick = (q: number, r: number) => {
    // Basic REST or WS call to place track
    sendMove('place_track', { hex: `${q},${r}`, company: 'Red' });
  };

  const renderHex = (q: number, r: number) => {
    const x = HEX_WIDTH * (q + r / 2);
    const y = HEX_HEIGHT * (3 / 4) * r;

    // Check if occupied in state
    const isOccupied = gameState?.board?.[`${q},${r}`];
    const fill = isOccupied ? (isOccupied === 'Red' ? '#ffcccc' : '#ccc') : 'transparent';

    return (
      <g
        key={`${q},${r}`}
        transform={`translate(${x + 100}, ${y + 100})`}
        onClick={() => handleHexClick(q, r)}
        className="cursor-pointer"
      >
        <polygon
          points="25.98,-15 0,-30 -25.98,-15 -25.98,15 0,30 25.98,15"
          fill={fill}
          stroke="#333"
          strokeWidth="1"
          className="hover:stroke-blue-500 hover:stroke-[2px]"
        />
        <text x="0" y="5" fontSize="10" textAnchor="middle" fill="#666">
          {q},{r}
        </text>
      </g>
    );
  };

  const hexes = [];
  for (let q = 0; q < 5; q++) {
    for (let r = 0; r < 5; r++) {
      hexes.push(renderHex(q, r));
    }
  }

  return (
    <div className="flex flex-col items-center p-8">
      <h2 className="text-2xl font-bold mb-4">Game: {id}</h2>
      <div className="bg-white p-4 shadow-lg rounded-lg overflow-auto">
        <svg width="600" height="400">
          {hexes}
        </svg>
      </div>

      <div className="mt-8 bg-white p-4 rounded shadow w-full max-w-2xl">
        <h3 className="font-bold text-lg mb-2">Game State Debug</h3>
        <pre className="bg-gray-100 p-2 text-sm overflow-auto">
          {JSON.stringify(gameState || { status: 'waiting for state...' }, null, 2)}
        </pre>
      </div>
    </div>
  );
};
