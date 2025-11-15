export type PortDirection = "in" | "out";

export interface PortDefinition {
  key: string;
  label: string;
  description?: string;
  accepts: string[];
  required?: boolean;
  direction: PortDirection;
}

export interface ElementPropertySchema {
  type?: "string" | "number" | "boolean";
  default?: unknown;
  enum?: string[];
  widget?: "textarea" | "code";
  minimum?: number;
  maximum?: number;
}

export interface ElementDefinition {
  type: string;
  version: string;
  label: string;
  icon?: string;
  summary?: string;
  inputs: Record<string, PortDefinition>;
  outputs: Record<string, PortDefinition>;
  propsSchema: Record<string, ElementPropertySchema>;
  runtime?: {
    executor: "client" | "server" | "notebook";
    handler: string;
  };
}

export interface NodeInstance {
  id: string;
  type: string;
  label: string;
  props: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  from: { node: string; port: string };
  to: { node: string; port: string };
}

export interface GraphMetadata {
  tags?: string[];
  createdBy?: string;
  updatedAt?: string;
}

export interface GraphDefinition {
  id: string;
  name: string;
  tenantId: string;
  workspaceId: string;
  nodes: NodeInstance[];
  edges: GraphEdge[];
  metadata?: GraphMetadata;
}

export interface ElementsTheme {
  name: string;
  tokens: {
    surface: string;
    surfaceAlt: string;
    border: string;
    text: string;
    textMuted: string;
    accent: string;
    accentMuted: string;
    background: string;
  };
}

export type ElementsRegistryMap = Record<string, ElementDefinition>;
