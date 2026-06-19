import { create } from 'zustand';

interface AuthState {
  token: string | null;
  user: any | null;
  setToken: (token: string) => void;
  setUser: (user: any) => void;
  logout: () => void;
}

// Decode user ID from JWT payload (no signature verification, client-side only)
function decodeUserIdFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub || null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => {
  const token = localStorage.getItem('token');
  let user = JSON.parse(localStorage.getItem('user') || 'null');
  // Fallback: if token exists but user wasn't persisted, decode ID from JWT
  if (!user && token) {
    const uid = decodeUserIdFromToken(token);
    if (uid) user = { id: uid };
  }
  return {
    token,
    user,
    setToken: (token) => {
      localStorage.setItem('token', token);
      set({ token });
    },
    setUser: (user) => {
      localStorage.setItem('user', JSON.stringify(user));
      set({ user });
    },
    logout: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      set({ token: null, user: null });
    },
  };
});

interface GameState {
  gameState: any | null;
  setGameState: (state: any) => void;
}

export const useGameStore = create<GameState>((set) => ({
  gameState: null,
  setGameState: (state) => set({ gameState: state }),
}));

interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  game_id: string | null;
  read: boolean;
  created_at: string;
}

interface NotifStore {
  items: NotificationItem[];
  unreadCount: number;
  setItems: (items: NotificationItem[]) => void;
  setUnreadCount: (n: number) => void;
  addItem: (item: NotificationItem) => void;
  markOneRead: (id: string) => void;
  markAllRead: () => void;
}

export const useNotifStore = create<NotifStore>((set) => ({
  items: [],
  unreadCount: 0,
  setItems: (items) => set({ items, unreadCount: items.filter(i => !i.read).length }),
  setUnreadCount: (n) => set({ unreadCount: n }),
  addItem: (item) => set((s) => ({ items: [item, ...s.items], unreadCount: s.unreadCount + (item.read ? 0 : 1) })),
  markOneRead: (id) => set((s) => ({
    items: s.items.map(i => i.id === id ? { ...i, read: true } : i),
    unreadCount: Math.max(0, s.unreadCount - 1),
  })),
  markAllRead: () => set((s) => ({
    items: s.items.map(i => ({ ...i, read: true })),
    unreadCount: 0,
  })),
}));
