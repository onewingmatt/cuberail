import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore, useAuthStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';

// City positions as percentages of the board image (1410 x 572)
const CITY_POSITIONS: Record<string, { pct_x: number; pct_y: number }> = {
  "Vancouver":    { pct_x: 0.078, pct_y: 0.069 },
  "Seattle":      { pct_x: 0.078, pct_y: 0.284 },
  "Portland":     { pct_x: 0.046, pct_y: 0.519 },
  "Oroville":     { pct_x: 0.166, pct_y: 0.171 },
  "Spokane":      { pct_x: 0.209, pct_y: 0.336 },
  "Richland":     { pct_x: 0.139, pct_y: 0.493 },
  "BonnersFerry": { pct_x: 0.268, pct_y: 0.189 },
  "Shelby":       { pct_x: 0.360, pct_y: 0.211 },
  "Chinook":      { pct_x: 0.455, pct_y: 0.216 },
  "GreatFalls":   { pct_x: 0.399, pct_y: 0.383 },
  "Lewiston":     { pct_x: 0.237, pct_y: 0.502 },
  "Butte":        { pct_x: 0.353, pct_y: 0.556 },
  "Glasgow":      { pct_x: 0.552, pct_y: 0.227 },
  "Terry":        { pct_x: 0.587, pct_y: 0.403 },
  "Billings":     { pct_x: 0.479, pct_y: 0.543 },
  "Casper":       { pct_x: 0.536, pct_y: 0.812 },
  "Minot":        { pct_x: 0.682, pct_y: 0.199 },
  "Bismarck":     { pct_x: 0.701, pct_y: 0.387 },
  "RapidCity":    { pct_x: 0.636, pct_y: 0.678 },
  "GrandForks":   { pct_x: 0.804, pct_y: 0.160 },
  "Fargo":        { pct_x: 0.820, pct_y: 0.349 },
  "Aberdeen":     { pct_x: 0.776, pct_y: 0.524 },
  "Duluth":       { pct_x: 0.951, pct_y: 0.259 },
  "SiouxFalls":   { pct_x: 0.838, pct_y: 0.691 },
  "StPaul":       { pct_x: 0.946, pct_y: 0.487 },
};

// All 49 track segments with source/target for rendering
const ALL_SEGMENTS: { id: string; source: string; target: string }[] = [
  { id: "t01", source: "StPaul", target: "Duluth" },
  { id: "t02", source: "StPaul", target: "Fargo" },
  { id: "t03", source: "StPaul", target: "Aberdeen" },
  { id: "t04", source: "StPaul", target: "SiouxFalls" },
  { id: "t05", source: "Duluth", target: "GrandForks" },
  { id: "t06", source: "Duluth", target: "Fargo" },
  { id: "t07", source: "GrandForks", target: "Minot" },
  { id: "t08", source: "Fargo", target: "GrandForks" },
  { id: "t09", source: "GrandForks", target: "Fargo" },
  { id: "t10", source: "Fargo", target: "Minot" },
  { id: "t11", source: "Fargo", target: "Bismarck" },
  { id: "t12", source: "SiouxFalls", target: "Aberdeen" },
  { id: "t13", source: "SiouxFalls", target: "RapidCity" },
  { id: "t14", source: "Aberdeen", target: "Bismarck" },
  { id: "t15", source: "Aberdeen", target: "RapidCity" },
  { id: "t16", source: "Minot", target: "Glasgow" },
  { id: "t17", source: "Minot", target: "Bismarck" },
  { id: "t18", source: "Bismarck", target: "Terry" },
  { id: "t19", source: "RapidCity", target: "Terry" },
  { id: "t20", source: "RapidCity", target: "Billings" },
  { id: "t21", source: "RapidCity", target: "Casper" },
  { id: "t22", source: "Terry", target: "Glasgow" },
  { id: "t23", source: "Terry", target: "GreatFalls" },
  { id: "t24", source: "Terry", target: "Billings" },
  { id: "t25", source: "Glasgow", target: "Chinook" },
  { id: "t26", source: "Glasgow", target: "Terry" },
  { id: "t27", source: "Casper", target: "Billings" },
  { id: "t28", source: "Casper", target: "Butte" },
  { id: "t29", source: "Billings", target: "GreatFalls" },
  { id: "t30", source: "Billings", target: "Butte" },
  { id: "t31", source: "Chinook", target: "Shelby" },
  { id: "t32", source: "Chinook", target: "GreatFalls" },
  { id: "t33", source: "Shelby", target: "BonnersFerry" },
  { id: "t34", source: "Shelby", target: "GreatFalls" },
  { id: "t35", source: "GreatFalls", target: "Lewiston" },
  { id: "t36", source: "GreatFalls", target: "Butte" },
  { id: "t37", source: "Butte", target: "Lewiston" },
  { id: "t38", source: "Lewiston", target: "Spokane" },
  { id: "t39", source: "Lewiston", target: "Richland" },
  { id: "t40", source: "BonnersFerry", target: "Oroville" },
  { id: "t41", source: "BonnersFerry", target: "Spokane" },
  { id: "t42", source: "BonnersFerry", target: "Lewiston" },
  { id: "t43", source: "Oroville", target: "Vancouver" },
  { id: "t44", source: "Oroville", target: "Spokane" },
  { id: "t45", source: "Spokane", target: "Richland" },
  { id: "t46", source: "Vancouver", target: "Seattle" },
  { id: "t47", source: "Vancouver", target: "Portland" },
  { id: "t48", source: "Richland", target: "Seattle" },
  { id: "t49", source: "Richland", target: "Portland" },
];

