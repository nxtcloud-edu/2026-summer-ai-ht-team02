import { useMemo } from "react";

// --- Types ---

export interface NodeData {
  id: number;
  floor_id: number;
  x: number;
  y: number;
  node_type: string; // path, exit, stair, elevator, room
  label?: string | null;
}

export interface EdgeData {
  id: number;
  floor_id: number;
  from_node_id: number;
  to_node_id: number;
  distance?: number | null;
  is_blocked: number;
}

export interface WorkerMarker {
  user_id: number;
  x: number;
  y: number;
  status?: string;
  is_moving?: boolean;
}

export interface FireZone {
  x: number;
  y: number;
  radius: number;
}

export interface FloorCanvasProps {
  width?: number;
  height?: number;
  floorPlanUrl?: string | null;
  nodes?: NodeData[];
  edges?: EdgeData[];
  workers?: WorkerMarker[];
  routePath?: NodeData[];
  fireZones?: FireZone[];
  onNodeClick?: (nodeId: number) => void;
}

// --- Node Style ---

function getNodeColor(nodeType: string): string {
  switch (nodeType) {
    case "exit":
      return "#22c55e"; // green-500
    case "stair":
      return "#3b82f6"; // blue-500
    case "elevator":
      return "#8b5cf6"; // violet-500
    case "room":
      return "#f59e0b"; // amber-500
    default:
      return "#9ca3af"; // gray-400
  }
}

/**
 * 노드 반경 — viewBox에 비례하여 계산
 * width에 기반한 상대 크기 반환 (기본 800px → 30000mm 스케일 대응)
 */
function getNodeRadius(nodeType: string, viewWidth: number): number {
  const scale = viewWidth / 800;
  const base = nodeType === "exit" ? 8 : nodeType === "stair" || nodeType === "elevator" ? 7 : 5;
  return base * scale;
}

// --- Component ---

export default function FloorCanvas({
  width = 800,
  height = 600,
  floorPlanUrl,
  nodes = [],
  edges = [],
  workers = [],
  routePath = [],
  fireZones = [],
  onNodeClick,
}: FloorCanvasProps) {
  // 노드 좌표 맵 (edge 렌더링용)
  const nodeMap = useMemo(() => {
    const map = new Map<number, NodeData>();
    for (const node of nodes) {
      map.set(node.id, node);
    }
    return map;
  }, [nodes]);

  // 경로 polyline 좌표
  const routePoints = useMemo(() => {
    if (routePath.length === 0) return "";
    return routePath.map((n) => `${n.x},${n.y}`).join(" ");
  }, [routePath]);

  // viewBox 크기에 따른 스케일 팩터
  const scale = width / 800;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-full border border-gray-200 rounded bg-white"
      style={{ maxHeight: "500px" }}
    >
      {/* Layer 1: 도면 배경 이미지 */}
      {floorPlanUrl && (
        <image
          href={floorPlanUrl.startsWith("http") ? floorPlanUrl : `http://localhost:8000${floorPlanUrl}`}
          x={0}
          y={0}
          width={width}
          height={height}
          preserveAspectRatio="xMidYMid meet"
          opacity={0.3}
        />
      )}

      {/* Layer 2: 엣지 */}
      {edges.map((edge) => {
        const from = nodeMap.get(edge.from_node_id);
        const to = nodeMap.get(edge.to_node_id);
        if (!from || !to) return null;

        return (
          <line
            key={`edge-${edge.id}`}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke={edge.is_blocked ? "#ef4444" : "#d1d5db"}
            strokeWidth={edge.is_blocked ? 3 * scale : 2 * scale}
            strokeDasharray={edge.is_blocked ? `${12 * scale},${6 * scale}` : undefined}
            opacity={0.8}
          />
        );
      })}

      {/* Layer 3: 화재 구역 */}
      {fireZones.map((zone, idx) => (
        <circle
          key={`fire-${idx}`}
          cx={zone.x}
          cy={zone.y}
          r={zone.radius * scale}
          fill="rgba(239, 68, 68, 0.2)"
          stroke="#ef4444"
          strokeWidth={3 * scale}
          strokeDasharray={`${8 * scale},${4 * scale}`}
        >
          <animate
            attributeName="opacity"
            values="0.3;0.6;0.3"
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>
      ))}

      {/* Layer 4: 경로 하이라이트 */}
      {routePoints && (
        <polyline
          points={routePoints}
          fill="none"
          stroke="#22c55e"
          strokeWidth={6 * scale}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.8}
          strokeDasharray={`${20 * scale},${10 * scale}`}
        >
          <animate
            attributeName="stroke-dashoffset"
            from={`${40 * scale}`}
            to="0"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </polyline>
      )}

      {/* Layer 5: 노드 */}
      {nodes.map((node) => (
        <g
          key={`node-${node.id}`}
          onClick={() => onNodeClick?.(node.id)}
          style={{ cursor: onNodeClick ? "pointer" : "default" }}
        >
          <circle
            cx={node.x}
            cy={node.y}
            r={getNodeRadius(node.node_type, width)}
            fill={getNodeColor(node.node_type)}
            stroke="#fff"
            strokeWidth={2 * scale}
          />
          {node.label && (
            <text
              x={node.x}
              y={node.y - 16 * scale}
              textAnchor="middle"
              fontSize={12 * scale}
              fill="#374151"
              fontWeight={500}
            >
              {node.label}
            </text>
          )}
        </g>
      ))}

      {/* Layer 6: 근로자 위치 마커 */}
      {workers.map((worker) => (
        <g key={`worker-${worker.user_id}`}>
          <circle
            cx={worker.x}
            cy={worker.y}
            r={14 * scale}
            fill="rgba(59, 130, 246, 0.2)"
            stroke="none"
          >
            <animate
              attributeName="r"
              values={`${10 * scale};${18 * scale};${10 * scale}`}
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
          <circle
            cx={worker.x}
            cy={worker.y}
            r={7 * scale}
            fill={worker.status === "unconscious" ? "#ef4444" : "#3b82f6"}
            stroke="#fff"
            strokeWidth={2 * scale}
          />
        </g>
      ))}

      {/* 데이터 없을 때 안내 */}
      {nodes.length === 0 && !floorPlanUrl && (
        <text
          x={width / 2}
          y={height / 2}
          textAnchor="middle"
          fontSize={14 * scale}
          fill="#9ca3af"
        >
          도면 데이터를 불러오는 중...
        </text>
      )}
    </svg>
  );
}
