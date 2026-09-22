"use client";

import { GraphIcon } from "@phosphor-icons/react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { DatasourceEntity, DatasourceRelationship } from "@/lib/datasources";

interface RelationshipExplorerProps {
  datasourceId?: string;
  entities: DatasourceEntity[];
  relationships: DatasourceRelationship[];
}

interface NodePosition {
  x: number;
  y: number;
}

type NodePositions = Record<string, NodePosition>;
type InteractionMode = "inspect" | "arrange";

const GRAPH_WIDTH = 840;
const NODE_WIDTH = 200;
const NODE_HEIGHT = 68;
const NODE_GAP_Y = 150;
const NODE_PADDING_X = 20;
const NODE_PADDING_Y = 25;
const DRAG_THRESHOLD = 4;

function layoutStorageKey(datasourceId?: string) {
  return datasourceId ? `relationship-layout:${datasourceId}` : null;
}

function defaultNodePositions(names: string[]): { positions: NodePositions; height: number } {
  const columnCount = Math.min(3, Math.max(1, names.length));
  const rowCount = Math.ceil(names.length / columnCount);
  const height = Math.max(180, rowCount * NODE_GAP_Y + 30);
  const positions: NodePositions = {};

  names.forEach((name, index) => {
    const column = index % columnCount;
    const row = Math.floor(index / columnCount);
    positions[name] = {
      x: NODE_PADDING_X + column * ((GRAPH_WIDTH - 40 - NODE_WIDTH) / Math.max(1, columnCount - 1)),
      y: NODE_PADDING_Y + row * NODE_GAP_Y,
    };
  });

  return { positions, height };
}

function loadSavedPositions(datasourceId: string | undefined, names: string[]): NodePositions {
  const key = layoutStorageKey(datasourceId);
  if (!key || typeof window === "undefined") return {};

  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(key) ?? "null");
    if (!value || typeof value !== "object") return {};
    const saved = value as Record<string, unknown>;
    return Object.fromEntries(
      names.flatMap((name) => {
        const position = saved[name];
        if (!position || typeof position !== "object") return [];
        const { x, y } = position as { x?: unknown; y?: unknown };
        return typeof x === "number" && typeof y === "number" && Number.isFinite(x) && Number.isFinite(y)
          ? [[name, { x, y }]]
          : [];
      }),
    );
  } catch {
    return {};
  }
}

