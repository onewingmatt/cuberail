import { describe, it, expect } from 'vitest';

function validateMove(state: any, actionType: string, payload: any, playerId: string) {
  if (state.current_player !== playerId) {
    return { valid: false, error: 'Not your turn' };
  }

  if (actionType === 'place_track') {
    const hex = payload.hex;
    if (state.board && state.board[hex]) {
      return { valid: false, error: 'Hex already occupied' };
    }
  }
  return { valid: true };
}

describe('Frontend Move Validation', () => {
  const mockState = {
    current_player: 'player-1',
    board: { '0,0': 'Red' },
    shares: {},
    game_over: false,
  };

  it('validates a correct move', () => {
    const result = validateMove(mockState, 'place_track', { hex: '1,1', company: 'Red' }, 'player-1');
    expect(result.valid).toBe(true);
  });

  it('rejects move out of turn', () => {
    const result = validateMove(mockState, 'place_track', { hex: '1,1', company: 'Red' }, 'player-2');
    expect(result.valid).toBe(false);
    expect(result.error).toBe('Not your turn');
  });

  it('rejects move on occupied hex', () => {
    const result = validateMove(mockState, 'place_track', { hex: '0,0', company: 'Blue' }, 'player-1');
    expect(result.valid).toBe(false);
    expect(result.error).toBe('Hex already occupied');
  });
});
