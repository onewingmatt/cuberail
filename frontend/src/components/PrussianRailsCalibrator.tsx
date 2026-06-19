import React, { useEffect, useMemo, useRef, useState } from 'react';

type CityEntry = {
  key: string;
  city: string;
  q: number;
  r: number;
  income?: number;
};

type HexMap = Record<string, { terrain: string; city?: string; income?: number }>;
type TerrainBrush = 'plains' | 'hills' | 'mountains' | 'berlin_approach' | 'urban' | 'erase';
type PaintedHex = { x: number; y: number; terrain: Exclude<TerrainBrush, 'erase'> };

interface Props {
  hexes: HexMap;
  backgroundImage?: string | null;
}

const BG_W = 1409;
const BG_H = 1046;
const STORAGE_KEY = 'prussian-rails-calibration-v1';
const PAINT_STORAGE_KEY = 'prussian-rails-hex-paint-v1';
const ASSIGN_STORAGE_KEY = 'prussian-rails-city-hex-assignments-v1';
const PAINT_PICK_RADIUS = 22;

const TERRAIN_COLORS: Record<Exclude<TerrainBrush, 'erase'>, string> = {
  plains: 'rgba(245, 230, 200, 0.45)',
  hills: 'rgba(145, 199, 136, 0.45)',
  mountains: 'rgba(188, 154, 124, 0.45)',
  berlin_approach: 'rgba(240, 194, 122, 0.55)',
  urban: 'rgba(212, 197, 169, 0.55)',
};

const DEFAULT_CALIBRATION_POSITIONS: Record<string, { x: number; y: number }> = {
  'Aachen': { x: 113.2, y: 599.9 },
  'Augsburg': { x: 489.4, y: 951.0 },
  'Bamberg': { x: 516.4, y: 699.4 },
  'Berlin': { x: 687.2, y: 367.7 },
  'Bielefeld': { x: 286.9, y: 402.1 },
  'Braunschweig': { x: 457.8, y: 404.9 },
  'Bremen': { x: 318.6, y: 250.8 },
  'Breslau': { x: 1005.0, y: 553.6 },
  'Bromberg': { x: 1061.6, y: 255.4 },
  'Chemnitz': { x: 691.0, y: 602.8 },
  'Danzig': { x: 1146.1, y: 104.0 },
  'Dortmund': { x: 229.3, y: 504.3 },
  'Dresden': { x: 717.0, y: 551.7 },
  'Duisburg': { x: 116.0, y: 505.2 },
  'Düsseldorf': { x: 144.8, y: 550.7 },
  'Erfurt': { x: 489.5, y: 553.6 },
  'Essen': { x: 174.5, y: 501.5 },
  'Flensburg': { x: 375.2, y: 52.9 },
  'Frankfurt am Main': { x: 287.1, y: 704.0 },
  'Frankfurt an der Oder': { x: 805.3, y: 405.9 },
  'Freiburg im Breisgau': { x: 199.6, y: 950.1 },
  'Görlitz': { x: 833.1, y: 556.4 },
  'Göttingen': { x: 400.3, y: 502.5 },
  'Halle': { x: 574.0, y: 504.3 },
  'Hamburg': { x: 401.2, y: 206.2 },
  'Hamm': { x: 260.0, y: 453.2 },
  'Hannover': { x: 400.3, y: 405.9 },
  'Heilbronn': { x: 314.9, y: 848.9 },
  'Karlsruhe': { x: 261.0, y: 851.6 },
  'Kassel': { x: 372.4, y: 551.6 },
  'Kiel': { x: 460.7, y: 105.9 },
  'Koblenz': { x: 201.5, y: 653.8 },
  'Köln': { x: 172.7, y: 603.7 },
  'Königsberg': { x: 1289.2, y: 54.8 },
  'Kottbus': { x: 775.6, y: 453.3 },
  'Kreuz': { x: 916.7, y: 304.6 },
  'Leipzig': { x: 602.7, y: 552.6 },
  'Liegnitz': { x: 917.7, y: 502.5 },
  'Lübeck': { x: 489.5, y: 155.1 },
  'Magdeburg': { x: 575.9, y: 404.0 },
  'Mainz': { x: 230.5, y: 700.3 },
  'Mannheim': { x: 288.9, y: 797.8 },
  'Mühlhausen': { x: 430.9, y: 552.6 },
  'München': { x: 543.3, y: 948.2 },
  'Münster': { x: 201.5, y: 453.2 },
  'Neu Brandenburg': { x: 687.3, y: 206.2 },
  'Nürnberg': { x: 512.7, y: 798.8 },
  'Oldenburg': { x: 261.0, y: 255.4 },
  'Osnabrück': { x: 259.1, y: 353.8 },
  'Plauen': { x: 601.9, y: 649.2 },
  'Posen': { x: 976.2, y: 405.0 },
  'Regensburg': { x: 603.7, y: 849.9 },
  'Rostock': { x: 601.9, y: 156.0 },
  'Saarbrücken': { x: 114.2, y: 798.8 },
  'Schneidemühl': { x: 1004.0, y: 256.4 },
  'Stettin': { x: 805.3, y: 208.1 },
  'Stolp': { x: 978.0, y: 102.2 },
  'Stralsund': { x: 687.2, y: 104.0 },
  'Strasbourg': { x: 172.7, y: 899.9 },
  'Stuttgart': { x: 344.5, y: 895.3 },
  'Waldenburg': { x: 976.2, y: 604.7 },
  'Wesel': { x: 143.0, y: 450.4 },
  'Wittenberge': { x: 488.4, y: 253.5 },
  'Würzburg': { x: 403.1, y: 699.3 },
};

