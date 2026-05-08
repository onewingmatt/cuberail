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
