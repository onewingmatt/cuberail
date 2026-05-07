import { create } from 'zustand';

interface AuthState {
  token: string | null;
  user: any | null;
  setToken: (token: string) => void;
  setUser: (user: any) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: null,
  setToken: (token) => {
    localStorage.setItem('token', token);
    set({ token });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, user: null });
  },
}));

interface GameState {
  gameState: any | null;
  setGameState: (state: any) => void;
}

export const useGameStore = create<GameState>((set) => ({
  gameState: null,
  setGameState: (state) => set({ gameState: state }),
}));
