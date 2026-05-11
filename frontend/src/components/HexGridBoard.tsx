import React, { useCallback, useRef, useState, useEffect } from 'react';

// Flat-top hex axial directions
const AXIAL_DIRECTIONS = [
  [1, -1],  // NE
  [1, 0],   // E
  [0, 1],   // SE
  [-1, 1],  // SW
  [-1, 0],  // W
  [0, -1],  // NW
];

export function hexToPixel(q: number, r: number, size: number): { x: number; y: number } {
  return {
    x: size * (3 / 2 * q),
    y: size * (Math.sqrt(3) / 2 * q + Math.sqrt(3) * r),
  };
}

export function hexCornerPath(q: number, r: number, size: number): string {
  const { x: cx, y: cy } = hexToPixel(q, r, size);
  const corners: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angleDeg = 60 * i;
    const angleRad = Math.PI / 180 * angleDeg;
    corners.push(`${cx + size * Math.cos(angleRad)},${cy + size * Math.sin(angleRad)}`);
  }
  return `M ${corners.join(' L ')} Z`;
}

export function pixelToHex(px: number, py: number, size: number): [number, number] {
  const q = (2 / 3 * px) / size;
  const r = (-1 / 3 * px + Math.sqrt(3) / 3 * py) / size;
  return hexRound(q, r);
}

function hexRound(qF: number, rF: number): [number, number] {
  const sF = -qF - rF;
  let qi = Math.round(qF);
  let ri = Math.round(rF);
  const si = Math.round(sF);
  const qDiff = Math.abs(qi - qF);
  const rDiff = Math.abs(ri - rF);
  const sDiff = Math.abs(si - sF);
  if (qDiff > rDiff && qDiff > sDiff) {
    qi = -ri - si;
  } else if (rDiff > sDiff) {
    ri = -qi - si;
  }
  return [qi, ri];
}

// Terrain colors — visibly distinct hues
const TERRAIN_COLORS: Record<string, string> = {
  water: '#7ab8e0',
  plains: '#f5e6c8',
  hills: '#91c788',
  mountains: '#bc9a7c',
  urban: '#d4c5a9',
  berlin_approach: '#f0c27a',
};

const TERRAIN_LABELS: Record<string, string> = {
  plains: 'P',
  hills: 'H',
  mountains: 'M',
  urban: 'U',
  berlin_approach: 'BA',
};

interface HexData {
  terrain: string;
  city?: string | null;
  income?: number;
}

interface HexGridBoardProps {
  hexes: Record<string, HexData>;
  hexSize?: number;
  boardData?: Record<string, string[]>;  // "q,r" -> company color hexes
  companies?: Record<string, { color: string }>;
  onHexClick?: (q: number, r: number) => void;
  selectedHex?: string | null; // "q,r"
  highlightedHexes?: string[]; // ["q,r", ...]
  showTerrainLabels?: boolean;
  scale?: number;
  offsetX?: number;
  offsetY?: number;
  minQ?: number;
  maxQ?: number;
  minR?: number;
  maxR?: number;
  backgroundImage?: string | null;
  imageOffsetX?: number;
  imageOffsetY?: number;
  imageScale?: number;
}

