import React from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuthStore } from '../store';

export const Lobby: React.FC = () => {
  const navigate = useNavigate();
  const { user, token } = useAuthStore();

  const handleCreateGame = async (gameType: string) => {
    try {
      const response = await axios.post(`http://localhost:8000/api/games/?game_type=${gameType}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
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
        <div className="flex gap-4">
          <button
            onClick={() => handleCreateGame('simple_rail')}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Create Simple Rail Game
          </button>
          <button
            onClick={() => handleCreateGame('northern_pacific')}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
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
