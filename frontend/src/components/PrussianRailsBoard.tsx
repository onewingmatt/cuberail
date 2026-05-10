import React, { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';
import { HexGridBoard } from './HexGridBoard';

// Decode JWT from localStorage to get current user ID.
const getCurrentUserId = (): string | null => {
  const token = localStorage.getItem('token');
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split('.')[1])).sub || null;
  } catch {
    return null;
  }
};

export const PrussianRailsBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { sendMove } = useWebSocket(id || '', false);
  const [selectedHex, setSelectedHex] = useState<string | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);

  if (!gameState || !gameState.map_data) return null;

  const myUserId = getCurrentUserId();
  const isMyTurn = gameState.current_player === myUserId;
  const isAuctionPhase = gameState.phase === 'initial_auction' || (gameState.phase === 'round' && gameState.auction_state);

  // Convert board (list of [key, companies]) to dict for hex renderer
  const boardDict: Record<string, string[]> = {};
  if (Array.isArray(gameState.board)) {
    for (const [key, companies] of gameState.board) {
      const colorList: string[] = [];
      for (const cid of (companies as string[])) {
        const comp = gameState.companies?.[cid];
        colorList.push(comp?.color || '#000');
      }
      boardDict[key as string] = colorList;
    }
  }

  const mapData = gameState.map_data;
  const hexes = mapData.hexes || {};

  const handleHexClick = useCallback((q: number, r: number) => {
    setSelectedHex(`${q},${r}`);
    // If in build phase with a company selected, auto-build
    if (selectedCompany && gameState.phase === 'round' && !gameState.auction_state) {
      sendMove('build_track', { hex_path: [[q, r]], company: selectedCompany });
      setSelectedHex(null);
    }
  }, [selectedCompany, gameState.phase, gameState.auction_state, sendMove]);

  const handleBuildTrack = () => {
    if (selectedHex && selectedCompany) {
      const [q, r] = selectedHex.split(',').map(Number);
      sendMove('build_track', { hex_path: [[q, r]], company: selectedCompany });
      setSelectedHex(null);
    }
  };

  const handleBid = (amount: number) => {
    sendMove('bid', { bid: amount });
  };

  const handlePass = () => {
    sendMove('pass', {});
  };

  const auction = gameState.auction_state;
  const companies = Object.values(gameState.companies || {}) as any[];

  const phaseLabel = gameState.phase === 'initial_auction' ? 'Initial Auction' :
    gameState.phase === 'round' && gameState.auction_state ? 'Share Auction' :
    gameState.phase === 'round' ? `Round ${gameState.round_number || ''} — ${gameState.round_phase || ''}` :
    gameState.phase;

  return (
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-1">Prussian Rails</h2>

      {gameState.game_over && (
        <div className="bg-red-100 text-red-800 p-3 mb-3 rounded">Game Over!</div>
      )}

      <div className="flex gap-4 w-full justify-center">
        {/* Hex Map */}
        <HexGridBoard
          hexes={hexes}
          hexSize={mapData.hex_size || 40}
          boardData={boardDict}
          companies={gameState.companies || {}}
          onHexClick={isMyTurn && gameState.phase === 'round' && !gameState.auction_state ? handleHexClick : undefined}
          selectedHex={selectedHex}
          showTerrainLabels={false}
        />

        {/* Sidebar */}
        <div className="w-64 flex flex-col gap-3">
          {/* Status */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="font-bold border-b pb-2 mb-2">Game Status</h3>
            <p className="text-sm"><span className="font-semibold">Phase:</span> <span className="capitalize">{phaseLabel}</span></p>
            <p className="text-sm">
              <span className="font-semibold">Turn:</span> {(() => {
                const cp = gameState.current_player;
                // Try to find player info
                return cp ? cp.slice(0, 8) : '—';
              })()}
            </p>
          </div>

          {/* Auction panel */}
          {auction && (
            <div className="bg-white p-4 rounded shadow border border-gray-200">
              <h3 className="font-bold border-b pb-2 mb-2">Auction</h3>
              <div className="text-sm space-y-1">
                <p>
                  Company: <span style={{ color: gameState.companies?.[auction.item]?.color }} className="font-medium">
                    {auction.item}
                  </span>
                </p>
                <p>Current Bid: ${auction.current_bid}</p>
                <p>Highest: {auction.highest_bidder ? auction.highest_bidder.slice(0, 8) : 'None'}</p>
              </div>
              {isMyTurn && (
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleBid(auction.current_bid + 1)}
                    className="bg-green-600 text-white px-2 py-1 rounded text-xs flex-1 cursor-pointer hover:bg-green-700"
                  >
                    Bid ${auction.current_bid + 1}
                  </button>
                  <button
                    onClick={handlePass}
                    className="bg-red-600 text-white px-2 py-1 rounded text-xs flex-1 cursor-pointer hover:bg-red-700"
                  >
                    Pass
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Build panel */}
          {gameState.phase === 'round' && !gameState.auction_state && (
            <div className="bg-white p-4 rounded shadow border border-gray-200">
              <h3 className="font-bold border-b pb-2 mb-2">Build Track</h3>
              <div className="flex flex-col gap-2">
                <select
                  className="border rounded p-1 text-sm"
                  onChange={(e) => setSelectedCompany(e.target.value)}
                  value={selectedCompany || ''}
                >
                  <option value="">-- Select Company --</option>
                  {companies.map((c: any) => (
                    <option key={c.id} value={c.id} style={{ color: c.color }}>
                      {c.id} ({c.track_remaining || '?'} cubes)
                    </option>
                  ))}
                </select>

                {selectedHex && selectedCompany ? (
                  <button
                    onClick={handleBuildTrack}
                    disabled={!isMyTurn}
                    className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-40 cursor-pointer"
                  >
                    Build in hex {selectedHex}
                  </button>
                ) : (
                  <p className="text-xs text-gray-500">
                    {selectedCompany ? 'Click a hex on the map.' : 'Select a company first.'}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Players */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="font-bold border-b pb-2 mb-2">Players</h3>
            {Object.entries(gameState.player_cash || {}).map(([pId, cash]) => {
              const income = gameState.player_income?.[pId] || 0;
              return (
                <div key={pId} className="mb-2 border-b border-gray-100 pb-1">
                  <div className="flex justify-between text-sm items-center font-medium">
                    <span>{pId.slice(0, 8)}</span>
                    <span className="text-green-600">${cash as number}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Income: ${income}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5 flex flex-wrap gap-1">
                    {Object.entries(gameState.shares?.[pId] || {}).map(([cId, count]) => (
                      count ? <span key={cId} style={{ color: gameState.companies?.[cId]?.color }}>
                        {cId.slice(0, 6)}:{count as number}
                      </span> : null
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
