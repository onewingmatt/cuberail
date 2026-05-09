import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';
import { InteractiveMapBoard } from './InteractiveMapBoard';

// Decode JWT from localStorage to get current user ID.
// The token's `sub` claim is the user UUID — more reliable than Zustand store
// which resets on navigation/reload.
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
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);

  if (!gameState || !gameState.map_data) return null;

  const myUserId = getCurrentUserId();
  const isMyTurn = gameState.current_player === myUserId;
  const isAuctionPhase = gameState.phase === 'auction';

  const handleCityClick = (city: string) => {
    setSelectedCity(city);
  };

  const handleBuildTrack = () => {
    if (selectedCity && selectedCompany) {
      sendMove('build_track', { city: selectedCity, company: selectedCompany });
      setSelectedCity(null);
    }
  };

  const handleBid = (amount: number) => {
    sendMove('bid', { bid: amount });
  };

  const handlePass = () => {
    sendMove('pass', {});
  };

  const renderNode = (city: string, node: any, px: { x: number, y: number }) => {
    const isSelected = selectedCity === city;
    const tracks = gameState.board?.[city] || [];

    return (
      <g key={city} onClick={() => handleCityClick(city)} style={{ cursor: 'pointer' }}>
        <circle
          cx={px.x}
          cy={px.y}
          r={12}
          fill="#f3f4f6"
          stroke={isSelected ? '#ef4444' : '#374151'}
          strokeWidth={isSelected ? 3 : 2}
        />

        {/* Render little cubes for track */}
        {tracks.map((companyId: string, idx: number) => {
          const comp = gameState.companies?.[companyId];
          const color = comp ? comp.color : '#000';
          return (
            <rect
              key={idx}
              x={px.x - 10 + (idx * 6)}
              y={px.y + 4}
              width={6}
              height={6}
              fill={color}
              stroke="#fff"
              strokeWidth={0.5}
            />
          );
        })}

        <text
          x={px.x}
          y={px.y - 16}
          textAnchor="middle"
          fontSize={12}
          fontWeight="bold"
          fill="#111827"
          style={{ userSelect: 'none', pointerEvents: 'none' }}
        >
          {node.label}
        </text>
      </g>
    );
  };

  return (
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-2">Prussian Rails: {id}</h2>

      {gameState.game_over && (
        <div className="bg-red-100 text-red-800 p-3 mb-3 rounded">Game Over!</div>
      )}

      <div className="flex gap-4 w-full justify-center">
        {/* Main Map */}
        <div className="relative">
          <InteractiveMapBoard
            boardWidth={gameState.map_data.board_width}
            boardHeight={gameState.map_data.board_height}
            backgroundImage={gameState.map_data.background_image}
            nodes={gameState.map_data.nodes}
            edges={gameState.map_data.edges}
            renderNode={renderNode}
          />
        </div>

        {/* Sidebar Controls */}
        <div className="w-64 flex flex-col gap-3">
          {/* Phase & Turn info */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="font-bold border-b pb-2 mb-2">Game Status</h3>
            <p className="text-sm"><span className="font-semibold">Phase:</span> <span className="capitalize">{gameState.phase}</span></p>
            <p className="text-sm">
              <span className="font-semibold">Turn:</span> {gameState.current_player}
            </p>
            {isAuctionPhase && gameState.auction_state && (
              <div className="mt-3 p-2 bg-blue-50 rounded text-sm">
                <p className="font-bold">Active Auction</p>
                <p>Company: <span style={{color: gameState.companies[gameState.auction_state.item]?.color}}>{gameState.auction_state.item}</span></p>
                <p>Current Bid: ${gameState.auction_state.current_bid}</p>
                <p>Highest Bidder: {gameState.auction_state.highest_bidder || 'None'}</p>

                {isMyTurn && (
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => handleBid(gameState.auction_state.current_bid + 1)} className="bg-green-600 text-white px-2 py-1 rounded text-xs flex-1 cursor-pointer hover:bg-green-700">Bid ${gameState.auction_state.current_bid + 1}</button>
                    <button onClick={handlePass} className="bg-red-600 text-white px-2 py-1 rounded text-xs flex-1 cursor-pointer hover:bg-red-700">Pass</button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Panel */}
          {gameState.phase === 'main' && (
            <div className="bg-white p-4 rounded shadow border border-gray-200">
              <h3 className="font-bold border-b pb-2 mb-2">Actions</h3>
              <div className="flex flex-col gap-2">
                <p className="text-xs text-gray-500 mb-1">Select a company and a city to build track.</p>
                <select
                  className="border rounded p-1 text-sm"
                  onChange={(e) => setSelectedCompany(e.target.value)}
                  value={selectedCompany || ''}
                >
                  <option value="">-- Select Company --</option>
                  {Object.values(gameState.companies || {}).map((c: any) => (
                    <option key={c.id} value={c.id}>{c.id}</option>
                  ))}
                </select>

                {selectedCity && selectedCompany ? (
                  <button
                    onClick={handleBuildTrack}
                    disabled={!isMyTurn}
                    className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-40 cursor-pointer"
                  >
                    Build in {selectedCity}
                  </button>
                ) : (
                  <button disabled className="bg-gray-300 text-white px-3 py-1 rounded text-sm opacity-50">Build Track</button>
                )}
              </div>
            </div>
          )}

          {/* Player info */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="font-bold border-b pb-2 mb-2">Players</h3>
            {Object.entries(gameState.balances || {}).map(([pId, bal]) => (
              <div key={pId} className="mb-2 border-b border-gray-100 pb-1">
                <div className="flex justify-between text-sm items-center font-medium">
                  <span>{pId.slice(0, 8)}</span>
                  <span className="text-green-600">${bal as number}</span>
                </div>
                <div className="text-xs text-gray-500 mt-1 flex flex-wrap gap-1">
                  {Object.entries(gameState.shares?.[pId] || {}).map(([cId, count]) => (
                    count ? <span key={cId} style={{color: gameState.companies[cId]?.color}}>{cId.slice(0,3)}:{count as number}</span> : null
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