const BOARD_W = 1410;
const BOARD_H = 572;
const DISPLAY_W = 900;
const DISPLAY_H = Math.round(BOARD_H * (DISPLAY_W / BOARD_W));

const MIN_SCALE = 0.5;
const MAX_SCALE = 4;

const PLAYER_COLORS = [
  '#ef4444', '#3b82f6', '#22c55e', '#f59e0b',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
];

function getPlayerColor(playerId: string, players: any[] | undefined): string {
  if (!players) return '#4f46e5';
  const idx = players.findIndex((p: any) => p.id === playerId);
  return idx >= 0 ? PLAYER_COLORS[idx % PLAYER_COLORS.length] : '#4f46e5';
}

function pctToPx(pct_x: number, pct_y: number) {
  return { x: pct_x * DISPLAY_W, y: pct_y * DISPLAY_H };
}

function renderSegmentPath(
  seg: { source: string; target: string },
  offset_px: number
): string {
  const a = CITY_POSITIONS[seg.source];
  const b = CITY_POSITIONS[seg.target];
  if (!a || !b) return '';
  const aPx = pctToPx(a.pct_x, a.pct_y);
  const bPx = pctToPx(b.pct_x, b.pct_y);
  const mx = (aPx.x + bPx.x) / 2;
  const my = (aPx.y + bPx.y) / 2;
  const dx = bPx.x - aPx.x;
  const dy = bPx.y - aPx.y;
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) return '';
  return `M ${aPx.x} ${aPx.y} Q ${mx + (dy / len) * offset_px} ${my - (dx / len) * offset_px} ${bPx.x} ${bPx.y}`;
}

