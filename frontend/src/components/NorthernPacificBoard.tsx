import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useGameStore, useAuthStore } from '../store';
import { useWebSocket } from '../hooks/useWebSocket';

// City positions as percentages of the board image (1410 x 572)
// Placed to align exactly with the cities on the Northern Pacific map
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

const BOARD_W = 1410;
const BOARD_H = 572;
const DISPLAY_W = 900;
const DISPLAY_H = Math.round(BOARD_H * (DISPLAY_W / BOARD_W));

const MIN_SCALE = 0.5;
const MAX_SCALE = 4;

function pctToPx(pct_x: number, pct_y: number) {
  return { x: pct_x * DISPLAY_W, y: pct_y * DISPLAY_H };
}

export const NorthernPacificBoard: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { gameState } = useGameStore();
  const { user } = useAuthStore();
  const { sendMove } = useWebSocket(id || '', false);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  // Pan & zoom state
  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [isPanning, setIsPanning] = useState(false);
  const [hasMoved, setHasMoved] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetAtPanStart = useRef({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  const resetView = useCallback(() => {
    setScale(1);
    setOffsetX(0);
    setOffsetY(0);
  }, []);

  const zoomIn = useCallback(() => {
    setScale(s => Math.min(MAX_SCALE, s * 1.3));
  }, []);

  const zoomOut = useCallback(() => {
    setScale(s => {
      const newScale = Math.max(MIN_SCALE, s / 1.3);
      return newScale;
    });
  }, []);

  // Wheel zoom via native listener (React wheel is passive by default)
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.85 : 1.18;
      const rect = svg.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;

      setScale(prevScale => {
        const newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, prevScale * delta));
        const ratio = newScale / prevScale;
        setOffsetX(ox => cx - ratio * (cx - ox));
        setOffsetY(oy => cy - ratio * (cy - oy));
        return newScale;
      });
    };

    svg.addEventListener('wheel', onWheel, { passive: false });
    return () => svg.removeEventListener('wheel', onWheel);
  }, []);

  // Mouse handlers for panning
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
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist > 3) setHasMoved(true);
    setOffsetX(offsetAtPanStart.current.x + dx);
    setOffsetY(offsetAtPanStart.current.y + dy);
  }, [isPanning]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  if (!gameState) return null;

  const handleCityClick = (city: string) => {
    if (hasMoved) return; // was a pan drag, ignore
    setSelectedCity(city);
  };
  const handleInvest = () => {
    if (selectedCity) { sendMove('invest', { city: selectedCity }); setSelectedCity(null); }
  };
  const handleMoveTrain = () => {
    if (selectedCity) { sendMove('move_train', { city: selectedCity }); setSelectedCity(null); }
  };

  const isMyTurn = gameState.current_player === user?.id;

  const edges: React.ReactNode[] = [];
  const drawn = new Set<string>();

  if (gameState.graph) {
    Object.entries(gameState.graph).forEach(([city, neighbors]) => {
      (neighbors as string[]).forEach((neighbor: string) => {
        const key = [city, neighbor].sort().join('--');
        if (drawn.has(key)) return;
        drawn.add(key);
        const a = CITY_POSITIONS[city];
        const b = CITY_POSITIONS[neighbor];
        if (!a || !b) return;
        const aPx = pctToPx(a.pct_x, a.pct_y);
        const bPx = pctToPx(b.pct_x, b.pct_y);
        const mx = (aPx.x + bPx.x) / 2;
        const my = (aPx.y + bPx.y) / 2;
        const dx = bPx.x - aPx.x;
        const dy = bPx.y - aPx.y;
        const len = Math.sqrt(dx * dx + dy * dy);
        const offset = len > 80 ? 6 : 3;
        const cx = mx + (dy / len) * offset;
        const cy = my - (dx / len) * offset;
        edges.push(
          <path
            key={key}
            d={`M ${aPx.x} ${aPx.y} Q ${cx} ${cy} ${bPx.x} ${bPx.y}`}
            stroke="#5c3d2e"
            strokeWidth={2}
            fill="none"
            opacity={0.6}
          />
        );
      });
    });
  }

  const cityNodes: React.ReactNode[] = Object.entries(CITY_POSITIONS).map(([city, pos]) => {
    const px = pctToPx(pos.pct_x, pos.pct_y);
    const isSelected = selectedCity === city;
    const hasTrain = gameState.train_pos === city;
    const isInvested = !!gameState.investments?.[city];
    const label = city.replace(/([A-Z])/g, ' $1').trim();

    return (
      <g key={city} onClick={() => handleCityClick(city)} style={{ cursor: 'pointer' }}>
        {hasTrain && (
          <circle cx={px.x} cy={px.y} r={12} fill="#dc2626" stroke="#fff" strokeWidth={2} opacity={0.8} />
        )}
        <circle
          cx={px.x}
          cy={px.y}
          r={8}
          fill={isInvested ? '#4f46e5' : '#fff'}
          stroke={isSelected ? '#ef4444' : '#333'}
          strokeWidth={isSelected ? 3 : 1.5}
          opacity={0.6}
        />
        <text
          x={px.x}
          y={px.y - 14}
          textAnchor="middle"
          fontSize={9}
          fill="#1a1a1a"
          style={{ userSelect: 'none', pointerEvents: 'none' }}
        >
          {label}
        </text>
      </g>
    );
  });

  const zoomPercent = Math.round(scale * 100);

  return (
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-2">Northern Pacific: {id}</h2>
      {gameState.game_over && (
        <div className="bg-red-100 text-red-800 p-3 mb-3 rounded">Game Over!</div>
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
              {edges}
              {cityNodes}
            </g>
          </svg>

          {/* Zoom overlay controls */}
          <div className="absolute top-2 right-2 flex flex-col gap-1">
            <button
              onClick={zoomIn}
              className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-lg font-bold shadow-sm cursor-pointer"
              title="Zoom in"
            >
              +
            </button>
            <button
              onClick={zoomOut}
              className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-lg font-bold shadow-sm cursor-pointer"
              title="Zoom out"
            >
              -
            </button>
            <button
              onClick={resetView}
              className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-xs font-bold shadow-sm cursor-pointer"
              title="Reset zoom to fit"
            >
              Fit
            </button>
            <div className="bg-white/80 border border-gray-300 rounded text-xs text-center py-1 px-1 shadow-sm select-none">
              {zoomPercent}%
            </div>
          </div>
        </div>
        <div className="w-52 flex flex-col gap-3">
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Controls</h3>
            <p className="text-sm mb-2">Turn: {gameState.current_player?.slice(0, 6)}</p>
            {selectedCity ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium">{selectedCity.replace(/([A-Z])/g, ' $1').trim()}</p>
                <button onClick={handleInvest} disabled={!isMyTurn} className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-40">Invest</button>
                <button onClick={handleMoveTrain} disabled={!isMyTurn} className="bg-red-600 text-white px-3 py-1 rounded text-sm disabled:opacity-40">Move Train</button>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Select a city.</p>
            )}
          </div>
          <div className="bg-white p-4 rounded shadow">
            <h3 className="font-bold border-b pb-2 mb-2">Scores</h3>
            {gameState.balances && Object.entries(gameState.balances).map(([pid, bal]) => (
              <div key={pid} className="flex justify-between text-sm">
                <span>{pid.slice(0, 6)}</span><span>${bal as number}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