function RelationshipGraph({
  entities,
  relationships,
  selectedEntity,
  positions,
  mode,
  onSelectEntity,
  onMoveEntity,
}: {
  entities: DatasourceEntity[];
  relationships: DatasourceRelationship[];
  selectedEntity: string | null;
  positions: NodePositions;
  mode: InteractionMode;
  onSelectEntity: (name: string) => void;
  onMoveEntity: (name: string, position: NodePosition) => void;
}) {
  const names = entities.map((entity) => `${entity.schema_name}.${entity.name}`);
  const { positions: defaults, height } = defaultNodePositions(names);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{
    name: string;
    pointerId: number;
    startX: number;
    startY: number;
    position: NodePosition;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const graphId = useId().replaceAll(":", "");
  const titleId = `relationship-graph-title-${graphId}`;
  const descriptionId = `relationship-graph-description-${graphId}`;
  const relatedEntities = useMemo(() => {
    if (!selectedEntity) return new Set<string>();
    const related = new Set<string>([selectedEntity]);
    relationships.forEach((relationship) => {
      if (relationship.source === selectedEntity) related.add(relationship.target);
      if (relationship.target === selectedEntity) related.add(relationship.source);
    });
    return related;
  }, [relationships, selectedEntity]);

  const getPosition = (name: string) => positions[name] ?? defaults[name];
  const clampPosition = (position: NodePosition) => ({
    x: Math.max(0, Math.min(GRAPH_WIDTH - NODE_WIDTH, position.x)),
    y: Math.max(0, Math.min(height - NODE_HEIGHT, position.y)),
  });
  const pointerPosition = (event: React.PointerEvent<SVGSVGElement>, start: NodePosition) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return start;
    return clampPosition({
      x: start.x + ((event.clientX - (dragRef.current?.startX ?? event.clientX)) * GRAPH_WIDTH) / rect.width,
      y: start.y + ((event.clientY - (dragRef.current?.startY ?? event.clientY)) * height) / rect.height,
    });
  };

  const handlePointerDown = (event: React.PointerEvent<SVGGElement>, name: string) => {
    if (mode !== "arrange") return;
    const position = getPosition(name);
    if (!position) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      name,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      position,
    };
    suppressClickRef.current = false;
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (
      Math.abs(event.clientX - drag.startX) > DRAG_THRESHOLD ||
      Math.abs(event.clientY - drag.startY) > DRAG_THRESHOLD
    ) {
      suppressClickRef.current = true;
    }
    onMoveEntity(drag.name, pointerPosition(event, drag.position));
  };

  const handlePointerUp = (event: React.PointerEvent<SVGSVGElement>) => {
    if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
  };

  const moveByKeyboard = (event: React.KeyboardEvent<SVGGElement>, name: string) => {
    if (mode !== "arrange") return;
    const position = getPosition(name);
    if (!position) return;
    const step = event.shiftKey ? 50 : 20;
    const delta = {
      ArrowLeft: { x: -step, y: 0 },
      ArrowRight: { x: step, y: 0 },
      ArrowUp: { x: 0, y: -step },
      ArrowDown: { x: 0, y: step },
    }[event.key];
    if (!delta) return;
    event.preventDefault();
    onMoveEntity(name, clampPosition({ x: position.x + delta.x, y: position.y + delta.y }));
  };

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${GRAPH_WIDTH} ${height}`}
        className="block h-auto min-h-64 w-full"
        role="img"
        aria-labelledby={`${titleId} ${descriptionId}`}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <title id={titleId}>Datasource relationship graph</title>
        <desc id={descriptionId}>
          {selectedEntity
            ? `Selected ${selectedEntity}. Directly related entities are highlighted.`
            : `${names.length} entities connected by ${relationships.length} relationships. Select an entity to highlight its direct relationships.`}
        </desc>
        {relationships.map((relationship) => {
          const source = getPosition(relationship.source);
          const target = getPosition(relationship.target);
          if (!source || !target) return null;
          const connectedToSelection = Boolean(
            selectedEntity &&
              (relationship.source === selectedEntity || relationship.target === selectedEntity),
          );
          const dimmed = Boolean(selectedEntity && !connectedToSelection);
          return (
            <line
              key={relationship.id}
              x1={source.x + NODE_WIDTH / 2}
              y1={source.y + NODE_HEIGHT / 2}
              x2={target.x + NODE_WIDTH / 2}
              y2={target.y + NODE_HEIGHT / 2}
              className={connectedToSelection ? "stroke-accent" : "stroke-border-strong"}
              strokeWidth={connectedToSelection ? 5 : 3}
              strokeDasharray={relationship.provenance === "inferred" ? "10 7" : undefined}
              opacity={dimmed ? 0.25 : 1}
              aria-hidden="true"
            />
          );
        })}
        {names.map((name) => {
          const position = getPosition(name);
          if (!position) return null;
          const selected = selectedEntity === name;
          const related = relatedEntities.has(name);
          const dimmed = Boolean(selectedEntity && !related);
          const [schema, ...entityParts] = name.split(".");
          return (
            <g
              key={name}
              tabIndex={0}
              role="button"
              aria-label={`${name}${selected ? ", selected" : ""}${related && !selected ? ", directly related" : ""}`}
              aria-pressed={selected}
              className={mode === "arrange" ? "cursor-move touch-none select-none outline-none" : "cursor-pointer outline-none"}
              opacity={dimmed ? 0.42 : 1}
              onClick={() => {
                if (suppressClickRef.current) {
                  suppressClickRef.current = false;
                  return;
                }
                onSelectEntity(name);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectEntity(name);
                } else {
                  moveByKeyboard(event, name);
                }
              }}
              onPointerDown={(event) => handlePointerDown(event, name)}
            >
              <rect
                x={position.x}
                y={position.y}
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={10}
                className={selected ? "fill-primary stroke-primary" : related ? "fill-card stroke-accent" : "fill-card stroke-border-strong"}
                strokeWidth={selected ? 4 : related ? 3 : 2}
              />
              <text
                x={position.x + 16}
                y={position.y + 27}
                className={selected ? "fill-on-primary font-mono text-[13px] font-semibold" : related ? "fill-text font-mono text-[13px] font-bold" : "fill-text font-mono text-[13px] font-semibold"}
              >
                {entityParts.join(".")}
              </text>
              <text
                x={position.x + 16}
                y={position.y + 49}
                className={selected ? "fill-on-primary text-[11px]" : "fill-muted-foreground text-[11px]"}
              >
                schema: {schema}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function RelationshipExplorer({ datasourceId, entities, relationships }: RelationshipExplorerProps) {
  const entityNames = useMemo(() => entities.map((entity) => `${entity.schema_name}.${entity.name}`), [entities]);
  const [mode, setMode] = useState<InteractionMode>("inspect");
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [positions, setPositions] = useState<NodePositions>(() => loadSavedPositions(datasourceId, entityNames));
  const layoutKey = layoutStorageKey(datasourceId);

  useEffect(() => {
    if (!layoutKey || typeof window === "undefined") return;
    window.localStorage.setItem(layoutKey, JSON.stringify(positions));
  }, [layoutKey, positions]);

  const savePosition = (name: string, position: NodePosition) => {
    setPositions((current) => ({ ...current, [name]: position }));
  };

  const resetLayout = () => {
    setPositions({});
    if (layoutKey && typeof window !== "undefined") window.localStorage.removeItem(layoutKey);
  };

  if (entities.length === 0) {
    return (
      <Card className="overflow-hidden">
        <div className="p-6 text-sm text-muted-foreground">No entities are available for this datasource.</div>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-border px-5 py-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <GraphIcon size={20} className="text-primary" aria-hidden />
            <h2 className="font-semibold text-text">Relationship map</h2>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {relationships.length} relationships across {entities.length} entities. Select an entity to highlight its direct relationships, or arrange the map to your preference.
          </p>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-muted/25 p-3">
          <div>
            <p className="text-sm font-semibold text-text">ERD interaction</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {mode === "inspect" ? "Click an entity to highlight directly related entities." : "Drag entities to arrange the map. Arrow keys also move the focused entity."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="ERD interaction mode">
            <Button size="small" variant={mode === "inspect" ? "primary" : "secondary"} aria-pressed={mode === "inspect"} onClick={() => setMode("inspect")}>Inspect</Button>
            <Button size="small" variant={mode === "arrange" ? "primary" : "secondary"} aria-pressed={mode === "arrange"} onClick={() => setMode("arrange")}>Arrange / drag</Button>
            <Button size="small" variant="ghost" onClick={resetLayout}>Reset layout</Button>
          </div>
        </div>

        <div className="min-h-10 rounded-md border border-border bg-muted/45 px-3 py-2 text-sm" role="status" aria-live="polite">
          {selectedEntity ? (
            <span><strong className="text-text">Selected entity:</strong> <span className="font-mono text-xs text-primary">{selectedEntity}</span>. Direct relationships are highlighted.</span>
          ) : (
            <span className="text-muted-foreground">Click an entity to highlight its direct relationships.</span>
          )}
          {selectedEntity ? <button type="button" className="ml-2 font-semibold text-primary underline-offset-2 hover:underline" onClick={() => setSelectedEntity(null)}>Clear entity</button> : null}
        </div>

        <RelationshipGraph
          entities={entities}
          relationships={relationships}
          selectedEntity={selectedEntity}
          positions={positions}
          mode={mode}
          onSelectEntity={(name) => setSelectedEntity((current) => current === name ? null : name)}
          onMoveEntity={savePosition}
        />
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground" aria-label="Relationship legend">
          <span><span className="mr-2 inline-block h-1 w-7 bg-border-strong align-middle" />Declared relationship</span>
          <span><span className="mr-2 inline-block w-7 border-t-2 border-dashed border-border-strong align-middle" />Inferred relationship</span>
          <span><span className="mr-2 inline-block h-1.5 w-7 bg-accent align-middle" />Related to selected entity</span>
        </div>
      </div>
    </Card>
  );
}
