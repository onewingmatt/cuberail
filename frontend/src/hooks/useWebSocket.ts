import { useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import axios from 'axios';
import { useGameStore, useAuthStore } from '../store';

export const useWebSocket = (gameId: string) => {
  const socket = useRef<Socket | null>(null);
  const { setGameState } = useGameStore();
  const { token, user } = useAuthStore();

  useEffect(() => {
    if (!gameId) return;

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

    socket.current = io('http://localhost:8000');

    socket.current.on('connect', () => {
      console.log('Socket Connected');
      socket.current?.emit('join_game', { game_id: gameId });
    });

    socket.current.on('STATE_UPDATED', (data) => {
      if (data && data.payload) {
        setGameState(data.payload);
      }
    });

    return () => {
      socket.current?.disconnect();
    };
  }, [gameId, setGameState, token]);

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
