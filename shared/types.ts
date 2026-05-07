export interface User {
  id: string;
  username: string;
  email: string;
}

export interface Game {
  id: string;
  game_type: string;
  status: 'waiting' | 'in_progress' | 'completed';
  created_by_id: string;
}

export interface GamePlayer {
  game_id: string;
  user_id: string;
  player_index: number;
}

export interface MovePayload {
  hex?: string;
  company?: string;
  [key: string]: any;
}

export interface GameMove {
  id: string;
  game_id: string;
  user_id: string;
  move_number: number;
  action_type: 'place_track' | 'buy_share' | 'pass';
  payload: MovePayload;
}

export interface GameState {
  current_player: string;
  board?: Record<string, string>; // Simple Rail
  shares?: Record<string, Record<string, number>>; // Simple Rail

  train_pos?: string; // Northern Pacific
  investments?: Record<string, string>; // Northern Pacific
  balances?: Record<string, number>; // Northern Pacific
  graph?: Record<string, string[]>; // Northern Pacific

  game_over: boolean;
}

export interface WebSocketMessage {
  type: 'STATE_UPDATED' | 'MOVE_ACCEPTED' | 'ERROR';
  payload: any;
}
