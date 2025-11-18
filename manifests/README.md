# ChatAI · Playground manifest samples

Use these payloads to test the `scripts/manifest_validator.py` CLI and any MCP agents that ingest Control Center manifests.

## Quick start

```pwsh
python scripts/manifest_validator.py manifests/sample.json --json
```

To validate every manifest (and fail the run if any file is invalid):

```pwsh
python scripts/manifest_validator.py manifests --pattern "*.json"
```

You can copy this folder when drafting new Kitchen manifests so reviewers can lint the payloads locally before pushing to the Ops control plane.
