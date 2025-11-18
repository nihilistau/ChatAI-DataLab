# Kitchen Framework

The Kitchen is the programmable notebook environment that defines every Playground. Recipes describe layouts, widget bindings, data access patterns, and workflows; Cookbooks are curated collections of Recipes that walk someone through designing, creating, and deploying a Playground for their tenant.

## Onboarding
- Skim `ONBOARDING.md` for a quick glossary (Playground, Kitchen, Recipe, Cookbook, Control Capsule).
- Launch `kitchen/notebooks/welcome_cookbook.ipynb` to load the Welcome Cookbook (auto-opens on first run).
- Legacy notebooks still live under `datalab/notebooks/`; reference them when porting older analyses into Recipes.

### Welcome Cookbook structure
1. **Orientation & Overview** – explains concepts, shows miniature widget updates, and links to the Playground Architecture guide.
2. **Getting Started** – scaffolds your first Playground namespace, helper functions, and layout tree.
3. **Tutorial Build** – produces a working frontend with inputs, outputs, telemetry tiles, and backend bindings.
4. **Sample Playground** – highlights how frontend, backend, and Kitchen exchange manifests in a realistic scenario (support triage board).
5. **Advanced Integrations** – connects to remote data sources (Cosmos DB/Postgres), demonstrates auth hooks, and showcases multi-tenant patterns.

## Extending Kitchen
- Use `EXTENSION_TEMPLATE.md` for extension instructions and code samples.
- Add new Recipes under `kitchen/notebooks/` and register them inside the relevant Cookbook manifest.
- Create custom widgets in `kitchen/widgets/`—they immediately become available to Recipes once exported.
- Add utility scripts (layout DSLs, manifest helpers) in `kitchen/scripts/` so Recipes stay concise.

## Sharing
- Document your extensions and share Cookbooks through Control Capsules or the repo's docs.
- Collaborate in the Kitchen Playground by pairing through the Welcome Cookbook or custom Cookbooks.
