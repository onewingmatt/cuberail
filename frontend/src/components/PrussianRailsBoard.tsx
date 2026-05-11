import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';
import { HexGridBoard } from './HexGridBoard';
import { PrussianRailsCalibrator } from './PrussianRailsCalibrator';

const getCurrentUserId = (): string | null => {
  const token = localStorage.getItem('token');
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split('.')[1])).sub || null;
  } catch {
    return null;
  }
};

const getUserName = (playerId: string, players: any[]): string => {
  const p = players?.find((pl: any) => pl.id === playerId);
  return p?.username || playerId.slice(0, 8);
};

export const PrussianRailsBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { sendMove } = useWebSocket(id || '', false);
  const [selectedHex, setSelectedHex] = useState<string | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [calibrationMode, setCalibrationMode] = useState(false);
  const [overlayTranslateX, setOverlayTranslateX] = useState(0);
  const [overlayTranslateY, setOverlayTranslateY] = useState(0);
  const [overlayScaleX, setOverlayScaleX] = useState(1);
  const [overlayScaleY, setOverlayScaleY] = useState(1);
  const [overlayRotation, setOverlayRotation] = useState(0);
  const [overlayOpacity, setOverlayOpacity] = useState(0.35);
  const [showOverlay, setShowOverlay] = useState(true);
  const historyEndRef = useRef<HTMLDivElement>(null);

  if (!gameState || !gameState.map_data) return null;

  const myUserId = getCurrentUserId();
  const isMyTurn = gameState.current_player === myUserId;
  const isAuctionPhase = gameState.phase === 'auction' && !gameState.round_phase;
  const players = (gameState as any).players || [];

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

  const handleAuctionShare = (companyId: string) => {
    sendMove('auction_share', { company: companyId });
  };

  const auction = gameState.auction_state;
  const companies = Object.values(gameState.companies || {}) as any[];
  const moveHistory: string[] = (gameState as any).move_history || [];

  useEffect(() => {
    if (historyOpen && historyEndRef.current) {
      historyEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [moveHistory.length, historyOpen]);

  const phaseLabel = gameState.phase === 'auction' && !gameState.round_phase ? 'Initial Auction' :
    gameState.phase === 'round' && gameState.auction_state ? 'Share Auction' :
    gameState.phase === 'round' ? `Round ${gameState.round_number || ''} — ${gameState.round_phase || ''}` :
    gameState.phase;

  const currentPlayerName = getUserName(gameState.current_player || '', players);

  return (
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-1">Prussian Rails</h2>
      <div className="mb-3 flex gap-2 flex-wrap items-center">
        <button
          onClick={() => setCalibrationMode(v => !v)}
          className={`px-3 py-1 rounded text-sm cursor-pointer ${calibrationMode ? 'bg-amber-600 text-white' : 'bg-slate-200 text-slate-900'}`}
        >
          {calibrationMode ? 'Exit calibration mode' : 'Enter calibration mode'}
        </button>
        <button
          onClick={() => setShowOverlay(v => !v)}
          className={`px-3 py-1 rounded text-sm cursor-pointer ${showOverlay ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-900'}`}
        >
          {showOverlay ? 'Hide logic overlay' : 'Show logic overlay'}
        </button>
        <span className="text-xs text-gray-600">Move/scale/rotate the overlay until it matches the board image. Logic stays in JSON underneath.</span>
      </div>

      {!calibrationMode && (
        <div className="mb-4 w-full max-w-6xl bg-white border rounded p-3 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 xl:grid-cols-7 gap-3 text-xs">
          <label className="flex flex-col gap-1">TX
            <input type="range" min={-300} max={300} step={0.5} value={overlayTranslateX} onChange={e => setOverlayTranslateX(Number(e.target.value))} />
            <input type="number" step={0.5} value={overlayTranslateX} onChange={e => setOverlayTranslateX(Number(e.target.value))} className="border rounded px-2 py-1" />
          </label>
          <label className="flex flex-col gap-1">TY
            <input type="range" min={-300} max={300} step={0.5} value={overlayTranslateY} onChange={e => setOverlayTranslateY(Number(e.target.value))} />
            <input type="number" step={0.5} value={overlayTranslateY} onChange={e => setOverlayTranslateY(Number(e.target.value))} className="border rounded px-2 py-1" />
          </label>
          <label className="flex flex-col gap-1">SX
            <input type="range" min={0.5} max={1.5} step={0.001} value={overlayScaleX} onChange={e => setOverlayScaleX(Number(e.target.value))} />
            <input type="number" step={0.001} value={overlayScaleX} onChange={e => setOverlayScaleX(Number(e.target.value))} className="border rounded px-2 py-1" />
          </label>
          <label className="flex flex-col gap-1">SY
            <input type="range" min={0.5} max={1.5} step={0.001} value={overlayScaleY} onChange={e => setOverlayScaleY(Number(e.target.value))} />
            <input type="number" step={0.001} value={overlayScaleY} onChange={e => setOverlayScaleY(Number(e.target.value))} className="border rounded px-2 py-1" />
          </label>
          <label className="flex flex-col gap-1">Rot
            <input type="range" min={-15} max={15} step={0.01} value={overlayRotation} onChange={e => setOverlayRotation(Number(e.target.value))} />
            <input type="number" step={0.01} value={overlayRotation} onChange={e => setOverlayRotation(Number(e.target.value))} className="border rounded px-2 py-1" />
          </label>
          <label className="flex flex-col gap-1">Opacity
            <input type="range" min={0} max={1} step={0.01} value={overlayOpacity} onChange={e => setOverlayOpacity(Number(e.target.value))} />
            <input type="number" min={0} max={1} step={0.01} value={overlayOpacity} onChange={e => setOverlayOpacity(Number(e.target.value))} className="border rounded px-2 py-1" />
          </label>
          <button
            onClick={() => {
              setOverlayTranslateX(0); setOverlayTranslateY(0); setOverlayScaleX(1); setOverlayScaleY(1); setOverlayRotation(0); setOverlayOpacity(0.35);
            }}
            className="px-3 py-2 rounded bg-slate-100 border cursor-pointer self-end"
          >
            Reset overlay
          </button>
        </div>
      )}

      {gameState.game_over && (
        <div className="bg-yellow-100 text-yellow-800 p-3 mb-3 rounded font-semibold">
          Game Over!
        </div>
      )}

      <div className="flex gap-4 w-full justify-center">
        {calibrationMode ? (
          <PrussianRailsCalibrator
            hexes={hexes}
            backgroundImage={mapData.background_image || null}
          />
        ) : (
          <>
        {/* Hex Map */}
        <HexGridBoard
          hexes={hexes}
          hexSize={mapData.hex_size || 40}
          boardData={boardDict}
          companies={gameState.companies || {}}
          onHexClick={isMyTurn && gameState.phase === 'round' && !gameState.auction_state ? handleHexClick : undefined}
          selectedHex={selectedHex}
          showTerrainLabels={false}
          minQ={mapData.grid_bounds?.q_min ?? 0}
          maxQ={mapData.grid_bounds?.q_max ?? 17}
          minR={mapData.grid_bounds?.r_min ?? 0}
          maxR={mapData.grid_bounds?.r_max ?? 17}
          backgroundImage={mapData.background_image || null}
          overlayTranslateX={overlayTranslateX}
          overlayTranslateY={overlayTranslateY}
          overlayScaleX={overlayScaleX}
          overlayScaleY={overlayScaleY}
          overlayRotation={overlayRotation}
          overlayOpacity={overlayOpacity}
          showOverlay={showOverlay}
        />

        {/* Sidebar */}
        <div className="w-72 flex flex-col gap-3">
          {/* Status */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="font-bold border-b pb-2 mb-2">Game Status</h3>
            <p className="text-sm"><span className="font-semibold">Phase:</span> <span className="capitalize">{phaseLabel}</span></p>
            <p className="text-sm">
              <span className="font-semibold">Turn:</span> {currentPlayerName}
              {isMyTurn && <span className="text-green-600 ml-1">(you)</span>}
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
                <p>Highest: {auction.highest_bidder ? getUserName(auction.highest_bidder, players) : 'None'}</p>
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
                      {c.id} ({c.track_remaining || '?'} left)
                    </option>
                  ))}
                </select>

                {selectedCompany && (
                  <div className="text-xs text-gray-600 space-y-0.5 bg-gray-50 p-2 rounded">
                    <p>Treasury: <span className="font-medium text-green-700">
                      ${(gameState as any).company_treasury?.[selectedCompany] || 0}</span>
                    </p>
                    <p>Income: <span className="font-medium">
                      {(gameState as any).company_income?.[selectedCompany] || 0}</span>
                    </p>
                  </div>
                )}

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

          {/* Share Auction button */}
          {gameState.phase === 'round' && !gameState.auction_state && isMyTurn && (
            <div className="bg-white p-4 rounded shadow border border-gray-200">
              <h3 className="font-bold border-b pb-2 mb-2">Actions</h3>
              <div className="flex gap-2">
                <button onClick={handlePass}
                  className="bg-gray-500 text-white px-3 py-1 rounded text-xs cursor-pointer hover:bg-gray-600">
                  Pass Turn
                </button>
              </div>
              <div className="mt-2">
                <p className="text-xs text-gray-500 mb-1">Auction a share:</p>
                <select
                  className="border rounded p-1 text-xs w-full"
                  onChange={(e) => { if (e.target.value) handleAuctionShare(e.target.value); }}
                  value=""
                >
                  <option value="">-- Select company --</option>
                  {companies.filter((c: any) => c.unissued_shares > 0).map((c: any) => (
                    <option key={c.id} value={c.id} style={{ color: c.color }}>
                      {c.id} ({c.unissued_shares} left)
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Players */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="font-bold border-b pb-2 mb-2">Players</h3>
            {Object.entries(gameState.player_cash || {}).map(([pId, cash]) => {
              const income = gameState.player_income?.[pId] || 0;
              const pName = getUserName(pId, players);
              const isCurrent = gameState.current_player === pId;
              return (
                <div key={pId} className={`mb-2 border-b border-gray-100 pb-1 ${isCurrent ? 'bg-blue-50 -mx-4 px-4' : ''}`}>
                  <div className="flex justify-between text-sm items-center font-medium">
                    <span>{pName} {isCurrent && '(current)'}</span>
                    <span className="text-green-600 font-mono">${cash as number}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Income: <span className="font-mono">${income}</span>
                  </div>
                  <div className="text-xs mt-0.5 flex flex-wrap gap-1">
                    {Object.entries(gameState.shares?.[pId] || {}).map(([cId, count]) => (
                      count ? (
                        <span key={cId} style={{
                          color: gameState.companies?.[cId]?.color || '#000',
                          background: (gameState.companies?.[cId]?.color || '#000') + '20',
                          padding: '0 4px',
                          borderRadius: 3,
                        }}>
                          {(gameState.companies as any)?.[cId]?.id?.slice(0, 3) || cId.slice(0, 3)} x{count as number}
                        </span>
                      ) : null
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Company State */}
          {!auction && (
            <div className="bg-white p-4 rounded shadow border border-gray-200">
              <h3 className="font-bold border-b pb-2 mb-2">Companies</h3>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {companies.map((c: any) => (
                  <div key={c.id} className="flex justify-between text-xs items-center">
                    <span style={{ color: c.color }} className="font-medium truncate max-w-[120px]">
                      {c.id}
                    </span>
                    <span className="text-gray-500">
                      ${(gameState as any).company_treasury?.[c.id] || 0} /
                      <span className="text-blue-600">{(gameState as any).company_income?.[c.id] || 0}i</span> /
                      {c.track_remaining || 0}t
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Move History */}
          <div className="bg-white rounded shadow border border-gray-200">
            <button
              onClick={() => setHistoryOpen(!historyOpen)}
              className="w-full text-left p-3 font-bold text-sm flex justify-between items-center cursor-pointer hover:bg-gray-50"
            >
              <span>Move History ({moveHistory.length})</span>
              <span className="text-xs text-gray-400">{historyOpen ? '▲' : '▼'}</span>
            </button>
            {historyOpen && (
              <div className="max-h-48 overflow-y-auto px-3 pb-3">
                {moveHistory.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No moves yet</p>
                ) : (
                  moveHistory.map((entry, i) => (
                    <div key={i} className="text-xs py-0.5 border-b border-gray-50 last:border-0">
                      {entry}
                    </div>
                  ))
                )}
                <div ref={historyEndRef} />
              </div>
            )}
          </div>
        </div>
          </>
        )}
      </div>
    </div>
  );
};
