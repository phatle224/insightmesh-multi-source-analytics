"use client";

import { GraphIcon, TableIcon, XIcon } from "@phosphor-icons/react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { DatasourceEntity, DatasourceRelationship } from "@/lib/datasources";

interface RelationshipExplorerProps {
  entities: DatasourceEntity[];
  relationships: DatasourceRelationship[];
}

interface JoinPath {
  entities: string[];
  relationshipIds: Set<string>;
}

function findJoinPath(
  relationships: DatasourceRelationship[],
  start: string,
  end: string,
): JoinPath | null {
  if (start === end) return { entities: [start], relationshipIds: new Set() };
  const adjacency = new Map<string, Array<{ next: string; relationshipId: string }>>();
  for (const relationship of relationships) {
    if (!relationship.generation_eligible) continue;
    adjacency.set(relationship.source, [
      ...(adjacency.get(relationship.source) ?? []),
      { next: relationship.target, relationshipId: relationship.id },
    ]);
    adjacency.set(relationship.target, [
      ...(adjacency.get(relationship.target) ?? []),
      { next: relationship.source, relationshipId: relationship.id },
    ]);
  }

  const queue = [start];
  const previous = new Map<string, { entity: string; relationshipId: string }>();
  const visited = new Set([start]);
  while (queue.length) {
    const current = queue.shift();
    if (!current) break;
    for (const edge of adjacency.get(current) ?? []) {
      if (visited.has(edge.next)) continue;
      visited.add(edge.next);
      previous.set(edge.next, { entity: current, relationshipId: edge.relationshipId });
      if (edge.next === end) {
        const entities = [end];
        const relationshipIds = new Set<string>();
        let cursor = end;
        while (cursor !== start) {
          const step = previous.get(cursor);
          if (!step) return null;
          relationshipIds.add(step.relationshipId);
          entities.unshift(step.entity);
          cursor = step.entity;
        }
        return { entities, relationshipIds };
      }
      queue.push(edge.next);
    }
  }
  return null;
}

function relationshipLabel(relationship: DatasourceRelationship) {
  const source = relationship.source_field
    ? `${relationship.source}.${relationship.source_field}`
    : relationship.source;
  const target = relationship.target_field
    ? `${relationship.target}.${relationship.target_field}`
    : relationship.target;
  return `${source} → ${target}`;
}