export const HexGridBoard: React.FC<HexGridBoardProps> = ({
  hexes,
  hexSize = 40,
  boardData = {},
  companies = {},
  onHexClick,
  selectedHex,
  highlightedHexes = [],
  showTerrainLabels = false,
  scale = 1,
  offsetX = 0,
  offsetY = 0,
  minQ = 0,
  maxQ = 17,
  minR = 0,
  maxR = 17,
  backgroundImage = null,
  imageOffsetX = 0,
  imageOffsetY = 0,
  imageScale = 1,
}) => {
  const [internalScale, setInternalScale] = useState(1);
  const [internalOffsetX, setInternalOffsetX] = useState(0);
  const [internalOffsetY, setInternalOffsetY] = useState(0);
  const [isPanning, setIsPanning] = useState(false);
  const [hasMoved, setHasMoved] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetAtPanStart = useRef({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const [viewDims, setViewDims] = useState({ w: 800, h: 600 });

  const effectiveScale = scale * internalScale;
  const effectiveOffsetX = offsetX + internalOffsetX;
  const effectiveOffsetY = offsetY + internalOffsetY;

  // Compute grid bounds from actual hex data
  const allHexes = Object.keys(hexes);
  let gridMinX = 0, gridMaxX = 800, gridMinY = 0, gridMaxY = 600;
  if (allHexes.length > 0) {
    const validHexes = allHexes.filter(key => {
      const [q, r] = key.split(',').map(Number);
      if (q < minQ || q > maxQ || r < minR || r > maxR) return false;
      const h = hexes[key];
      return h && h.terrain !== 'water';
    });
    const pixelPositions = validHexes.map(key => {
      const [q, r] = key.split(',').map(Number);
      return hexToPixel(q, r, hexSize);
    });
    const xs = pixelPositions.map(p => p.x);
    const ys = pixelPositions.map(p => p.y);
    gridMinX = Math.min(...xs) - hexSize;
    gridMaxX = Math.max(...xs) + hexSize;
    gridMinY = Math.min(...ys) - hexSize;
    gridMaxY = Math.max(...ys) + hexSize;
  }

  // Auto-fit on mount: scale to fill viewport
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || allHexes.length === 0) return;
    const parent = svg.parentElement;
    const vw = parent?.clientWidth || 800;
    const vh = parent?.clientHeight || 600;
    setViewDims({ w: vw, h: vh });

    const gridW = gridMaxX - gridMinX;
    const gridH = gridMaxY - gridMinY;
    if (gridW <= 0 || gridH <= 0) return;
    const fitScale = Math.min(vw / gridW, vh / gridH, 1.5);
    const cx = (gridMinX + gridMaxX) / 2;
    const cy = (gridMinY + gridMaxY) / 2;
    setInternalScale(fitScale);
    setInternalOffsetX(vw / 2 - cx * fitScale);
    setInternalOffsetY(vh / 2 - cy * fitScale);
  }, []); // run once on mount

  const fitToView = () => {
    const svg = svgRef.current;
    if (!svg) return;
    const parent = svg.parentElement;
    const vw = parent?.clientWidth || 800;
    const vh = parent?.clientHeight || 600;
    setViewDims({ w: vw, h: vh });
    const gridW = gridMaxX - gridMinX;
    const gridH = gridMaxY - gridMinY;
    if (gridW <= 0 || gridH <= 0) return;
    const fitScale = Math.min(vw / gridW, vh / gridH, 1.5);
    const cx = (gridMinX + gridMaxX) / 2;
    const cy = (gridMinY + gridMaxY) / 2;
    setInternalScale(fitScale);
    setInternalOffsetX(vw / 2 - cx * fitScale);
    setInternalOffsetY(vh / 2 - cy * fitScale);
  };

  // Wheel zoom
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.85 : 1.18;
      const rect = svg.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      setInternalScale(prev => {
        const ns = Math.max(0.3, Math.min(5, prev * delta));
        const r = ns / prev;
        setInternalOffsetX(ox => cx - r * (cx - ox));
        setInternalOffsetY(oy => cy - r * (cy - oy));
        return ns;
      });
    };
    svg.addEventListener('wheel', onWheel, { passive: false });
    return () => svg.removeEventListener('wheel', onWheel);
  }, []);

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    panStart.current = { x: e.clientX, y: e.clientY };
    offsetAtPanStart.current = { x: effectiveOffsetX, y: effectiveOffsetY };
    setHasMoved(false);
    setIsPanning(true);
  }, [effectiveOffsetX, effectiveOffsetY]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning) return;
    const dx = e.clientX - panStart.current.x;
    const dy = e.clientY - panStart.current.y;
    if (Math.sqrt(dx * dx + dy * dy) > 3) setHasMoved(true);
    setInternalOffsetX(offsetAtPanStart.current.x + dx);
    setInternalOffsetY(offsetAtPanStart.current.y + dy);
  }, [isPanning]);

  const handleMouseUp = useCallback(() => setIsPanning(false), []);

  const handleHexClick = useCallback((q: number, r: number) => {
    if (hasMoved) return;
    onHexClick?.(q, r);
  }, [hasMoved, onHexClick]);

  const hexElements: React.ReactNode[] = [];

  for (const [key, hex] of Object.entries(hexes)) {
    const [q, r] = key.split(',').map(Number);
    if (q < minQ || q > maxQ || r < minR || r > maxR) continue;

    const terrain = hex.terrain;
    if (terrain === 'water') continue; // skip water

    const fillColor = TERRAIN_COLORS[terrain] || '#eee';
    const strokeColor = terrain === 'berlin_approach' ? '#e65100' : '#999';
    const isSelected = selectedHex === key;
    const isHighlighted = highlightedHexes.includes(key);
    const path = hexCornerPath(q, r, hexSize);
    const center = hexToPixel(q, r, hexSize);

    // Company track cubes in this hex
    const tracks = boardData[key] || [];
    const hasTracks = tracks.length > 0;

    hexElements.push(
      <g key={key} onClick={() => handleHexClick(q, r)} style={{ cursor: onHexClick ? 'pointer' : 'default' }}>
        {/* Hex polygon */}
        <path
          d={path}
          fill={fillColor}
          stroke={isSelected ? '#ef4444' : (isHighlighted ? '#22c55e' : strokeColor)}
          strokeWidth={isSelected ? 3 : (isHighlighted ? 2.5 : 1)}
          opacity={hasTracks ? 1 : 0.95}
        />
        {/* Terrain label */}
        {showTerrainLabels && !hex.city && (
          <text
            x={center.x}
            y={center.y + 3}
            textAnchor="middle"
            fontSize={8}
            fill="#666"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {TERRAIN_LABELS[terrain] || terrain[0].toUpperCase()}
          </text>
        )}
        {/* City name */}
        {hex.city && (
          <text
            x={center.x}
            y={center.y - 4}
            textAnchor="middle"
            fontSize={8}
            fontWeight="bold"
            fill="#1a1a1a"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {hex.city}
          </text>
        )}
        {/* Income */}
        {hex.city && hex.income && (
          <text
            x={center.x}
            y={center.y + 8}
            textAnchor="middle"
            fontSize={7}
            fill="#555"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            ${hex.income}
          </text>
        )}
        {/* Track cubes */}
        {tracks.map((companyColor: string, idx: number) => (
          <rect
            key={idx}
            x={center.x - 9 + (idx * 5)}
            y={center.y + (hex.city ? 16 : 10)}
            width={4}
            height={4}
            fill={companyColor}
            stroke="#fff"
            strokeWidth={0.5}
            rx={0.5}
          />
        ))}
      </g>
    );
  }

  const zoomPercent = Math.round(effectiveScale * 100);

  // Compute background image dimensions to cover the grid
  const gridPixelW = gridMaxX - gridMinX;
  const gridPixelH = gridMaxY - gridMinY;
  const imgW = gridPixelW * imageScale;
  const imgH = gridPixelH * imageScale;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={viewDims.w}
        height={viewDims.h}
        style={{
          border: '1px solid #ccc',
          borderRadius: 4,
          cursor: isPanning ? 'grabbing' : 'grab',
          background: '#7ab8e0', // water color
          width: '100%',
          height: '100%',
          minHeight: 500,
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${effectiveOffsetX}, ${effectiveOffsetY}) scale(${effectiveScale})`}
           style={{ transformOrigin: '0 0' }}>
          {/* Background image */}
          {backgroundImage && (
            <image
              href={backgroundImage}
              x={0}
              y={0}
              width={1409}
              height={1046}
              style={{ opacity: 0.35, pointerEvents: 'none', imageRendering: 'auto' }}
            />
          )}
          {hexElements}
        </g>
      </svg>
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 flex flex-col gap-1">
        <button
          onClick={() => setInternalScale(s => Math.min(5, s * 1.3))}
          className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-lg font-bold shadow-sm cursor-pointer"
        >+</button>
        <button
          onClick={() => setInternalScale(s => Math.max(0.3, s / 1.3))}
          className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-lg font-bold shadow-sm cursor-pointer"
        >-</button>
        <button
          onClick={fitToView}
          className="bg-white/80 hover:bg-white border border-gray-300 rounded w-8 h-8 flex items-center justify-center text-xs font-bold shadow-sm cursor-pointer"
        >Fit</button>
        <div className="bg-white/80 border border-gray-300 rounded text-xs text-center py-1 px-1 shadow-sm select-none">{zoomPercent}%</div>
      </div>
    </div>
  );
};