export const NorthernPacificBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { user } = useAuthStore();
  const { sendMove } = useWebSocket(id || '', false);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [useEnhanced, setUseEnhanced] = useState(false);

  // Pan & zoom
  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [isPanning, setIsPanning] = useState(false);
  const [hasMoved, setHasMoved] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetAtPanStart = useRef({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  const resetView = useCallback(() => { setScale(1); setOffsetX(0); setOffsetY(0); }, []);
  const zoomIn = useCallback(() => setScale(s => Math.min(MAX_SCALE, s * 1.3)), []);
  const zoomOut = useCallback(() => setScale(s => Math.max(MIN_SCALE, s / 1.3)), []);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.85 : 1.18;
      const rect = svg.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      setScale(prev => {
        const ns = Math.max(MIN_SCALE, Math.min(MAX_SCALE, prev * delta));
        const r = ns / prev;
        setOffsetX(ox => cx - r * (cx - ox));
        setOffsetY(oy => cy - r * (cy - oy));
        return ns;
      });
    };
    svg.addEventListener('wheel', onWheel, { passive: false });
    return () => svg.removeEventListener('wheel', onWheel);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    panStart.current = { x: e.clientX, y: e.clientY };
    offsetAtPanStart.current = { x: offsetX, y: offsetY };
    setHasMoved(false);
    setIsPanning(true);
  }, [offsetX, offsetY]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning) return;
    const dx = e.clientX - panStart.current.x;
    const dy = e.clientY - panStart.current.y;
    if (Math.sqrt(dx * dx + dy * dy) > 3) setHasMoved(true);
    setOffsetX(offsetAtPanStart.current.x + dx);
    setOffsetY(offsetAtPanStart.current.y + dy);
  }, [isPanning]);

  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  // --- CityActions sub-component ---
  const CityActions: React.FC<{
    city: string;
    isReachable: boolean;
    isInvestable: boolean;
    hasStd: boolean;
    hasEnh: boolean;
    onLayTrack: () => void;
    onInvest: (enhanced: boolean) => void;
    onCancel: () => void;
  }> = ({ city, isReachable, isInvestable, hasStd, hasEnh, onLayTrack, onInvest, onCancel }) => {
    const label = city.replace(/([A-Z])/g, ' $1').trim();
    const cityCubes = gameState?.city_cubes || {};
    const cityEnh = gameState?.city_enhanced || {};
    const stdCount = cityCubes[city]?.[user?.id || ''] || 0;
    const enhCount = cityEnh[city]?.[user?.id || ''] || 0;
    const hasMyCubes = stdCount > 0 || enhCount > 0;

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-base font-bold">{label}</h4>
          <button onClick={onCancel} className="text-gray-400 hover:text-gray-600 text-sm">X</button>
        </div>
        <p className="text-xs text-gray-500">
          {isReachable && isInvestable ? 'You can lay track here or invest.' :
           isReachable ? 'You can lay track here.' :
           isInvestable ? 'You can invest here.' : 'No actions available for this city.'}
        </p>

        <div className="flex flex-wrap gap-2">
          {isReachable && (
            <button
              onClick={onLayTrack}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm font-medium"
            >
              Lay Track
            </button>
          )}
          {isInvestable && hasStd && (
            <button
              onClick={() => onInvest(false)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium"
            >
              Invest Cube
            </button>
          )}
          {isInvestable && hasEnh && (
            <button
              onClick={() => onInvest(true)}
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded text-sm font-medium"
            >
              Invest Enhanced
            </button>
          )}
        </div>

        {hasMyCubes && (
          <p className="text-xs text-gray-500">You have {stdCount + enhCount} cube{stdCount + enhCount > 1 ? 's' : ''} here.</p>
        )}
      </div>
    );
  };

  if (!gameState) return null;

  const socket = (window as any).__socket;
  const handleCityClick = (city: string) => {
    if (hasMoved) return;
    setSelectedCity(city);
    setSelectedSegment(null);
  };
  const handleSegmentClick = (segId: string) => {
    if (hasMoved) return;
    setSelectedSegment(segId);
    setSelectedCity(null);
  };
  const handleInvest = () => {
    if (selectedCity) {
      sendMove('invest', { city: selectedCity, enhanced: useEnhanced });
      setSelectedCity(null);
    }
  };
  const handleLayTrack = () => {
    if (selectedSegment) {
      sendMove('lay_track', { segment_id: selectedSegment });
      setSelectedSegment(null);
    }
  };

  const isMyTurn = gameState.current_player === user?.id;
  const playerSupply = gameState.player_supply || {};
  const playerEnhanced = gameState.player_enhanced || {};
  const cityCubes = gameState.city_cubes || {};
  const cityEnhanced = gameState.city_enhanced || {};
  const cumulativeGood = gameState.cumulative_good || {};
  const laidTracks: string[] = gameState.laid_tracks || [];
  const availableTracks: { segment_id: string; source: string; target: string }[] = gameState.available_tracks || [];
  const availableInvestCities: string[] = gameState.available_invest_cities || [];
  const trainEndpoint: string = gameState.train_endpoint || 'StPaul';

  // Set of laid segment IDs for quick lookup
  const laidSet = new Set(laidTracks);
  const availableSet = new Map(availableTracks.map(t => [t.segment_id, t]));

  // Render track segments
  const trackElements: React.ReactNode[] = ALL_SEGMENTS.map(seg => {
    const a = CITY_POSITIONS[seg.source];
    const b = CITY_POSITIONS[seg.target];
    if (!a || !b) return null;

    const isLaid = laidSet.has(seg.id);
    const isAvailable = availableSet.has(seg.id);
    const isSelected = selectedSegment === seg.id;

    const offset = 4; // slight curve for visual clarity

    let stroke = '#d1d5db'; // default light gray
    let strokeWidth = 1.5;
    let opacity = 0.4;
    let dash = '';
    let cursor = 'default';

    if (isLaid) {
      stroke = '#5c3d2e'; // brown for laid tracks
      strokeWidth = 3;
      opacity = 0.9;
    } else if (isAvailable) {
      stroke = '#22c55e'; // green for available
      strokeWidth = 2.5;
      opacity = 0.7;
      dash = '5,3';
      cursor = 'pointer';
    } else {
      // Not laid and not available — show faintly
      strokeWidth = 1;
      opacity = 0.25;
    }

    if (isSelected) {
      stroke = '#ef4444'; // red highlight
      strokeWidth = 3.5;
      opacity = 1;
    }

    return (
      <path
        key={seg.id}
        d={renderSegmentPath(seg, offset)}
        stroke={stroke}
        strokeWidth={strokeWidth}
        fill="none"
        opacity={opacity}
        strokeDasharray={dash}
        style={{ cursor, transition: 'stroke 0.15s, opacity 0.15s' }}
        onClick={() => handleSegmentClick(seg.id)}
      />
    );
  });

  // Render city nodes
  const cityElements: React.ReactNode[] = Object.entries(CITY_POSITIONS).map(([city, pos]) => {
    const px = pctToPx(pos.pct_x, pos.pct_y);
    const isSelected = selectedCity === city;
    const isEndpoint = trainEndpoint === city;
    const canInvest = availableInvestCities.includes(city);
    const canReach = !!(gameState.available_tracks || []).find((t: any) => t.target === city);
    const isClickable = canInvest || canReach;

    // Determine stroke color
    let strokeColor = '#999';
    if (isEndpoint) strokeColor = '#dc2626';
    else if (isSelected) strokeColor = '#ef4444';
    else if (canReach) strokeColor = '#dc2626'; // red for reachable by track
    else if (canInvest) strokeColor = '#22c55e'; // green for investable

    // Count cubes in this city
    const stdCubes = cityCubes[city] || {};
    const enhCubes = cityEnhanced[city] || {};
    const totalCubes = Object.values(stdCubes).reduce((a: number, b: number) => a + b, 0)
      + Object.values(enhCubes).reduce((a: number, b: number) => a + b, 0);
    const isAtCapacity = totalCubes >= (gameState.city_capacity || 3);

    const label = city.replace(/([A-Z])/g, ' $1').trim();

    // Build cube indicators
    const cubeDots: React.ReactNode[] = [];
    let dotIdx = 0;

    // Collect all players' cubes
    const allPlayersWithCubes: { playerId: string; count: number; isEnhanced: boolean }[] = [];
    for (const [pid, count] of Object.entries(stdCubes)) {
      allPlayersWithCubes.push({ playerId: pid, count: count as number, isEnhanced: false });
    }
    for (const [pid, count] of Object.entries(enhCubes)) {
      allPlayersWithCubes.push({ playerId: pid, count: count as number, isEnhanced: true });
    }

    // Render colored dots for each investor
    allPlayersWithCubes.forEach((inv, idx) => {
      const dotColor = getPlayerColor(inv.playerId, gameState.players);
      const dotX = px.x - 8 + idx * 7;
      // Show a small circle per cube (up to 3 dots, then +N)
      const showCount = Math.min(inv.count, 3);
      for (let c = 0; c < showCount; c++) {
        cubeDots.push(
          <circle
            key={`dot-${city}-${inv.playerId}-${c}`}
            cx={dotX + c * 5}
            cy={px.y + 15}
            r={3}
            fill={dotColor}
            stroke="#fff"
            strokeWidth={0.5}
          />
        );
        dotIdx++;
      }
      if (inv.count > 3) {
        cubeDots.push(
          <text key={`more-${city}-${inv.playerId}`}
            x={dotX + 12}
            y={px.y + 18}
            fontSize={6}
            fill="#666"
          >+{inv.count - 3}</text>
        );
      }
    });

    return (
      <g key={city}>
        {/* Train endpoint indicator */}
        {isEndpoint && (
          <circle cx={px.x} cy={px.y} r={13} fill="#dc2626" stroke="#fff" strokeWidth={2.5} opacity={0.85} />
        )}
        {/* City circle */}
        <circle
          cx={px.x}
          cy={px.y}
          r={9}
          fill={isEndpoint ? '#fee2e2' : '#fff'}
          stroke={strokeColor}
          strokeWidth={isSelected ? 3 : (isClickable ? 2.5 : 1.5)}
          opacity={isAtCapacity ? 0.5 : 0.9}
          style={{ cursor: isClickable ? 'pointer' : 'default' }}
          onClick={() => isClickable && handleCityClick(city)}
        />
        {/* City label */}
        <text
          x={px.x}
          y={px.y - 14}
          textAnchor="middle"
          fontSize={9}
          fontWeight={isEndpoint ? 'bold' : 'normal'}
          fill="#1a1a1a"
          style={{ userSelect: 'none', pointerEvents: 'none' }}
        >
          {label}
        </text>
        {/* Investment cube dots */}
        {cubeDots}
        {/* Capacity indicator */}
        {isAtCapacity && (
          <text
            x={px.x}
            y={px.y + 28}
            textAnchor="middle"
            fontSize={6}
            fill="#999"
            style={{ userSelect: 'none', pointerEvents: 'none' }}
          >
            FULL
          </text>
        )}
      </g>
    );
  });

  const zoomPercent = Math.round(scale * 100);

  return (
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-1">Northern Pacific — Round {gameState.current_round || 1}/3</h2>
      {gameState.game_over && (
        <div className="bg-yellow-100 border-2 border-yellow-400 text-yellow-900 p-4 mb-3 rounded text-center">
          <span className="text-lg font-bold">
            {gameState.winner ? (
              <>Game Over! {
                (() => {
                  const winner = gameState.players?.find((p: any) => p.id === gameState.winner);
                  return winner ? winner.username : 'Unknown';
                })()
              } wins!</>
            ) : 'Game Over!'}
          </span>
        </div>
      )}
      <div className="flex gap-4 w-full">
        <div className="relative">
          <svg
            ref={svgRef}
            width={DISPLAY_W}
            height={DISPLAY_H}
            style={{
              border: '1px solid #ccc',
              borderRadius: 4,
              cursor: isPanning ? 'grabbing' : 'grab',
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <g transform={`translate(${offsetX}, ${offsetY}) scale(${scale})`}
               style={{ transformOrigin: '0 0' }}>
              <image href="/np_board.png" width={DISPLAY_W} height={DISPLAY_H} />
              {trackElements}
              {cityElements}
            </g>
          </svg>
          <div className="absolute top-2 right-2 flex flex-col gap-1">
            <button onClick={zoomIn} className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-lg font-bold shadow-sm cursor-pointer">+</button>
            <button onClick={zoomOut} className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-lg font-bold shadow-sm cursor-pointer">-</button>
            <button onClick={resetView} className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-xs font-bold shadow-sm cursor-pointer">Fit</button>
            <div className="bg-white/80 border border-gray-300 rounded text-xs text-center py-1 px-1 shadow-sm select-none">{zoomPercent}%</div>
          </div>
        </div>
        <div className="w-64 flex flex-col gap-3">
          {/* Controls panel */}
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Controls</h3>
            <p className="text-sm mb-2">
              Turn: {(() => {
                const cp = gameState.current_player;
                const player = gameState.players?.find((p: any) => p.id === cp);
                return player ? player.username : cp?.slice(0, 6);
              })()}
              {gameState.current_round && <span className="ml-2 text-xs text-gray-400">Round {gameState.current_round}/3</span>}
            </p>
            <p className="text-xs text-gray-500 mb-2">Train at: {trainEndpoint.replace(/([A-Z])/g, ' $1').trim()}</p>

            {!isMyTurn ? (
              <p className="text-sm text-gray-500">Waiting for opponent...</p>
            ) : selectedCity ? (
              <CityActions
                city={selectedCity}
                isReachable={!!(gameState.available_tracks || []).find((t: any) => t.target === selectedCity)}
                isInvestable={availableInvestCities.includes(selectedCity)}
                hasStd={(playerSupply[user?.id || ''] ?? 0) > 0}
                hasEnh={(playerEnhanced[user?.id || ''] ?? 0) > 0}
                onLayTrack={() => {
                  const seg = (gameState.available_tracks || []).find((t: any) => t.target === selectedCity);
                  if (seg) sendMove('lay_track', { segment_id: seg.segment_id });
                  setSelectedCity(null);
                }}
                onInvest={(enhanced: boolean) => {
                  sendMove('invest', { city: selectedCity, enhanced });
                  setSelectedCity(null);
                }}
                onCancel={() => setSelectedCity(null)}
              />
            ) : (
              <div className="text-sm text-gray-500">
                <p>Click a city on the map <span className="text-green-600 font-medium">outlined in green</span> to see available actions.</p>
              </div>
            )}
          </div>

          {/* Player supplies */}
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Supplies</h3>
            {gameState.players && gameState.players.map((p: any) => (
              <div key={p.id} className="flex justify-between text-sm items-center py-0.5">
                <span>
                  <span className="inline-block w-3 h-3 rounded-full mr-1.5 align-middle"
                    style={{ backgroundColor: getPlayerColor(p.id, gameState.players) }} />
                  {p.username}
                  {p.is_bot && <span className="ml-1 text-xs text-purple-500 font-medium">[BOT]</span>}
                </span>
                <span className="text-xs">
                  {playerSupply[p.id] ?? 0} std + {playerEnhanced[p.id] ?? 0} enh
                </span>
              </div>
            ))}
          </div>

          {/* Cumulative scores */}
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Cumulative Scores</h3>
            <p className="text-xs text-gray-500 mb-1">Good investments (cubes in hand)</p>
            {gameState.players && gameState.players.map((p: any) => (
              <div key={p.id} className="flex justify-between text-sm items-center py-0.5">
                <span>
                  <span className="inline-block w-3 h-3 rounded-full mr-1.5 align-middle"
                    style={{ backgroundColor: getPlayerColor(p.id, gameState.players) }} />
                  {p.username}
                </span>
                <span className="font-medium">
                  {cumulativeGood[p.id] ?? 0}
                  {gameState.game_over && gameState.winner === p.id && (
                    <span className="ml-1 text-yellow-600 font-bold"> [WINNER]</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          {/* Move history */}
          {(gameState.move_history || []).length > 0 && (
            <div className="bg-white p-4 rounded shadow">
              <h3 className="font-bold border-b pb-2 mb-2">Game Log</h3>
              <div className="max-h-40 overflow-y-auto text-xs space-y-0.5">
                {(gameState.move_history || []).slice(-15).reverse().map((entry: string, i: number) => (
                  <div key={i} className={`py-0.5 ${entry.startsWith('---') ? 'font-bold text-gray-600 mt-1' : 'text-gray-700'}`}>
                    {entry}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
