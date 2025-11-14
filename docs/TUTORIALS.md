# Tutorials & Workflow Recipes

Each recipe walks through the end-to-end hypothesis workflow so newcomers can see how telemetry, Ops control, and notebooks stay in sync.

## 1. Capture → Ops Deck → Artifact Shelf

1. **Start the stack** using Lab Control (`Start-AllLabJobs`) or `./scripts/labctl.sh start-all`.
2. **Submit a prompt** in the ChatAI UI and watch:
   - `PromptRecorder` emit keystroke telemetry.
   - Tail Log show `chat · assistant responded` updates.
   - Ops Deck status chip tick every ~25s.
3. **Promote insights**: drag cards inside Canvas → click “Promote to artifact” and confirm entries show up in `ArtifactsShelf`.
4. **Tag the change**: run `python scripts/project_integrity.py checkpoint --tag tutorial --reason "Captured prompt"` to persist a milestone.

## 2. Hypothesis Workflow Control Lab notebook

1. Launch Jupyter Lab (`cd datalab && . .venv/bin/activate && jupyter lab`).
2. Open `notebooks/hypothesis_control.ipynb` and run all cells.
3. Use the panels:
   - **Meta grid**: refresh stat cards after new tests land in the backend.
   - **Experiment designer**: add a new hypothesis + tests; simulate runs to populate pass rates.
   - **Voting matrix**: cast votes and watch the change-log + Tail Log console update.
   - **Ops console**: click “Refresh tail log” after running Ops commands from the UI.
4. Record a notebook checkpoint by saving the file and running `python scripts/project_integrity.py checkpoint --tag notebook --reason "Hypothesis lab run"`.

## 3. Ops Deck orchestration drill

1. From the UI, run an Ops command (e.g., `restart` backend). Observe the command log entry.
2. In PowerShell: `Invoke-LabControlCenter` → confirm the matching job message.
3. Use `python scripts/project_integrity.py status --tags ops` to limit the diff report to files tagged `@tag:ops`.
4. Update `controlplane/orchestrator.py` (add a dummy log) and repeat the status command to see the targeted diff.

## 4. Data replay + repair

1. Run `python scripts/project_integrity.py checkpoint --tag replay --reason "Pre-replay"`.
2. Modify `chatai/backend/app/models.py` intentionally (add whitespace).
3. `python scripts/project_integrity.py verify chatai/backend/app/models.py` shows the hash mismatch.
4. `python scripts/project_integrity.py repair chatai/backend/app/models.py --checkpoint latest` restores the pristine copy.

## 5. Extending the stack

- **Frontend themes**: add a new entry to `THEME_VARIANTS` in `App.tsx` and tag it with `@tag:ui,theme`.
- **LLM providers**: implement a new client in `app/services/llm_client.py`, annotate the class with `# @tag:backend,llm`.
- **DataLab assets**: drop additional notebooks into `datalab/notebooks/` and document them inside `docs/TUTORIALS.md` so future contributors know how to reproduce your analysis.

> Every tutorial step now maps to the integrity manifest + tagging system, making it easy to answer “what changed, why, and when?”
