import { useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import axios from 'axios';
import { useGameStore, useAuthStore } from '../store';

// Ensure we don't duplicate sockets if called multiple times
let globalSocket: Socket | null = null;

export const useWebSocket = (gameId: string, autoConnect = true) => {
  const { setGameState } = useGameStore();
  const { token, user } = useAuthStore();

  useEffect(() => {
    if (!gameId || !autoConnect) return;

    // Fetch initial state
    const fetchState = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/api/games/${gameId}/state`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        setGameState(response.data);
      } catch (err) {
        console.error('Failed to fetch initial game state', err);
      }
    };
    fetchState();

    if (!globalSocket) {
      globalSocket = io('http://localhost:8000');
    }

    globalSocket.on('connect', () => {
      console.log('Socket Connected');
      globalSocket?.emit('join_game', { game_id: gameId });
    });

    globalSocket.on('STATE_UPDATED', (data) => {
      if (data && data.payload) {
        setGameState(data.payload);
      }
    });

    return () => {
      // Don't disconnect on unmount if it's managed globally, but remove listeners to prevent duplicates
      globalSocket?.off('STATE_UPDATED');
      globalSocket?.off('connect');
    };
  }, [gameId, setGameState, token, autoConnect]);

  const sendMove = async (action_type: string, payload: any) => {
    if (!token || !user) return;
    try {
      await axios.post(
        `http://localhost:8000/api/games/${gameId}/moves`,
        { action_type, payload },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (err) {
      console.error('Failed to submit move:', err);
      alert('Move failed. Check turn order or validity.');
    }
  };

  return { sendMove };
};