export const PrussianRailsCalibrator: React.FC<Props> = ({ hexes, backgroundImage }) => {
  const cities = useMemo<CityEntry[]>(() => {
    const canonicalCities = [
      'Aachen', 'Augsburg', 'Bamberg', 'Berlin', 'Bielefeld', 'Braunschweig',
      'Bremen', 'Breslau', 'Bromberg', 'Chemnitz', 'Danzig', 'Dortmund',
      'Dresden', 'Duisburg', 'Düsseldorf', 'Erfurt', 'Essen', 'Flensburg',
      'Frankfurt am Main', 'Frankfurt an der Oder', 'Freiburg im Breisgau',
      'Görlitz', 'Göttingen', 'Halle', 'Hamburg', 'Hamm', 'Hannover',
      'Heilbronn', 'Karlsruhe', 'Kassel', 'Kiel', 'Koblenz', 'Köln',
      'Königsberg', 'Kottbus', 'Kreuz', 'Leipzig', 'Liegnitz', 'Lübeck',
      'Magdeburg', 'Mainz', 'Mannheim', 'Mühlhausen', 'München', 'Münster',
      'Neu Brandenburg', 'Nürnberg', 'Oldenburg', 'Osnabrück', 'Plauen',
      'Posen', 'Regensburg', 'Rostock', 'Saarbrücken', 'Schneidemühl',
      'Stettin', 'Stolp', 'Stralsund', 'Strasbourg', 'Stuttgart',
      'Waldenburg', 'Wesel', 'Wittenberge', 'Würzburg'
    ];

    const byCity = new Map<string, CityEntry>();
    for (const [key, v] of Object.entries(hexes)) {
      if (!v.city) continue;
      const [q, r] = key.split(',').map(Number);
      byCity.set(v.city, { key, city: v.city, q, r, income: v.income });
    }

    return canonicalCities
      .map((city) => byCity.get(city) || { key: '', city, q: 0, r: 0, income: 0 })
      .sort((a, b) => a.city.localeCompare(b.city));
  }, [hexes]);

  const [selectedCity, setSelectedCity] = useState<string>(cities[0]?.city || '');
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [selectedPoint, setSelectedPoint] = useState<string | null>(null);
  const [showLabels, setShowLabels] = useState(true);
  const [showDots, setShowDots] = useState(true);
  const [showBoard, setShowBoard] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [draggingPoint, setDraggingPoint] = useState<string | null>(null);
  const [paintMode, setPaintMode] = useState(false);
  const [paintBrush, setPaintBrush] = useState<TerrainBrush>('plains');
  const [paintedHexes, setPaintedHexes] = useState<Record<string, PaintedHex>>({});
  const [assignMode, setAssignMode] = useState(false);
  const [cityAssignments, setCityAssignments] = useState<Record<string, string[]>>({});
  const dragStart = useRef({ x: 0, y: 0, ox: 0, oy: 0 });
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    let saved: Record<string, { x: number; y: number }> = {};
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) saved = JSON.parse(raw);
    } catch {
      saved = {};
    }

    setPositions(prev => {
      const next: Record<string, { x: number; y: number }> = { ...DEFAULT_CALIBRATION_POSITIONS, ...saved, ...prev };
      for (const c of cities) {
        if (!next[c.city]) {
          next[c.city] = {
            x: 150 + c.q * 50,
            y: 120 + c.r * 45,
          };
        }
      }
      return next;
    });

    if (cities[0] && !selectedPoint) setSelectedPoint(cities[0].city);
    if (cities[0] && !selectedCity) setSelectedCity(cities[0].city);
  }, [cities, selectedCity, selectedPoint]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(positions));
    } catch {
      // ignore storage failures
    }
  }, [positions]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!selectedPoint) return;
      const step = e.shiftKey ? 10 : 1;
      if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) return;
      e.preventDefault();
      setPositions(prev => {
        const cur = prev[selectedPoint] || { x: 0, y: 0 };
        let { x, y } = cur;
        if (e.key === 'ArrowUp') y -= step;
        if (e.key === 'ArrowDown') y += step;
        if (e.key === 'ArrowLeft') x -= step;
        if (e.key === 'ArrowRight') x += step;
        return { ...prev, [selectedPoint]: { x, y } };
      });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedPoint]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(PAINT_STORAGE_KEY);
      if (raw) {
        setPaintedHexes(JSON.parse(raw));
      }
    } catch {
      // ignore storage failures
    }
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(ASSIGN_STORAGE_KEY);
      if (raw) {
        setCityAssignments(JSON.parse(raw));
      }
    } catch {
      // ignore storage failures
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(PAINT_STORAGE_KEY, JSON.stringify(paintedHexes));
    } catch {
      // ignore storage failures
    }
  }, [paintedHexes]);

  useEffect(() => {
    try {
      localStorage.setItem(ASSIGN_STORAGE_KEY, JSON.stringify(cityAssignments));
    } catch {
      // ignore storage failures
    }
  }, [cityAssignments]);

  const paintExportJson = useMemo(() => {
    return JSON.stringify(
      Object.entries(paintedHexes).map(([key, value]) => ({ key, ...value })),
      null,
      2,
    );
  }, [paintedHexes]);

  const assignmentExportJson = useMemo(() => {
    return JSON.stringify(cityAssignments, null, 2);
  }, [cityAssignments]);

  const assignCityToNearestHex = (x: number, y: number) => {
    let nearestKey: string | null = null;
    let nearestDist = Infinity;
    for (const [key, value] of Object.entries(paintedHexes)) {
      const d = Math.hypot(value.x - x, value.y - y);
      if (d < nearestDist) {
        nearestDist = d;
        nearestKey = key;
      }
    }
    if (!nearestKey || nearestDist > PAINT_PICK_RADIUS) return;

    setCityAssignments(prev => {
      const next = { ...prev };
      const existing = next[selectedCity] || [];
      const maxCount = selectedCity === 'Berlin' ? 3 : 1;
      if (existing.includes(nearestKey)) return next;
      next[selectedCity] = [...existing, nearestKey].slice(0, maxCount);
      return next;
    });

    // Assigned city hexes should be urban for map generation.
    setPaintedHexes(prev => {
      const existing = prev[nearestKey!];
      if (!existing) return prev;
      return {
        ...prev,
        [nearestKey!]: {
          ...existing,
          terrain: 'urban',
        },
      };
    });
  };

  const selectedPos = selectedPoint ? positions[selectedPoint] : null;

  const exportJson = useMemo(() => {
    const out = cities.map(c => ({
      city: c.city,
      q: c.q,
      r: c.r,
      x: Math.round((positions[c.city]?.x ?? 0) * 10) / 10,
      y: Math.round((positions[c.city]?.y ?? 0) * 10) / 10,
      income: c.income || 0,
    }));
    return JSON.stringify(out, null, 2);
  }, [cities, positions]);

  const paintHexAt = (x: number, y: number) => {
    setPaintedHexes(prev => {
      const next = { ...prev };

      // Find nearest existing painted hex for selection/erase
      let nearestKey: string | null = null;
      let nearestDist = Infinity;
      for (const [key, value] of Object.entries(prev)) {
        const d = Math.hypot(value.x - x, value.y - y);
        if (d < nearestDist) {
          nearestDist = d;
          nearestKey = key;
        }
      }

      if (paintBrush === 'erase') {
        if (nearestKey && nearestDist <= PAINT_PICK_RADIUS) {
          delete next[nearestKey];
        }
        return next;
      }

      // If clicking near an existing hex center, repaint that one
      if (nearestKey && nearestDist <= PAINT_PICK_RADIUS) {
        next[nearestKey] = { ...next[nearestKey], terrain: paintBrush };
        return next;
      }

      // Otherwise create a brand new hex center where clicked
      const key = `hex_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      next[key] = { x, y, terrain: paintBrush };
      return next;
    });
  };



  const handleBoardClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;

    const svg = svgRef.current;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;

    const screenCTM = svg.getScreenCTM();
    if (!screenCTM) return;

    const svgPoint = pt.matrixTransform(screenCTM.inverse());
    const x = (svgPoint.x - offset.x) / zoom;
    const y = (svgPoint.y - offset.y) / zoom;

    if (paintMode) {
      paintHexAt(x, y);
      return;
    }

    if (assignMode) {
      if (!selectedCity) return;
      assignCityToNearestHex(x, y);
      return;
    }

    if (!selectedCity) return;
    setPositions(prev => ({ ...prev, [selectedCity]: { x, y } }));
    setSelectedPoint(selectedCity);
  };

  const startPan = (e: React.MouseEvent) => {
    if (e.button !== 0 || (e.target as HTMLElement).dataset.point === '1') return;
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
  };

  const startPointDrag = (city: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedPoint(city);
    setSelectedCity(city);
    setDraggingPoint(city);
  };

  const movePan = (e: React.MouseEvent) => {
    if (draggingPoint && svgRef.current) {
      const svg = svgRef.current;
      const pt = svg.createSVGPoint();
      pt.x = e.clientX;
      pt.y = e.clientY;
      const screenCTM = svg.getScreenCTM();
      if (!screenCTM) return;
      const svgPoint = pt.matrixTransform(screenCTM.inverse());
      const x = (svgPoint.x - offset.x) / zoom;
      const y = (svgPoint.y - offset.y) / zoom;
      setPositions(prev => ({ ...prev, [draggingPoint]: { x, y } }));
      return;
    }

    if (!dragging) return;
    setOffset({
      x: dragStart.current.ox + (e.clientX - dragStart.current.x),
      y: dragStart.current.oy + (e.clientY - dragStart.current.y),
    });
  };

  const endPan = () => {
    setDragging(false);
    setDraggingPoint(null);
  };

  return (
    <div className="w-full">
      <div className="mb-3 flex flex-wrap gap-2 items-center">
        <button onClick={() => setShowBoard(v => !v)} className="px-2 py-1 border rounded cursor-pointer">
          {showBoard ? 'Hide board' : 'Show board'}
        </button>
        <button onClick={() => setShowDots(v => !v)} className="px-2 py-1 border rounded cursor-pointer">
          {showDots ? 'Hide dots' : 'Show dots'}
        </button>
        <button onClick={() => setShowLabels(v => !v)} className="px-2 py-1 border rounded cursor-pointer">
          {showLabels ? 'Hide labels' : 'Show labels'}
        </button>
        <button onClick={() => setZoom(z => Math.min(4, z * 1.2))} className="px-2 py-1 border rounded cursor-pointer">+</button>
        <button onClick={() => setZoom(z => Math.max(0.2, z / 1.2))} className="px-2 py-1 border rounded cursor-pointer">-</button>
        <button onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }} className="px-2 py-1 border rounded cursor-pointer">Reset view</button>
        <button onClick={() => {
          localStorage.removeItem(STORAGE_KEY);
          setPositions({ ...DEFAULT_CALIBRATION_POSITIONS });
        }} className="px-2 py-1 border rounded cursor-pointer">
          Reset calibration
        </button>
        <button onClick={() => setPaintMode(v => !v)} className={`px-2 py-1 border rounded cursor-pointer ${paintMode ? 'bg-amber-200 border-amber-400' : ''}`}>
          {paintMode ? 'Paint mode on' : 'Paint mode off'}
        </button>
        <button onClick={() => setAssignMode(v => !v)} className={`px-2 py-1 border rounded cursor-pointer ${assignMode ? 'bg-emerald-200 border-emerald-400' : ''}`}>
          {assignMode ? 'Assign mode on' : 'Assign mode off'}
        </button>
        <select
          value={paintBrush}
          onChange={(e) => setPaintBrush(e.target.value as TerrainBrush)}
          className="px-2 py-1 border rounded text-sm"
        >
          <option value="plains">plains</option>
          <option value="hills">hills</option>
          <option value="mountains">mountains</option>
          <option value="berlin_approach">berlin approach</option>
          <option value="urban">urban</option>
          <option value="erase">erase</option>
        </select>
        <button onClick={() => {
          localStorage.removeItem(PAINT_STORAGE_KEY);
          setPaintedHexes({});
        }} className="px-2 py-1 border rounded cursor-pointer">
          Clear painted hexes
        </button>
        <button onClick={() => {
          localStorage.removeItem(ASSIGN_STORAGE_KEY);
          setCityAssignments({});
        }} className="px-2 py-1 border rounded cursor-pointer">
          Clear assignments
        </button>
        <span className="text-sm text-gray-600">{paintMode ? 'Paint mode: click to create hex centers exactly where you want them. Click near an existing hex to repaint it. Use erase to remove the nearest hex.' : assignMode ? 'Assign mode: select a city, then click a painted hex to bind it. Berlin can bind to 3 hexes.' : 'City mode: click the board to place the selected city. Arrow keys nudge selected point, Shift+Arrow = 10px.'}</span>
      </div>

      <div className="grid grid-cols-[320px_1fr] gap-4">
        <div className="bg-white border rounded p-3 space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Selected city</label>
            <select
              className="w-full border rounded p-2 text-sm"
              value={selectedCity}
              onChange={(e) => {
                setSelectedCity(e.target.value);
                setSelectedPoint(e.target.value);
              }}
            >
              {cities.map(c => (
                <option key={c.city} value={c.city}>{c.city}</option>
              ))}
            </select>
          </div>

          <div className="text-sm space-y-1">
            <div>Selected point: <span className="font-mono">{selectedPoint || '—'}</span></div>
            <div>X: <span className="font-mono">{selectedPos ? selectedPos.x.toFixed(1) : '—'}</span></div>
            <div>Y: <span className="font-mono">{selectedPos ? selectedPos.y.toFixed(1) : '—'}</span></div>
            <div>Zoom: <span className="font-mono">{zoom.toFixed(2)}x</span></div>
          </div>

          <div>
            <div className="text-sm font-medium mb-1">Calibration export</div>
            <textarea
              readOnly
              value={exportJson}
              className="w-full h-[220px] border rounded p-2 text-xs font-mono"
            />
          </div>

          <div>
            <div className="text-sm font-medium mb-1">Painted hex export</div>
            <textarea
              readOnly
              value={paintExportJson}
              className="w-full h-[120px] border rounded p-2 text-xs font-mono"
            />
          </div>

          <div>
            <div className="text-sm font-medium mb-1">City → painted hex assignments</div>
            <textarea
              readOnly
              value={assignmentExportJson}
              className="w-full h-[120px] border rounded p-2 text-xs font-mono"
            />
          </div>
        </div>

        <div className="bg-white border rounded p-2 overflow-hidden">
          <svg
            ref={svgRef}
            width="100%"
            viewBox={`0 0 ${BG_W} ${BG_H}`}
            className="w-full h-auto border rounded bg-slate-100"
            onClick={handleBoardClick}
            onMouseDown={startPan}
            onMouseMove={movePan}
            onMouseUp={endPan}
            onMouseLeave={endPan}
            style={{ cursor: dragging ? 'grabbing' : 'grab' }}
          >
            <g transform={`translate(${offset.x}, ${offset.y}) scale(${zoom})`}>
              {showBoard && backgroundImage && (
                <image href={backgroundImage} x={0} y={0} width={BG_W} height={BG_H} opacity={1} />
              )}

              {(paintMode || assignMode) && Object.entries(paintedHexes).map(([key, painted]) => {
                const assignedCities = Object.entries(cityAssignments)
                  .filter(([, keys]) => keys.includes(key))
                  .map(([city]) => city);
                return (
                <g key={`paint-${key}`}>
                  <circle
                    cx={painted.x}
                    cy={painted.y}
                    r={12}
                    fill={TERRAIN_COLORS[painted.terrain]}
                    stroke={'rgba(0,0,0,0.45)'}
                    strokeWidth={2}
                    pointerEvents="none"
                  />
                  <text
                    x={painted.x}
                    y={painted.y + 4}
                    textAnchor="middle"
                    fontSize={10}
                    fontWeight="bold"
                    fill="#111827"
                    stroke="#fff"
                    strokeWidth={2}
                    paintOrder="stroke"
                    pointerEvents="none"
                  >
                    {painted.terrain === 'berlin_approach' ? 'BA' : painted.terrain[0].toUpperCase()}
                  </text>
                  {assignedCities.length > 0 && (
                    <text
                      x={painted.x + 14}
                      y={painted.y - 14}
                      fontSize={10}
                      fontWeight="bold"
                      fill="#065f46"
                      stroke="#fff"
                      strokeWidth={2}
                      paintOrder="stroke"
                      pointerEvents="none"
                    >
                      {assignedCities.length === 1 ? assignedCities[0] : `${assignedCities.length} cities`}
                    </text>
                  )}
                </g>
              )})}

              {showDots && cities.map((c) => {
                const pos = positions[c.city];
                if (!pos) return null;
                const selected = selectedPoint === c.city;
                return (
                  <g key={c.city}>
                    <circle
                      data-point="1"
                      cx={pos.x}
                      cy={pos.y}
                      r={selected ? 8 : 5}
                      fill={selected ? '#ef4444' : '#2563eb'}
                      stroke="#fff"
                      strokeWidth={2}
                      onMouseDown={startPointDrag(c.city)}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedPoint(c.city);
                        setSelectedCity(c.city);
                      }}
                    />
                    {showLabels && (
                      <text
                        x={pos.x + 10}
                        y={pos.y - 8}
                        fontSize={14}
                        fontWeight={selected ? 'bold' : 'normal'}
                        fill={selected ? '#991b1b' : '#111827'}
                        stroke="#fff"
                        strokeWidth={3}
                        paintOrder="stroke"
                      >
                        {c.city}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
};
