import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store';
import { fetchNotificationPrefs, updateNotificationPrefs } from '../api/notifications';

const LABELS: Record<string, string> = {
  game_invite: 'Game invites',
  game_started: 'Game started',
  your_turn: 'Your turn',
  game_over: 'Game over',
  player_joined: 'Player joined your game',
};

const DESCRIPTIONS: Record<string, string> = {
  game_invite: 'When someone invites you to play',
  game_started: 'When a game you joined begins',
  your_turn: 'When an opponent moves in async mode',
  game_over: 'When a game ends with final scores',
  player_joined: 'When someone joins your game',
};

export const NotificationPreferences: React.FC = () => {
  const { token } = useAuthStore();
  const [prefs, setPrefs] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!token) return;
    fetchNotificationPrefs(token).then(setPrefs).catch(() => {});
  }, [token]);

  const toggle = (key: string) => {
    setSaved(false);
    setPrefs((p) => ({ ...p, [key]: !p[key] }));
  };

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    await updateNotificationPrefs(token, prefs).catch(() => {});
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-2">Notification Preferences</h1>
      <p className="text-sm text-gray-600 mb-6">
        Choose which events send you notifications and emails. Turn off notifications for games set to "realtime."
      </p>

      <div className="bg-white rounded-lg shadow divide-y divide-gray-100">
        {Object.keys(LABELS).map((key) => (
          <div key={key} className="flex items-center justify-between px-4 py-4">
            <div>
              <p className="text-sm font-medium text-gray-900">{LABELS[key]}</p>
              <p className="text-xs text-gray-500">{DESCRIPTIONS[key]}</p>
            </div>
            <button
              onClick={() => toggle(key)}
              className={`relative w-11 h-6 rounded-full transition-colors cursor-pointer ${prefs[key] ? 'bg-blue-600' : 'bg-gray-300'}`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${prefs[key] ? 'translate-x-5' : ''}`}
              />
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-4 bg-blue-600 text-white px-6 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-40 cursor-pointer"
      >
        {saving ? 'Saving...' : 'Save Preferences'}
      </button>

      {saved && <span className="ml-3 text-sm text-green-600">Saved!</span>}
    </div>
  );
};
