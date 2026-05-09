import { useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import axios from 'axios';
import { useGameStore, useAuthStore } from '../store';
import { API_BASE, WS_URL } from '../config';

// Ensure we don't duplicate sockets if called multiple times
let globalSocket: Socket | null = null;

export const useWebSocket = (gameId: string, autoConnect = true) => {
  const { setGameState } = useGameStore();
  const { token } = useAuthStore();

  useEffect(() => {
    if (!gameId || !autoConnect) return;

    // Fetch initial state
    const fetchState = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/games/${gameId}/state`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        setGameState(response.data);
      } catch (err) {
        console.error('Failed to fetch initial game state', err);
      }
    };
    fetchState();

    if (!globalSocket) {
      globalSocket = io(WS_URL);
    }

    globalSocket.on('connect', () => {
      console.log('Socket Connected');
      globalSocket?.emit('join_game', { game_id: gameId });
    });

    globalSocket.on('STATE_UPDATED', (data) => {
      if (data && data.payload) {
        // WS payload doesn't include game_type/players — preserve from current state
        const currentState = useGameStore.getState().gameState;
        setGameState({
          ...data.payload,
          game_type: currentState?.game_type || data.payload.game_type,
          players: currentState?.players || data.payload.players,
        });
      }
    });

    return () => {
      globalSocket?.off('STATE_UPDATED');
      globalSocket?.off('connect');
    };
  }, [gameId, setGameState, token, autoConnect]);

  const sendMove = async (action_type: string, payload: any) => {
    if (!token) return;
    try {
      await axios.post(
        `${API_BASE}/api/games/${gameId}/moves`,
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
