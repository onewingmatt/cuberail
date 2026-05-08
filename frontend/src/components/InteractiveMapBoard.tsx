import React, { useState, useCallback, useRef, useEffect } from 'react';

interface NodeData {
  pct_x: number;
  pct_y: number;
  label: string;
}

interface InteractiveMapBoardProps {
  boardWidth: number;
  boardHeight: number;
  backgroundImage: string;
  nodes: Record<string, NodeData>;
  edges: Record<string, string[]>;
  renderNode: (id: string, node: NodeData, px: { x: number, y: number }) => React.ReactNode;
}

const DISPLAY_W = 900;
const MIN_SCALE = 0.5;
const MAX_SCALE = 4;

export const InteractiveMapBoard: React.FC<InteractiveMapBoardProps> = ({
  boardWidth,
  boardHeight,
  backgroundImage,
  nodes,
  edges,
  renderNode,
}) => {
  const DISPLAY_H = Math.round(boardHeight * (DISPLAY_W / boardWidth));

  const pctToPx = useCallback((pct_x: number, pct_y: number) => {
    return { x: pct_x * DISPLAY_W, y: pct_y * DISPLAY_H };
  }, [DISPLAY_H]);

  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [isPanning, setIsPanning] = useState(false);
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
    setScale(s => Math.max(MIN_SCALE, s / 1.3));
  }, []);

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

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    panStart.current = { x: e.clientX, y: e.clientY };
    offsetAtPanStart.current = { x: offsetX, y: offsetY };
    setIsPanning(true);
  }, [offsetX, offsetY]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning) return;
    const dx = e.clientX - panStart.current.x;
    const dy = e.clientY - panStart.current.y;
    setOffsetX(offsetAtPanStart.current.x + dx);
    setOffsetY(offsetAtPanStart.current.y + dy);
  }, [isPanning]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  const drawnEdges = new Set<string>();
  const edgeElements: React.ReactNode[] = [];

  Object.entries(edges).forEach(([city, neighbors]) => {
    neighbors.forEach((neighbor: string) => {
      const key = [city, neighbor].sort().join('--');
      if (drawnEdges.has(key)) return;
      drawnEdges.add(key);

      const a = nodes[city];
      const b = nodes[neighbor];
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

      edgeElements.push(
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

  const nodeElements = Object.entries(nodes).map(([id, node]) => {
    return renderNode(id, node, pctToPx(node.pct_x, node.pct_y));
  });

  const zoomPercent = Math.round(scale * 100);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={DISPLAY_W}
        height={DISPLAY_H}
        style={{
          border: '1px solid #ccc',
          borderRadius: 4,
          cursor: isPanning ? 'grabbing' : 'grab',
          backgroundColor: '#fff'
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${offsetX}, ${offsetY}) scale(${scale})`}
           style={{ transformOrigin: '0 0' }}>
          {backgroundImage && <image href={backgroundImage} width={DISPLAY_W} height={DISPLAY_H} />}
          {edgeElements}
          {nodeElements}
        </g>
      </svg>

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
  );
};
