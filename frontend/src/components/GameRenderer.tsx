import React from 'react';
import { Stage, Layer, Circle, Line, Text, RegularPolygon } from 'react-konva';

interface RendererProps {
  boardType: 'hex' | 'graph';
  width?: number;
  height?: number;

  // Graph Props
  graphEdges?: Array<{ start: {x: number, y: number}, end: {x: number, y: number} }>;
  graphNodes?: Array<{ id: string, x: number, y: number, color: string, stroke: string, hasTrain: boolean, isInvested: boolean }>;
  onNodeClick?: (id: string) => void;

  // Hex Props
  hexes?: Array<{ id: string, q: number, r: number, color: string }>;
  onHexClick?: (q: number, r: number) => void;
}

export const GameRenderer: React.FC<RendererProps> = ({
  boardType,
  width = 600,
  height = 400,
  graphEdges = [],
  graphNodes = [],
  onNodeClick,
  hexes = [],
  onHexClick
}) => {

  const HEX_RADIUS = 30;
  const HEX_WIDTH = Math.sqrt(3) * HEX_RADIUS;
  const HEX_HEIGHT = 2 * HEX_RADIUS;

  return (
    <div className="bg-white shadow-lg rounded-lg overflow-hidden border">
      <Stage width={width} height={height}>
        <Layer>
          {boardType === 'graph' && (
            <>
              {graphEdges.map((edge, i) => (
                <Line
                  key={`edge-${i}`}
                  points={[edge.start.x, edge.start.y, edge.end.x, edge.end.y]}
                  stroke="#ccc"
                  strokeWidth={3}
                />
              ))}

              {graphNodes.map((node) => (
                <React.Fragment key={node.id}>
                  <Circle
                    x={node.x}
                    y={node.y}
                    radius={15}
                    fill={node.color}
                    stroke={node.stroke}
                    strokeWidth={node.stroke === '#333' ? 2 : 4}
                    onClick={() => onNodeClick && onNodeClick(node.id)}
                    onTap={() => onNodeClick && onNodeClick(node.id)}
                  />
                  {node.hasTrain && (
                    <Circle x={node.x} y={node.y} radius={8} fill="#ef4444" listening={false} />
                  )}
                  <Text
                    x={node.x - 30}
                    y={node.y - 30}
                    text={node.id}
                    fontSize={12}
                    fontStyle="bold"
                    align="center"
                    width={60}
                    listening={false}
                  />
                  {node.isInvested && (
                    <Text
                      x={node.x - 5}
                      y={node.y - 5}
                      text="$"
                      fontSize={12}
                      fill="#fff"
                      listening={false}
                    />
                  )}
                </React.Fragment>
              ))}
            </>
          )}

          {boardType === 'hex' && (
            <>
              {hexes.map((hex) => {
                const x = HEX_WIDTH * (hex.q + hex.r / 2) + 100;
                const y = HEX_HEIGHT * (3 / 4) * hex.r + 100;

                return (
                  <React.Fragment key={hex.id}>
                    <RegularPolygon
                      x={x}
                      y={y}
                      sides={6}
                      radius={30}
                      fill={hex.color}
                      stroke="#333"
                      strokeWidth={1}
                      onClick={() => onHexClick && onHexClick(hex.q, hex.r)}
                      onTap={() => onHexClick && onHexClick(hex.q, hex.r)}
                    />
                    <Text
                      x={x - 15}
                      y={y - 5}
                      text={hex.id}
                      fontSize={10}
                      fill="#666"
                      listening={false}
                    />
                  </React.Fragment>
                );
              })}
            </>
          )}
        </Layer>
      </Stage>
    </div>
  );
};
