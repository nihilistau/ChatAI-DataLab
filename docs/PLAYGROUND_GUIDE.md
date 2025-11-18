# Playground Architecture Guide

> Canonical reference for how the frontend, backend, and Kitchen collaborate to form a Playground.

## Vocabulary

| Term | Definition |
| --- | --- |
| **Playground** | A deployable trio of frontend, backend, and Kitchen assets that work together to deliver a tailored experience for a specific goal or tenant. Designing, creating, and deploying a Playground is the core workflow for this framework. |
| **Kitchen** | The notebook environment (formerly "DataLab") where builders author logic, workflows, layouts, and data wiring through Recipes. The Kitchen is the system-of-record for how a Playground behaves. |
| **Recipe** | A single Notebook (or notebook page) that bundles UI layout definitions, backend binding directives, and workflow automation helpers. Recipes focus on one topic (e.g., onboarding, telemetry, advanced integrations). |
| **Cookbook** | A curated set of Recipes that guide a user through building or operating a Playground. Cookbooks enable progressive disclosure—from quick starts to deep dives.
| **Welcome Cookbook** | The default Cookbook that loads the first time a Kitchen opens. It ships five Recipes: Overview, Getting Started, Tutorial Build, Showcase Playground, and Advanced Integrations (details below). |
| **Control Capsule** | The distribution artifact that bundles the source code plus configuration for one or more Playgrounds. |
| **Tenant / Space** | A logical owner or team that provisions Playgrounds. Multi-tenant support is achieved by namespacing Kitchen state, backend resources, and frontend runtime configs per tenant. |

## Component Responsibilities

### Frontend — Control Surface

- Renders layouts, widgets, and visual telemetry authored in Recipes.
- Avoids domain logic; instead it reacts to declarative instructions provided by the backend/Kitchen handshake (layout schema, widget registry, action contracts).
- Exposes instrumentation hooks (inputs, telemetry streams, widget events) that the backend can route anywhere.
- Provides the human-centered design surface for monitoring, control, and storytelling.

### Backend — Orchestration & Safety Layer

- Serves the compiled frontend, static assets, and widget manifests.
- Provides a stable API for the Kitchen to push layout definitions, data contracts, and signal routing instructions.
- Manages session state, auth, and tenant scoping so each Playground remains isolated.
- Facilitates low-latency bridging between live Notebook edits and what the frontend renders.
- Hosts integration connectors (LLMs, remote data stores) so Recipes call into hardened services rather than embedding credentials in notebooks.

### Kitchen — Live System Designer

- Runs as an opinionated Jupyter environment with helper libraries for:
  - Declaring UI layout trees (sections, widgets, interactive canvases).
  - Binding widgets to backend endpoints or direct dataframes.
  - Defining workflows (prompt pipelines, telemetry aggregations, alert rules).
  - Managing datasets, secrets, and remote resources per tenant.
- Emits structured manifests (Recipes) that the backend can hot-reload without restarts.
- Offers tooling to snapshot or clone Recipes so builders can templatize proven patterns.
- Acts as the primary programming interface—for scripting, automation, and experimentation.

## Interaction Lifecycle

| Phase | Kitchen Role | Backend Role | Frontend Role |
| --- | --- | --- | --- |
| **Design** | Author Recipes, set layout + widget schema, configure data sources. | Validate manifests, version Recipes, expose schema diffs. | Reflect placeholder layouts, provide live preview scaffolding. |
| **Compose** | Chain Recipes into a Cookbook, attach workflow automation, define permissions. | Wire multi-tenant routing, provision endpoints, emit telemetry contracts. | Display Cookbook navigation to switch Recipes on demand. |
| **Deploy** | Publish Cookbook revisions; optionally freeze versions per tenant. | Promote manifests to production, hydrate caches, maintain compatibility gates. | Load the targeted revision, lazy-load assets, and keep state in sync. |
| **Observe** | Run diagnostics notebooks, iterate on KPIs, tweak widgets. | Stream telemetry/events to Kitchen, enforce guardrails, throttle workloads. | Surface monitoring widgets, command panels, and alert banners for operators. |

## Multi-Tenant & User Management Considerations

- **Namespaces:** Every Playground is referenced as `<tenant>/<playground>/<revision>`. The backend enforces namespace isolation, while the Kitchen stores Recipes in tenant-specific folders.
- **Roles:** Default roles include `builder` (full Kitchen access), `operator` (frontend control + limited Kitchen execution), and `viewer` (frontend only).
- **State sync:** Recipes publish versioned manifests; Frontend sessions subscribe to the manifest associated with their tenant/role. Backend websockets broadcast deltas when the Kitchen saves a cell.
- **Auditing:** Each manifest change is logged with `{tenant, playground, recipe, author, checksum}` so operators can roll back or diff states quickly.

## Welcome Cookbook Specification

| Recipe | Purpose | Key Elements |
| --- | --- | --- |
| **1. Orientation & Overview** | Explain core vocabulary (Playground, Kitchen, Recipes) and show micro-examples. | Textual tour, inline code cells that live-update a sample widget, diagram of data flow. |
| **2. Getting Started** | Walk through provisioning a new Playground, connecting to a tenant namespace, and pushing the first layout. | Cell blocks for scaffolding a layout tree, helper function demonstrations, link to LabControl commands. |
| **3. Tutorial Build** | End-to-end walkthrough producing a functional frontend with form inputs, streaming output, and telemetry tiles. | Stepwise manifests, backend connector bindings, preview toggles, automated tests. |
| **4. Sample Playground** | Showcase how the three systems interact with a slightly more complete scenario (e.g., support triage board). | Multi-pane layout, workflow automation sample, depiction of backend routes triggered by widgets. |
| **5. Advanced Integrations** | Demonstrate remote data (Cosmos DB / Postgres), authentication, and external API stitching. | Secrets management helpers, multi-tenant routing example, resilience patterns and retry snippets. |

Each Recipe should finish with "Try this next" callouts that deep-link to other Cookbooks or recipes (metrics, observability, deployment playbooks).

## Feature Roadmap (Kitchen-centric)

1. **Layout DSL Library** — A Python module that translates declarative Recipe specs into strongly typed manifests shared with the frontend.
2. **Live Preview Service** — Backend websockets that broadcast manifest diffs to the frontend when a Notebook cell completes.
3. **Cookbook Packager** — CLI/Notebook widget that exports a Cookbook (including assets/data) into a versioned Control Capsule.
4. **Tenant Sandbox Manager** — Backend API + Kitchen helpers for spinning up isolated sandboxes per customer.
5. **Telemetry Hooks** — Standardized metrics emitted by each Playground so operators can monitor adoption and errors per tenant.

These initiatives ensure Playgrounds stay modular, reproducible, and multi-tenant ready as user management scenarios expand.
