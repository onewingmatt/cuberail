import axios from 'axios';

const API = 'http://localhost:8000/api';

function headers(token: string | null) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchNotifications(token: string, limit = 20, unreadOnly = false) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (unreadOnly) params.set('unread_only', 'true');
  const res = await axios.get(`${API}/notifications?${params}`, { headers: headers(token) });
  return res.data;
}

export async function fetchUnreadCount(token: string) {
  const res = await axios.get(`${API}/notifications/unread-count`, { headers: headers(token) });
  return res.data.count;
}

export async function markRead(token: string, notifId: string) {
  await axios.post(`${API}/notifications/${notifId}/read`, {}, { headers: headers(token) });
}

export async function markAllRead(token: string) {
  await axios.post(`${API}/notifications/read-all`, {}, { headers: headers(token) });
}

export async function fetchNotificationPrefs(token: string) {
  const res = await axios.get(`${API}/notifications/preferences`, { headers: headers(token) });
  return res.data;
}

export async function updateNotificationPrefs(token: string, prefs: Record<string, boolean>) {
  await axios.put(`${API}/notifications/preferences`, { notification_preferences: prefs }, { headers: headers(token) });
}
