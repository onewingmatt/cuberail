import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuthStore } from '../store';

export const Lobby: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [mode, setMode] = useState<'async' | 'realtime'>('async');
  const [botCount, setBotCount] = useState(0);

  const handleCreateGame = async (gameType: string) => {
    try {
      const response = await axios.post(
        `http://localhost:8000/api/games/?game_type=${gameType}&mode=${mode}&bot_count=${botCount}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.data && response.data.game_id) {
        navigate(`/game/${response.data.game_id}`);
      }
    } catch (err) {
      console.error("Failed to create game", err);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Game Lobby</h1>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Start a New Game</h2>

        {/* Mode toggle */}
        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm font-medium text-gray-700">Game mode:</span>
          <div className="flex rounded border border-gray-300 overflow-hidden">
            <button
              onClick={() => setMode('async')}
              className={`px-3 py-1.5 text-sm font-medium cursor-pointer transition-colors ${
                mode === 'async' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              Async
            </button>
            <button
              onClick={() => setMode('realtime')}
              className={`px-3 py-1.5 text-sm font-medium cursor-pointer transition-colors ${
                mode === 'realtime' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              Real-time
            </button>
          </div>
          <span className="text-xs text-gray-500">
            {mode === 'async'
              ? 'Get notified when it\'s your turn'
              : 'No turn notifications — all players at the board'
            }
          </span>
        </div>

        {/* Bot count */}
        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm font-medium text-gray-700">Bot opponents:</span>
          <div className="flex rounded border border-gray-300 overflow-hidden">
            {[0, 1, 2, 3].map((n) => (
              <button
                key={n}
                onClick={() => setBotCount(n)}
                className={`px-3 py-1.5 text-sm font-medium cursor-pointer transition-colors ${
                  botCount === n ? 'bg-purple-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                {n}
              </button>
            ))}
          </div>
          <span className="text-xs text-gray-500">
            {botCount > 0 ? `Play against ${botCount} bot${botCount > 1 ? 's' : ''}` : 'Human opponents only'}
          </span>
        </div>

        <div className="flex gap-4">
          <button
            onClick={() => handleCreateGame('simple_rail')}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 cursor-pointer"
          >
            Create Simple Rail Game
          </button>
          <button
            onClick={() => handleCreateGame('northern_pacific')}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer"
          >
            Create Northern Pacific Game
          </button>
        </div>
      </div>

      <div className="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Open Games</h2>
        <p className="text-gray-500">No open games available.</p>
      </div>
    </div>
  );
};
