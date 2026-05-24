# Workshop Framework

The Workshop is the programmable notebook environment that defines every Horizon Relay. Recipes describe layouts, widget bindings, data access patterns, and workflows; Cookbooks are curated collections of Recipes that walk someone through designing, creating, and deploying a Relay for their tenant.

## Onboarding
- Skim `ONBOARDING.md` for a quick glossary (Horizon Relay, Workshop, Recipe, Cookbook).
- Launch `workshop/notebooks/welcome_cookbook.ipynb` to load the Welcome Cookbook (auto-opens on first run).
- Legacy notebooks now live under `legacy/archives/notebooks/`; reference them only when porting older analyses into Recipes.

### Welcome Cookbook structure
1. **Orientation & Overview** – explains concepts, shows miniature widget updates, and links to the Horizon Relay Architecture guide.
2. **Getting Started** – scaffolds your first Relay namespace, helper functions, and layout tree.
3. **Tutorial Build** – produces a working frontend with inputs, outputs, telemetry tiles, and backend bindings.
4. **Sample Relay** – highlights how frontend, backend, and Workshop exchange manifests in a realistic scenario (support triage board).
5. **Advanced Integrations** – connects to remote data sources (Cosmos DB/Postgres), demonstrates auth hooks, and showcases multi-tenant patterns.

## Extending Workshop
- Use `EXTENSION_TEMPLATE.md` for extension instructions and code samples.
- Add new Recipes under `workshop/notebooks/` and register them inside the relevant Cookbook manifest.
- Create custom widgets in `workshop/widgets/`—they immediately become available to Recipes once exported.
- Add utility scripts (layout DSLs, manifest helpers) in `workshop/scripts/` so Recipes stay concise.

## Sharing
- Document your extensions and share Cookbooks through Horizon Relays or the repo's docs.
- Collaborate in the Workshop by pairing through the Welcome Cookbook or custom Cookbooks.