function RelationshipGraph({
  entities,
  relationships,
  path,
}: RelationshipExplorerProps & { path: JoinPath | null }) {
  const names = entities.map((entity) => `${entity.schema_name}.${entity.name}`);
  const columnCount = Math.min(3, Math.max(1, names.length));
  const rowCount = Math.ceil(names.length / columnCount);
  const width = 840;
  const height = Math.max(180, rowCount * 150 + 30);
  const nodeWidth = 200;
  const nodeHeight = 68;
  const positions = new Map(
    names.map((name, index) => {
      const column = index % columnCount;
      const row = Math.floor(index / columnCount);
      return [
        name,
        {
          x: 20 + column * ((width - 40 - nodeWidth) / Math.max(1, columnCount - 1)),
          y: 25 + row * 150,
        },
      ];
    }),
  );
  const pathEntities = new Set(path?.entities ?? []);

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="block h-auto min-h-64 w-full"
        role="img"
        aria-labelledby="relationship-graph-title relationship-graph-description"
      >
        <title id="relationship-graph-title">Datasource relationship graph</title>
        <desc id="relationship-graph-description">
          {path
            ? `Selected join path: ${path.entities.join(" to ")}`
            : `${names.length} entities connected by ${relationships.length} relationships. Use the labeled endpoint controls above to highlight a generation-eligible join path.`}
        </desc>
        {relationships.map((relationship) => {
          const source = positions.get(relationship.source);
          const target = positions.get(relationship.target);
          if (!source || !target) return null;
          const selected = path?.relationshipIds.has(relationship.id) ?? false;
          return (
            <line
              key={relationship.id}
              x1={source.x + nodeWidth / 2}
              y1={source.y + nodeHeight / 2}
              x2={target.x + nodeWidth / 2}
              y2={target.y + nodeHeight / 2}
              className={selected ? "stroke-accent" : "stroke-border-strong"}
              strokeWidth={selected ? 7 : 3}
              strokeDasharray={relationship.provenance === "inferred" ? "10 7" : undefined}
            />
          );
        })}
        {names.map((name) => {
          const position = positions.get(name);
          if (!position) return null;
          const selected = pathEntities.has(name);
          const [schema, ...entityParts] = name.split(".");
          return (
            <g key={name}>
              <rect
                x={position.x}
                y={position.y}
                width={nodeWidth}
                height={nodeHeight}
                rx={10}
                className={selected ? "fill-primary stroke-primary" : "fill-card stroke-border-strong"}
                strokeWidth={selected ? 4 : 2}
              />
              <text
                x={position.x + 16}
                y={position.y + 27}
                className={selected ? "fill-on-primary font-mono text-[13px] font-semibold" : "fill-text font-mono text-[13px] font-semibold"}
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

export function RelationshipExplorer({ entities, relationships }: RelationshipExplorerProps) {
  const entityNames = useMemo(
    () => entities.map((entity) => `${entity.schema_name}.${entity.name}`),
    [entities],
  );
  const [view, setView] = useState<"graph" | "list">("graph");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const path = useMemo(
    () => (start && end ? findJoinPath(relationships, start, end) : null),
    [end, relationships, start],
  );
  const hasSelection = Boolean(start || end);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-border px-5 py-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <GraphIcon size={20} className="text-primary" aria-hidden />
            <h2 className="font-semibold text-text">Relationship map</h2>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {relationships.length} relationships across {entities.length} entities. Select two
            endpoints to inspect the shortest generation-eligible join path.
          </p>
        </div>
        <div className="flex gap-2" role="group" aria-label="Relationship view">
          <Button
            size="small"
            variant={view === "graph" ? "primary" : "secondary"}
            aria-pressed={view === "graph"}
            onClick={() => setView("graph")}
          >
            <GraphIcon size={17} aria-hidden /> Graph
          </Button>
          <Button
            size="small"
            variant={view === "list" ? "primary" : "secondary"}
            aria-pressed={view === "list"}
            onClick={() => setView("list")}
          >
            <TableIcon size={17} aria-hidden /> Accessible list
          </Button>
        </div>
      </div>

      {relationships.length === 0 ? (
        <div className="p-6 text-sm text-muted-foreground">
          No declared or inferred relationships are available for this datasource.
        </div>
      ) : (
        <div className="space-y-4 p-5">
          <fieldset>
            <legend className="text-sm font-semibold text-text">Join path endpoints</legend>
            <div className="mt-2 grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
              <label className="text-sm text-muted-foreground">
                From entity
                <select
                  className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 text-sm text-text focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  value={start}
                  onChange={(event) => setStart(event.target.value)}
                >
                  <option value="">Choose starting entity</option>
                  {entityNames.map((name) => <option key={name} value={name}>{name}</option>)}
                </select>
              </label>
              <label className="text-sm text-muted-foreground">
                To entity
                <select
                  className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 text-sm text-text focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  value={end}
                  onChange={(event) => setEnd(event.target.value)}
                >
                  <option value="">Choose destination entity</option>
                  {entityNames.map((name) => <option key={name} value={name}>{name}</option>)}
                </select>
              </label>
              <Button
                variant="ghost"
                disabled={!hasSelection}
                onClick={() => { setStart(""); setEnd(""); }}
              >
                <XIcon size={17} aria-hidden /> Clear path
              </Button>
            </div>
          </fieldset>

          <div className="min-h-10 rounded-md border border-border bg-muted/45 px-3 py-2 text-sm" role="status" aria-live="polite">
            {!start || !end ? (
              <span className="text-muted-foreground">Choose both endpoints to highlight a generation-eligible join path.</span>
            ) : path ? (
              <span><strong className="text-text">Selected join path:</strong> <span className="font-mono text-xs text-primary">{path.entities.join(" → ")}</span></span>
            ) : (
              <span className="font-medium text-destructive">No generation-eligible relationship path connects the selected entities. Low-confidence inferred edges remain available in the list for inspection.</span>
            )}
          </div>

          {view === "graph" ? (
            <>
              <RelationshipGraph entities={entities} relationships={relationships} path={path} />
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground" aria-label="Graph legend">
                <span><span className="mr-2 inline-block h-1 w-7 bg-border-strong align-middle" />Declared relationship</span>
                <span><span className="mr-2 inline-block w-7 border-t-2 border-dashed border-border-strong align-middle" />Inferred relationship</span>
                <span><span className="mr-2 inline-block h-1.5 w-7 bg-accent align-middle" />Selected join path</span>
              </div>
            </>
          ) : (
            <div className="overflow-x-auto" tabIndex={0} aria-label="Scrollable relationship list">
              <table className="w-full min-w-[52rem] border-collapse text-left text-sm">
                <caption className="sr-only">Accessible list of datasource relationships and join-path status.</caption>
                <thead className="bg-muted/70 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr><th className="px-3 py-3">Relationship</th><th className="px-3 py-3">Provenance</th><th className="px-3 py-3">Confidence</th><th className="px-3 py-3">Query generation</th><th className="px-3 py-3">Path status</th></tr>
                </thead>
                <tbody>
                  {relationships.map((relationship) => {
                    const selected = path?.relationshipIds.has(relationship.id) ?? false;
                    return (
                      <tr key={relationship.id} className={selected ? "border-t border-border bg-accent/10" : "border-t border-border"}>
                        <td className="px-3 py-3"><p className="font-mono text-xs text-text">{relationshipLabel(relationship)}</p><p className="mt-1 text-xs text-muted-foreground">{relationship.evidence.join("; ")}</p></td>
                        <td className="px-3 py-3">{relationship.provenance === "declared" ? "Declared" : "Inferred"}</td>
                        <td className="px-3 py-3 font-mono text-xs">{Math.round(relationship.confidence * 100)}%</td>
                        <td className="px-3 py-3">{relationship.generation_eligible ? "Included" : "Excluded"}</td>
                        <td className="px-3 py-3 font-medium">{selected ? "In selected path" : "Not selected"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
